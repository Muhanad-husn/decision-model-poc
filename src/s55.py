"""S55 arm: label Axial items with Sonnet 5.5 through headless `claude -p` (PRD §6.2).

One draw per process. The blind-axis and head-axis gold-coder prompts are merged into one
system prompt carrying the slice 02 question text; each call labels a batch of at most 10
items sent on stdin. Every call runs isolated from this harness: a fresh empty temp dir
outside the repo, no tools, no MCP, no slash commands, no setting sources, no session
persistence, and the parent session's env vars dropped. A calibration call opens each draw
and measures the input tokens the CLI adds around a near-empty prompt; past the ceiling the
draw aborts, and the figure is logged as harness overhead. A resolved model id that is not
Sonnet 5.5 stops the draw (RULES.md kill line). An invalid item is re-asked once alone,
then recorded as `invalid`.

Run: uv run python src/s55.py --run-id <id> --draw <n> [--limit 5]
     uv run python src/s55.py --run-id <id> --calibrate   (measure only)
Writes runs/s55/<run_id>/draw_<n>/: calls/ (raw CLI output), calls.jsonl, labels.jsonl,
summary.json.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.codebook import questions  # noqa: E402

ITEMS = {"axial": ROOT / "data" / "axial" / "items.jsonl"}
RUNS = ROOT / "runs" / "s55"

MODEL = "claude-sonnet-5-5"
SONNET_55 = re.compile(r"^claude-sonnet-5-5(?![0-9])")
BATCH_SIZE = 10
# Total input tokens (input + cache read + cache creation) the calibration call may cost.
# None until the smoke run measures it; a draw refuses to start without it.
CALIBRATION_CEILING = None
CALIBRATION_SYSTEM = "Reply with exactly one word."
CALIBRATION_USER = "ping"
# CreateProcess refuses a command line past 32,767 characters; the system prompt rides argv.
MAX_COMMAND_LINE = 32_000
TIMEOUT_S = 900

EXIT_WRONG_MODEL = 3
EXIT_CALIBRATION = 4
EXIT_CLI = 5

# Parent-session variables that would tie the child to this harness.
DROP_ENV_PREFIXES = ("CLAUDE_CODE_", "AEO_")
DROP_ENV = {"CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT"}

# The gold-coder prompt (Axial docs/_archive/gold-coder.md), blind and head variants merged.
# File reads are replaced by the inlined codebook and the passages on stdin.
PREAMBLE = """\
You are an expert qualitative coder applying a fixed codebook to short scholarly
passages. This is a coding task, not an interpretive essay: apply the codebook
faithfully and consistently, the same way a trained second coder would. You have no
memory of any other conversation — treat this as a standalone task.

The codebook follows: for each axis, its question and every option id with a definition,
an example and a counter-example. The passages arrive in the user turn, each as
<passage key="...">text</passage>.

You have NOT been shown any prior automated guess for these passages — label from your
own independent reading only. For every passage, produce `field` (one tag id),
`empirical_scope` (one `scope:*` id, most specific level the claims actually rest on),
`role_in_argument` (one `role:*` id, the passage's function in the author's own
argument), `claim_type` (one top-level tag id) and `theory_school` (one tag id;
`not-applicable` if the passage advances no theoretical position, `unlisted` if a real
school applies but isn't listed — decide not-applicable-or-not FIRST, never use either
marker as a hedge).

Work through every passage — do not skip any. Reply with a single JSON object keyed by
passage key, each value an object with exactly these keys: {axes}. Every value is one
option id from the codebook, written exactly as listed. Do not echo the passage text
back. Reply with the JSON object only, no other text."""

PASSAGE = re.compile(r'<passage key="([^"]+)">')


class WrongModel(RuntimeError):
    """The resolved model id is not Sonnet 5.5: the kill line."""


class CalibrationExceeded(RuntimeError):
    """The CLI added more input tokens than the ceiling allows."""


class CLIError(RuntimeError):
    """The CLI exited non-zero or reported an error."""


def system_prompt(qs):
    parts = [PREAMBLE.format(axes=", ".join(f"`{a}`" for a in qs)), "", "# Codebook"]
    for axis, q in qs.items():
        parts += ["", f"## {axis}", f"Question: {q['instructions']}", "Options:"]
        parts += [f"- `{option}`: {text}" for option, text in q["criteria"].items()]
    return "\n".join(parts)


def user_prompt(batch):
    if len(batch) > BATCH_SIZE:
        raise ValueError(f"batch of {len(batch)} is over {BATCH_SIZE}")
    blocks = [f'<passage key="{k}">\n{item["text"]}\n</passage>' for k, item in enumerate(batch, 1)]
    return "Label these passages.\n\n" + "\n\n".join(blocks) + "\n"


def batch_keys(user):
    return PASSAGE.findall(user)


def batches(items, size=BATCH_SIZE):
    return [items[i:i + size] for i in range(0, len(items), size)]


def argv(system):
    return [
        "claude", "-p",
        "--output-format", "json",
        "--model", MODEL,
        "--tools", "",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--setting-sources", "",
        "--no-session-persistence",
        "--system-prompt", system,
    ]


def child_env(env):
    return {k: v for k, v in env.items()
            if k not in DROP_ENV and not k.startswith(DROP_ENV_PREFIXES)}


def subprocess_runner(args, cwd, env, stdin):
    p = subprocess.run(args, cwd=cwd, env=env, input=stdin, capture_output=True,
                       text=True, encoding="utf-8", timeout=TIMEOUT_S)
    return p.returncode, p.stdout, p.stderr


def parse_labels(text):
    """The JSON object in a reply, or None. Tolerates a code fence around it."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def invalid_axes(labels, qs):
    if not isinstance(labels, dict):
        return list(qs)
    return [axis for axis, q in qs.items() if labels.get(axis) not in q["criteria"]]


def input_total(usage):
    return sum(usage.get(k) or 0 for k in
               ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


class Draw:
    def __init__(self, run_dir, runner, pause):
        self.dir = Path(run_dir)
        (self.dir / "calls").mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.pause = pause
        self.n = 0
        self.models = set()
        self.usage = {}
        self.duration_ms = 0

    def call(self, kind, system, user, ids=()):
        if self.n and self.pause:
            time.sleep(self.pause)
        self.n += 1
        args = argv(system)
        if len(subprocess.list2cmdline(args)) > MAX_COMMAND_LINE:
            raise ValueError("system prompt too long for one command line")
        cwd = Path(tempfile.mkdtemp(prefix="s55-"))
        if cwd.resolve() == ROOT or ROOT in cwd.resolve().parents:
            raise RuntimeError(f"temp dir {cwd} is inside the repo")
        try:
            t0 = time.perf_counter()
            code, out, err = self.runner(args, cwd, child_env(os.environ), user)
            wall_ms = round((time.perf_counter() - t0) * 1000)
        finally:
            shutil.rmtree(cwd, ignore_errors=True)
        (self.dir / "calls" / f"{self.n:03d}-{kind}.json").write_text(out or "", encoding="utf-8")
        try:
            reply = json.loads(out)
        except (json.JSONDecodeError, TypeError):
            reply = None
        usage = (reply or {}).get("usage") or {}
        models = sorted((reply or {}).get("modelUsage") or {})
        row = {
            "n": self.n, "kind": kind, "ids": list(ids), "returncode": code,
            "is_error": (reply or {}).get("is_error"), "duration_ms": (reply or {}).get("duration_ms"),
            "wall_ms": wall_ms, "usage": usage, "models": models,
        }
        with open(self.dir / "calls.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        if code != 0 or reply is None or reply.get("is_error"):
            raise CLIError(f"call {self.n} ({kind}) failed: exit {code}; {(err or '').strip()[:300]}")
        if not models or not all(SONNET_55.match(m) for m in models):
            raise WrongModel(f"call {self.n} ({kind}) resolved to {models or 'no model id'}, not Sonnet 5.5")
        self.models.update(models)
        for k, v in usage.items():
            if isinstance(v, (int, float)):
                self.usage[k] = self.usage.get(k, 0) + v
        self.duration_ms += row["duration_ms"] or 0
        return reply, row


def calibrate(draw):
    _, row = draw.call("calibration", CALIBRATION_SYSTEM, CALIBRATION_USER)
    return input_total(row["usage"])


def run_draw(items, *, run_dir, runner=subprocess_runner, draw=1, ceiling=CALIBRATION_CEILING,
             batch_size=BATCH_SIZE, pause=0, qs=None):
    qs = qs or questions()
    d = Draw(run_dir, runner, pause)
    overhead = calibrate(d)
    if ceiling is None:
        raise CalibrationExceeded(f"no calibration ceiling set (measured {overhead}); set it from the smoke run")
    if overhead > ceiling:
        raise CalibrationExceeded(f"calibration input tokens {overhead} over the ceiling {ceiling}")
    system = system_prompt(qs)
    out, reasked = {}, set()
    for batch in batches(items, batch_size):
        user = user_prompt(batch)
        reply, _ = d.call("batch", system, user, [i["id"] for i in batch])
        labels = parse_labels(reply.get("result") or "") or {}
        for key, item in zip(batch_keys(user), batch):
            got = labels.get(key)
            if invalid_axes(got, qs):
                reasked.add(item["id"])
                lone = user_prompt([item])
                again, _ = d.call("reask", system, lone, [item["id"]])
                got = (parse_labels(again.get("result") or "") or {}).get(batch_keys(lone)[0])
                bad = invalid_axes(got, qs)
                got = {axis: "invalid" if axis in bad else got[axis] for axis in qs}
            out[item["id"]] = {axis: got[axis] for axis in qs}
    invalid = [{"id": i, "axes": [a for a, v in labs.items() if v == "invalid"]}
               for i, labs in out.items() if "invalid" in labs.values()]
    with open(d.dir / "labels.jsonl", "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps({"id": item["id"], "draw": draw, "labels": out[item["id"]],
                                "reasked": item["id"] in reasked}) + "\n")
    summary = {
        "draw": draw, "items": len(items), "calls": d.n, "models": sorted(d.models),
        "harness_overhead_input_tokens": overhead, "calibration_ceiling": ceiling,
        "usage": d.usage, "duration_ms": d.duration_ms,
        "reasked": sorted(reasked), "invalid": invalid,
    }
    (d.dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def load_items(path, limit=None):
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return [{"id": r["id"], "text": r["text"]} for r in rows[:limit]]


def cli_version():
    try:
        return subprocess.run(["claude", "--version"], capture_output=True, text=True,
                              timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main(args=None, runner=None, runs_root=RUNS):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--set", default="axial", choices=sorted(ITEMS))
    p.add_argument("--run-id", required=True)
    p.add_argument("--draw", type=int, default=1)
    p.add_argument("--limit", type=int)
    p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    p.add_argument("--pause", type=float, default=5.0, help="seconds between calls")
    p.add_argument("--calibrate", action="store_true", help="measure harness overhead only")
    a = p.parse_args(args)
    run_dir = Path(runs_root) / a.run_id / f"draw_{a.draw}"
    version = cli_version() if runner is None else None
    runner = runner or subprocess_runner
    try:
        if a.calibrate:
            d = Draw(run_dir, runner, 0)
            overhead = calibrate(d)
            print(json.dumps({"harness_overhead_input_tokens": overhead, "models": sorted(d.models),
                              "cli": version}))
            return 0
        summary = run_draw(load_items(ITEMS[a.set], a.limit), run_dir=run_dir, runner=runner,
                           draw=a.draw, batch_size=a.batch_size, pause=a.pause)
    except WrongModel as e:
        print(f"KILL LINE: {e}", file=sys.stderr)
        return EXIT_WRONG_MODEL
    except CalibrationExceeded as e:
        print(f"ABORT: {e}", file=sys.stderr)
        return EXIT_CALIBRATION
    except CLIError as e:
        print(f"CLI ERROR: {e}", file=sys.stderr)
        return EXIT_CLI
    summary.update({"run_id": a.run_id, "set": a.set, "cli": version})
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
                      ("run_id", "draw", "items", "calls", "models", "harness_overhead_input_tokens",
                       "usage", "duration_ms", "reasked", "invalid")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
