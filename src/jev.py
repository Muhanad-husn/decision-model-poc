"""Send each item to Jev in one call carrying all its questions (PRD §6.1), under the spend
guard and pacing of PRD §9.

Every call goes through the pinned typesafe-sdk with the SDK's own retries switched off, so the
exponential backoff on 429 and 529 here is the only one. 401, 422 and any other error are
recorded once as failures. Cost is usage.input_tokens at $0.042 per million; the run stops
sending once spend booked by every earlier run under runs/jev/ plus this run passes $2.00.
Every response, failures included, lands raw in runs/jev/<run_id>/responses.jsonl with the
request hash, latency and input tokens, and summary.json closes the run.

A CIP set (c1, c2) takes its questions from src/cip.py, which refuses to build them unless
options.yaml still matches its frozen SHA-256; no key is read and no call made before that.
An option id missing only its `scope:`/`role:` prefix is that option, the same rule as the S55
arm, and is counted as prefix_restored.

Run: uv run python src/jev.py --set axial|c1|c2 --limit 5 --run-id smoke-axial-YYYYMMDD
     uv run python src/jev.py [--set c1] --check <run_id_1> <run_id_2>   (no calls)
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from typesafe_sdk import RetryPolicy, TypeSafeAPIError, TypeSafeClient, TypeSafeError
from typesafe_sdk import __version__ as SDK_VERSION

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from src import cip  # noqa: E402
from src.codebook import questions as codebook_questions  # noqa: E402
from src.codebook import restore_option  # noqa: E402

MODEL = "jev-1.13.0"
USD_PER_MILLION = 0.042
CEILING_USD = 2.00
MAX_CONCURRENCY = 4
BACKOFF_STATUSES = {429, 529}
BACKOFF_BASE_S = 1.0
MAX_RETRIES = 6
TIMEOUT_S = 60.0
RUNS = ROOT / "runs" / "jev"
SETS = {"axial": ROOT / "data" / "axial" / "items.jsonl", **cip.ITEMS}


class ParseError(ValueError):
    pass


def cost_usd(input_tokens):
    return input_tokens * USD_PER_MILLION / 1_000_000


def build_request(item, questions):
    """The wire body: the passage text alone as state, every question in one call."""
    return {"model": MODEL, "state": item["text"], "questions": questions}


def request_hash(body):
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_answers(raw, questions):
    """{axis: {choice, probabilities, confidence, prefix_restored}}. An option id missing only
    its `scope:`/`role:` prefix is that option, as on the S55 arm, and is flagged. Refuses a
    missing axis, a choice outside the options, or a probability vector that does not cover
    exactly the options."""
    answers = raw.get("answers") or {}
    parsed = {}
    for axis, q in questions.items():
        a = answers.get(axis)
        if not isinstance(a, dict):
            raise ParseError(f"{axis}: no answer")
        options = set(q["criteria"])
        choice, restored = restore_option(a.get("choice"), options)
        probs = a.get("probabilities")
        if isinstance(probs, dict):
            probs = {restore_option(o, options)[0]: p for o, p in probs.items()}
        if choice not in options:
            raise ParseError(f"{axis}: choice {a.get('choice')!r} is not an option")
        if not isinstance(probs, dict) or set(probs) != options:
            raise ParseError(f"{axis}: probabilities do not cover exactly the {len(options)} options")
        parsed[axis] = {"choice": choice, "probabilities": probs, "confidence": a.get("confidence"),
                        "prefix_restored": restored}
    return parsed


def restored_count(parsed):
    return sum(a["prefix_restored"] for a in parsed.values())


def prior_spend(runs_dir=RUNS):
    """Dollars already booked by every responses.jsonl under runs_dir."""
    tokens = 0
    for path in Path(runs_dir).glob("*/responses.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tokens += json.loads(line).get("input_tokens") or 0
    return cost_usd(tokens)


def make_client(api_key, transport=None):
    """The SDK client with its own retries off, so our backoff is the only one."""
    return TypeSafeClient(api_key=api_key, model=MODEL, retry=RetryPolicy(max_retries=0),
                          timeout=TIMEOUT_S, transport=transport)


def _call(client, body, sleep):
    """One item's call with backoff. Returns (status, raw body, latency_ms, attempts, error)."""
    attempt = 0
    while True:
        attempt += 1
        started = time.perf_counter()
        try:
            resp = client.system_one(body["state"], body["questions"], model=body["model"])
            latency = (time.perf_counter() - started) * 1000
            return resp.raw_http_response.status_code, resp.raw_http_response.json(), latency, attempt, None
        except TypeSafeAPIError as e:
            latency = (time.perf_counter() - started) * 1000
            if e.status in BACKOFF_STATUSES and attempt <= MAX_RETRIES:
                sleep(BACKOFF_BASE_S * 2 ** (attempt - 1))
                continue
            if 200 <= e.status < 300:  # the SDK could not validate a successful body
                return e.status, e.body, latency, attempt, None
            return e.status, e.body, latency, attempt, str(e)
        except TypeSafeError as e:  # no HTTP response: connection error or timeout
            return None, None, (time.perf_counter() - started) * 1000, attempt, str(e)


def run(items, client, run_dir, *, questions, concurrency=MAX_CONCURRENCY, sleep=time.sleep,
        ceiling=CEILING_USD, prior_usd=0.0):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    state = {"tokens": 0, "parsed": 0, "sent": 0, "restored": 0, "failed": [], "aborted": None,
             "models": set()}

    def over(spent):
        return prior_usd + spent > ceiling

    if over(0.0):
        state["aborted"] = f"prior spend ${prior_usd:.4f} already past the ${ceiling:.2f} ceiling"

    def one(item, out):
        with lock:
            if state["aborted"]:
                return
            state["sent"] += 1
        body = build_request(item, questions)
        status, raw, latency, attempts, error = _call(client, body, sleep)
        tokens, restored = 0, 0
        if error is None:
            tokens = ((raw or {}).get("usage") or {}).get("input_tokens") or 0
            try:
                restored = restored_count(parse_answers(raw or {}, questions))
            except ParseError as e:
                error = f"parse: {e}"
        row = {
            "item_id": item["id"],
            "request_hash": request_hash(body),
            "status": status,
            "latency_ms": round(latency, 1),
            "attempts": attempts,
            "input_tokens": tokens,
            "parsed": error is None,
            "error": error,
            "response": raw,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        with lock:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            state["tokens"] += tokens
            if isinstance(raw, dict) and raw.get("model"):
                state["models"].add(raw["model"])
            if error is None:
                state["parsed"] += 1
                state["restored"] += restored
            else:
                state["failed"].append({"item_id": item["id"], "status": status, "error": error})
            spent = cost_usd(state["tokens"])
            if not state["aborted"] and over(spent):
                state["aborted"] = (f"cumulative spend ${prior_usd + spent:.4f} passed the "
                                    f"${ceiling:.2f} ceiling")

    with (run_dir / "responses.jsonl").open("a", encoding="utf-8", newline="\n") as out:
        with ThreadPoolExecutor(max_workers=max(1, min(concurrency, MAX_CONCURRENCY))) as pool:
            for f in [pool.submit(one, item, out) for item in items]:
                f.result()

    spent = cost_usd(state["tokens"])
    summary = {
        "run_id": run_dir.name,
        "model": MODEL,
        "models_seen": sorted(state["models"]),
        "sdk": f"typesafe-sdk {SDK_VERSION}",
        "items": len(items),
        "sent": state["sent"],
        "parsed": state["parsed"],
        "prefix_restored": state["restored"],
        "failures": len(state["failed"]),
        "failed": state["failed"],
        "input_tokens": state["tokens"],
        "cost_usd": spent,
        "prior_usd": prior_usd,
        "cumulative_usd": prior_usd + spent,
        "aborted": state["aborted"],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _rows(run_dir):
    """{item_id: row} from a run's responses.jsonl; a later row for an item replaces an earlier."""
    rows = {}
    for line in (Path(run_dir) / "responses.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["item_id"]] = row
    return rows


def check_runs(*run_dirs, questions):
    """Validity across runs of the same items: each response re-parsed against the questions,
    each item's request hash compared across runs, each item absent from a run listed."""
    runs = {Path(d).name: _rows(d) for d in run_dirs}
    ids = sorted(set().union(*runs.values()))
    invalid, missing, mismatches, valid, restored = [], [], [], 0, 0
    for item_id in ids:
        hashes = set()
        for name, rows in runs.items():
            row = rows.get(item_id)
            if row is None:
                missing.append({"run": name, "item_id": item_id})
                continue
            hashes.add(row["request_hash"])
            try:
                restored += restored_count(parse_answers(row.get("response") or {}, questions))
                valid += 1
            except ParseError as e:
                invalid.append({"run": name, "item_id": item_id, "error": str(e)})
        if len(hashes) > 1:
            mismatches.append(item_id)
    return {
        "runs": list(runs),
        "items": len(ids),
        "valid": valid,
        "prefix_restored": restored,
        "invalid": invalid,
        "hash_mismatches": mismatches,
        "missing": missing,
        "ok": not (invalid or mismatches or missing),
    }


def load_key(env_file=ROOT / ".env"):
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "TYPESAFE_API_KEY":
                key = value.strip().strip('"').strip("'")
    return key


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--set", choices=sorted(SETS), help="with --check: the set the runs labelled")
    p.add_argument("--run-id")
    p.add_argument("--limit", type=int, help="first N items only (the smoke run uses 5)")
    p.add_argument("--check", nargs="+", metavar="RUN_ID",
                   help="no calls: validate these runs and compare request hashes item by item")
    args = p.parse_args(argv)

    try:
        questions = cip.questions(args.set) if args.set in cip.ITEMS else codebook_questions()
    except cip.OptionsChanged as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    if args.check:
        check = check_runs(*(RUNS / r for r in args.check), questions=questions)
        print(json.dumps(check, indent=2))
        return 0 if check["ok"] else 1
    if not (args.set and args.run_id):
        p.error("--set and --run-id are required unless --check is given")

    key = load_key()
    if not key:
        print("TYPESAFE_API_KEY is not set (environment or .env); no call was made.", file=sys.stderr)
        return 2
    run_dir = RUNS / args.run_id
    if (run_dir / "responses.jsonl").exists():
        print(f"{run_dir.relative_to(ROOT).as_posix()} already holds responses; pick a new run id.",
              file=sys.stderr)
        return 2
    if args.set in cip.ITEMS:
        items = cip.load_items(args.set, limit=args.limit)
    else:
        with SETS[args.set].open(encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]
        items = items[: args.limit] if args.limit else items

    prior = prior_spend()
    with make_client(key) as client:
        summary = run(items, client, run_dir, questions=questions, prior_usd=prior)
    print(json.dumps({k: v for k, v in summary.items() if k != "failed"}, indent=2))
    for f in summary["failed"]:
        print(f"FAILED {f['item_id']}: {f['status']} {f['error']}", file=sys.stderr)
    return 1 if summary["aborted"] or summary["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
