"""The Jev runner: request shape (PRD §6.1), spend guard, backoff, failures, concurrency and
raw logging (PRD §9, RULES.md). Every test stubs the HTTP layer under the real SDK client, so
no call leaves the machine and no key is needed."""

import json
import threading
import time

import httpx2
import pytest

from src.codebook import questions as codebook_questions
from src.jev import (
    CEILING_USD,
    MODEL,
    ParseError,
    build_request,
    check_runs,
    cost_usd,
    make_client,
    parse_answers,
    prior_spend,
    request_hash,
    run,
)

QUESTIONS = codebook_questions()
AXES = ("field", "empirical_scope", "role_in_argument", "claim_type", "theory_school")
ITEMS = [{"id": f"item-{n}", "text": f"Passage {n}.", "source": "src-x"} for n in range(6)]


def answer(axis_criteria, pick=None):
    options = list(axis_criteria)
    pick = pick or options[0]
    rest = (1.0 - 0.6) / (len(options) - 1)
    probs = {o: (0.6 if o == pick else rest) for o in options}
    return {"type": "choice", "choice": pick, "confidence": 0.6, "probabilities": probs}


def good_body(input_tokens=7000, questions=QUESTIONS):
    return {
        "model": MODEL,
        "usage": {"input_tokens": input_tokens, "output_tokens": 5},
        "answers": {axis: answer(q["criteria"]) for axis, q in questions.items()},
    }


def client_for(handler):
    return make_client("test-key", transport=httpx2.MockTransport(handler))


def ok(request, input_tokens=7000):
    return httpx2.Response(200, json=good_body(input_tokens), headers={"x-typesafe-request-id": "req-1"})


def lines(run_dir):
    return [json.loads(l) for l in (run_dir / "responses.jsonl").read_text(encoding="utf-8").splitlines()]


# Request shape

def test_request_is_model_state_and_all_five_questions():
    body = build_request(ITEMS[0], QUESTIONS)
    assert body["model"] == MODEL == "jev-1.13.0"
    assert body["state"] == "Passage 0."  # passage text only, no id, source or metadata
    assert list(body["questions"]) == list(AXES)
    assert body["questions"] == QUESTIONS


def test_wire_body_is_the_built_request(tmp_path):
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return ok(request)

    run(ITEMS[:1], client_for(handler), tmp_path, questions=QUESTIONS, sleep=lambda s: None)
    assert seen == [build_request(ITEMS[0], QUESTIONS)]


def test_request_hash_is_stable_and_content_sensitive():
    a = build_request(ITEMS[0], QUESTIONS)
    assert request_hash(a) == request_hash(json.loads(json.dumps(a)))
    assert request_hash(a) != request_hash(build_request(ITEMS[1], QUESTIONS))


# Parsing

def test_parse_gives_choice_and_full_probabilities_per_axis():
    parsed = parse_answers(good_body(), QUESTIONS)
    assert list(parsed) == list(AXES)
    for axis in AXES:
        assert parsed[axis]["choice"] in QUESTIONS[axis]["criteria"]
        assert set(parsed[axis]["probabilities"]) == set(QUESTIONS[axis]["criteria"])
        assert "confidence" in parsed[axis]


def test_missing_axis_is_a_parse_failure():
    body = good_body()
    del body["answers"]["theory_school"]
    with pytest.raises(ParseError, match="theory_school"):
        parse_answers(body, QUESTIONS)


def test_missing_option_probability_is_a_parse_failure():
    body = good_body()
    dropped = next(iter(QUESTIONS["claim_type"]["criteria"]))
    del body["answers"]["claim_type"]["probabilities"][dropped]
    with pytest.raises(ParseError, match="claim_type"):
        parse_answers(body, QUESTIONS)


def test_choice_outside_the_options_is_a_parse_failure():
    body = good_body()
    body["answers"]["field"]["choice"] = "not-an-option"
    with pytest.raises(ParseError, match="field"):
        parse_answers(body, QUESTIONS)


# Logging

def test_every_response_is_logged_raw_with_hash_latency_and_tokens(tmp_path):
    summary = run(ITEMS[:3], client_for(ok), tmp_path, questions=QUESTIONS, sleep=lambda s: None)
    rows = lines(tmp_path)
    assert len(rows) == 3
    for row in rows:
        item = next(i for i in ITEMS if i["id"] == row["item_id"])
        assert row["request_hash"] == request_hash(build_request(item, QUESTIONS))
        assert row["latency_ms"] >= 0
        assert row["input_tokens"] == 7000
        assert row["status"] == 200
        assert row["response"] == good_body()
    assert summary["items"] == 3 and summary["parsed"] == 3 and summary["failures"] == 0
    assert summary["input_tokens"] == 21000
    assert summary["cost_usd"] == pytest.approx(21000 * 0.042 / 1e6)
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == summary


# Spend guard

def test_cost_is_input_tokens_at_0_042_per_million():
    assert cost_usd(1_000_000) == pytest.approx(0.042)
    assert CEILING_USD == 2.00


def test_guard_aborts_once_cumulative_cost_passes_two_dollars(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return ok(request, input_tokens=20_000_000)  # $0.84 a call

    summary = run(ITEMS, client_for(handler), tmp_path, questions=QUESTIONS, concurrency=1, sleep=lambda s: None)
    assert len(calls) == 3  # 0.84, 1.68, 2.52: the third passes $2.00, nothing after it is sent
    assert summary["aborted"] and "2.00" in summary["aborted"]
    assert summary["cost_usd"] == pytest.approx(3 * 0.84)


def test_guard_counts_spend_already_booked_by_earlier_runs(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return ok(request, input_tokens=1_000_000)  # $0.042

    summary = run(ITEMS, client_for(handler), tmp_path, questions=QUESTIONS, concurrency=1,
                  sleep=lambda s: None, prior_usd=1.99)
    assert len(calls) == 1
    assert summary["aborted"]


def test_prior_spend_sums_input_tokens_over_earlier_runs(tmp_path):
    for run_id, tokens in (("a", [1_000_000, 500_000]), ("b", [500_000])):
        d = tmp_path / run_id
        d.mkdir()
        (d / "responses.jsonl").write_text(
            "".join(json.dumps({"input_tokens": t}) + "\n" for t in tokens), encoding="utf-8")
    assert prior_spend(tmp_path) == pytest.approx(2_000_000 * 0.042 / 1e6)
    assert prior_spend(tmp_path / "missing") == 0.0


# Backoff and failures

@pytest.mark.parametrize("status", [429, 529])
def test_backoff_fires_exponentially_on_429_and_529(tmp_path, status):
    hits, sleeps = [], []

    def handler(request):
        hits.append(1)
        return ok(request) if len(hits) > 3 else httpx2.Response(status, json={"error": "busy"})

    summary = run(ITEMS[:1], client_for(handler), tmp_path, questions=QUESTIONS, sleep=sleeps.append)
    assert len(hits) == 4  # the SDK's own retries are off: every hit is one of ours
    assert sleeps == [1.0, 2.0, 4.0]
    assert summary["parsed"] == 1 and summary["failures"] == 0


def test_backoff_gives_up_and_records_a_failure(tmp_path):
    sleeps = []
    summary = run(ITEMS[:1], client_for(lambda r: httpx2.Response(429, json={})), tmp_path,
                  questions=QUESTIONS, sleep=sleeps.append)
    assert len(sleeps) == 6
    assert summary["failures"] == 1
    assert lines(tmp_path)[0]["status"] == 429


@pytest.mark.parametrize("status", [401, 422])
def test_401_and_422_are_failures_not_retried(tmp_path, status):
    hits, sleeps = [], []

    def handler(request):
        hits.append(1)
        return httpx2.Response(status, json={"error": "nope"})

    summary = run(ITEMS[:1], client_for(handler), tmp_path, questions=QUESTIONS, sleep=sleeps.append)
    assert len(hits) == 1 and sleeps == []
    assert summary["failures"] == 1 and summary["parsed"] == 0
    row = lines(tmp_path)[0]
    assert row["status"] == status and row["input_tokens"] == 0 and "nope" in row["error"]
    assert summary["failed"] == [{"item_id": "item-0", "status": status, "error": row["error"]}]


def test_unparseable_response_is_a_failure_but_its_tokens_still_count(tmp_path):
    def handler(request):
        body = good_body()
        del body["answers"]["field"]["probabilities"]["state"]
        return httpx2.Response(200, json=body)

    summary = run(ITEMS[:1], client_for(handler), tmp_path, questions=QUESTIONS, sleep=lambda s: None)
    assert summary["parsed"] == 0 and summary["failures"] == 1
    assert summary["input_tokens"] == 7000


# Concurrency

def test_concurrency_never_exceeds_four(tmp_path):
    lock, live, peak = threading.Lock(), [0], [0]

    def handler(request):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        time.sleep(0.05)
        with lock:
            live[0] -= 1
        return ok(request)

    items = [{"id": f"i{n}", "text": f"t{n}"} for n in range(12)]
    summary = run(items, client_for(handler), tmp_path, questions=QUESTIONS, concurrency=8, sleep=lambda s: None)
    assert summary["parsed"] == 12
    assert peak[0] == 4  # asked for 8, capped at the PRD's 4


# Cross-run check (slice 04)

def write_run(run_dir, rows):
    run_dir.mkdir(parents=True)
    with (run_dir / "responses.jsonl").open("w", encoding="utf-8") as f:
        for item_id, body, response in rows:
            f.write(json.dumps({"item_id": item_id, "request_hash": request_hash(body),
                                "parsed": True, "response": response}) + "\n")


def test_check_runs_passes_two_identical_valid_runs(tmp_path):
    rows = [(i["id"], build_request(i, QUESTIONS), good_body()) for i in ITEMS]
    write_run(tmp_path / "r1", rows)
    write_run(tmp_path / "r2", rows)
    check = check_runs(tmp_path / "r1", tmp_path / "r2", questions=QUESTIONS)
    assert check["ok"] is True
    assert check["valid"] == 2 * len(ITEMS)
    assert check["invalid"] == [] and check["hash_mismatches"] == [] and check["missing"] == []


def test_check_runs_lists_a_response_missing_probabilities(tmp_path):
    broken = good_body()
    del broken["answers"]["theory_school"]["probabilities"]
    rows = [(i["id"], build_request(i, QUESTIONS), good_body()) for i in ITEMS]
    write_run(tmp_path / "r1", rows)
    write_run(tmp_path / "r2", rows[:-1] + [(ITEMS[-1]["id"], rows[-1][1], broken)])
    check = check_runs(tmp_path / "r1", tmp_path / "r2", questions=QUESTIONS)
    assert check["ok"] is False
    assert check["valid"] == 2 * len(ITEMS) - 1
    assert [(v["run"], v["item_id"]) for v in check["invalid"]] == [("r2", ITEMS[-1]["id"])]


def test_check_runs_lists_items_whose_request_hash_differs_or_is_missing(tmp_path):
    rows = [(i["id"], build_request(i, QUESTIONS), good_body()) for i in ITEMS]
    changed = dict(ITEMS[0], text="A different passage.")
    write_run(tmp_path / "r1", rows)
    write_run(tmp_path / "r2", [(ITEMS[0]["id"], build_request(changed, QUESTIONS), good_body())] + rows[1:-1])
    check = check_runs(tmp_path / "r1", tmp_path / "r2", questions=QUESTIONS)
    assert check["ok"] is False
    assert check["hash_mismatches"] == [ITEMS[0]["id"]]
    assert check["missing"] == [{"run": "r2", "item_id": ITEMS[-1]["id"]}]
