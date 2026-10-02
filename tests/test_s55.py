"""The S55 runner (PRD §6.2), against a canned `claude -p` output. No subprocess is started."""

import json
from pathlib import Path

import pytest

from src import s55
from src.codebook import questions

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = questions()
AXES = list(QUESTIONS)
SONNET = "claude-sonnet-5-5-20260915"


def valid_labels():
    return {axis: next(iter(QUESTIONS[axis]["criteria"])) for axis in AXES}


def items(n):
    return [{"id": f"item-{i:03d}", "text": f"Passage number {i}."} for i in range(n)]


def canned(result, model=SONNET, input_tokens=12, cache_read=0, cache_creation=0):
    """The shape `claude -p --output-format json` prints."""
    return json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 1234,
        "result": result if isinstance(result, str) else json.dumps(result),
        "usage": {
            "input_tokens": input_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_creation,
            "output_tokens": 40,
        },
        "modelUsage": {model: {"inputTokens": input_tokens, "outputTokens": 40}},
    })


class FakeCLI:
    """Records every call; answers from a list of callables, one per call."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, argv, cwd, env, stdin):
        cwd = Path(cwd)
        self.calls.append({
            "argv": argv,
            "cwd": cwd,
            "cwd_exists": cwd.is_dir(),
            "cwd_entries": list(cwd.iterdir()) if cwd.is_dir() else None,
            "env": env,
            "stdin": stdin,
        })
        answer = self.answers.pop(0)
        return 0, answer(stdin) if callable(answer) else answer, ""


def calibration(**kw):
    return canned("pong", **kw)


def labels_for(stdin, override=None):
    """Answer a labelling call with valid labels for every key the user turn names."""
    keys = s55.batch_keys(stdin)
    out = {k: valid_labels() for k in keys}
    for k, axis_labels in (override or {}).items():
        out[k].update(axis_labels)
    return canned(out)


# The merged prompt.


def test_system_prompt_merges_blind_and_head_axes_with_codebook_text():
    system = s55.system_prompt(QUESTIONS)
    assert "expert qualitative coder" in system
    assert "decide not-applicable-or-not FIRST" in system  # blind-axis variant
    assert "NOT been shown any prior automated guess" in system  # head-axis variant
    for axis, q in QUESTIONS.items():
        assert q["instructions"] in system
        for option, text in q["criteria"].items():
            assert f"`{option}`: {text}" in system
    assert "Do not read or write any other files" not in system  # no file reads in this method


def test_user_prompt_inlines_the_batch_under_short_keys():
    batch = items(3)
    user = s55.user_prompt(batch)
    for item in batch:
        assert item["text"] in user
    assert s55.batch_keys(user) == ["1", "2", "3"]


def test_batches_hold_at_most_ten_items():
    assert [len(b) for b in s55.batches(items(23), 10)] == [10, 10, 3]
    with pytest.raises(ValueError):
        s55.user_prompt(items(11))


# Isolation.


def test_argv_carries_the_exact_isolation_flags():
    assert s55.argv("SYSTEM") == [
        "claude", "-p",
        "--output-format", "json",
        "--model", "claude-sonnet-5-5",
        "--tools", "",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--setting-sources", "",
        "--no-session-persistence",
        "--system-prompt", "SYSTEM",
    ]


def test_every_call_runs_in_a_fresh_empty_temp_dir_outside_the_repo(tmp_path):
    cli = FakeCLI(calibration(), lambda s: labels_for(s))
    s55.run_draw(items(2), run_dir=tmp_path / "run", runner=cli, draw=1, ceiling=100)
    cwds = [c["cwd"] for c in cli.calls]
    assert len(set(cwds)) == 2
    for c in cli.calls:
        assert c["cwd_exists"] and c["cwd_entries"] == []
        assert ROOT not in c["cwd"].resolve().parents
        assert not c["cwd"].exists()  # removed after the call


def test_child_env_drops_the_parent_session_vars():
    env = s55.child_env({"PATH": "x", "CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli",
                         "CLAUDE_EFFORT": "low", "AEO_DATA_ROOT": "", "HOME": "h"})
    assert env == {"PATH": "x", "HOME": "h"}


# Logging and validation.


def test_each_call_logs_duration_usage_and_model(tmp_path):
    cli = FakeCLI(calibration(), lambda s: labels_for(s))
    s55.run_draw(items(2), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    rows = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in rows] == ["calibration", "batch"]
    for r in rows:
        assert r["duration_ms"] == 1234
        assert r["usage"]["input_tokens"] == 12
        assert r["models"] == [SONNET]


def test_labels_are_validated_against_the_option_lists():
    good = valid_labels()
    assert s55.invalid_axes(good, QUESTIONS) == []
    assert s55.invalid_axes({**good, "field": "not-an-option"}, QUESTIONS) == ["field"]
    missing = dict(good)
    del missing["theory_school"]
    assert s55.invalid_axes(missing, QUESTIONS) == ["theory_school"]
    assert s55.invalid_axes(None, QUESTIONS) == AXES


def test_invalid_item_is_reasked_once_alone_and_kept_when_valid(tmp_path):
    cli = FakeCLI(
        calibration(),
        lambda s: labels_for(s, {"2": {"field": "bogus"}}),
        lambda s: labels_for(s),
    )
    summary = s55.run_draw(items(3), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert s55.batch_keys(cli.calls[2]["stdin"]) == ["1"]
    assert "Passage number 1." in cli.calls[2]["stdin"]
    rows = [json.loads(line) for line in (tmp_path / "labels.jsonl").read_text().splitlines()]
    assert [r["id"] for r in rows] == ["item-000", "item-001", "item-002"]
    assert rows[1]["reasked"] is True and rows[1]["labels"] == valid_labels()
    assert summary["invalid"] == []


def test_item_still_invalid_after_reask_is_recorded_invalid(tmp_path):
    cli = FakeCLI(
        calibration(),
        lambda s: labels_for(s, {"1": {"theory_school": "bogus"}}),
        lambda s: labels_for(s, {"1": {"theory_school": "still-bogus"}}),
    )
    summary = s55.run_draw(items(2), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert len(cli.calls) == 3  # one re-ask, never a second
    rows = [json.loads(line) for line in (tmp_path / "labels.jsonl").read_text().splitlines()]
    assert rows[0]["labels"]["theory_school"] == "invalid"
    assert rows[0]["labels"]["field"] == valid_labels()["field"]
    assert summary["invalid"] == [{"id": "item-000", "axes": ["theory_school"]}]


def test_unparseable_reply_reasks_every_item_alone(tmp_path):
    cli = FakeCLI(calibration(), canned("I cannot do that."), lambda s: labels_for(s), lambda s: labels_for(s))
    summary = s55.run_draw(items(2), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert len(cli.calls) == 4
    assert summary["invalid"] == []


# The kill line and the calibration ceiling.


def test_wrong_model_on_calibration_stops_before_any_labelling(tmp_path):
    cli = FakeCLI(calibration(model="claude-haiku-4-5-20251001"))
    with pytest.raises(s55.WrongModel):
        s55.run_draw(items(2), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert len(cli.calls) == 1


def test_wrong_model_on_a_batch_stops_the_draw(tmp_path):
    cli = FakeCLI(calibration(), canned({"1": valid_labels()}, model="claude-sonnet-5-20250929"))
    with pytest.raises(s55.WrongModel):
        s55.run_draw(items(12), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert len(cli.calls) == 2


def test_main_exits_nonzero_on_the_kill_line(tmp_path, monkeypatch):
    cli = FakeCLI(calibration(model="claude-opus-5-5"))
    code = s55.main(["--run-id", "t", "--limit", "2"], runner=cli, runs_root=tmp_path)
    assert code == s55.EXIT_WRONG_MODEL != 0
    assert len(cli.calls) == 1


def test_calibration_over_the_ceiling_aborts_before_any_labelling(tmp_path):
    cli = FakeCLI(calibration(input_tokens=10, cache_read=60, cache_creation=40))
    with pytest.raises(s55.CalibrationExceeded):
        s55.run_draw(items(2), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert len(cli.calls) == 1


def test_calibration_total_counts_cache_tokens_and_is_logged_as_overhead(tmp_path):
    cli = FakeCLI(calibration(input_tokens=10, cache_read=30, cache_creation=20), lambda s: labels_for(s))
    summary = s55.run_draw(items(1), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert summary["harness_overhead_input_tokens"] == 60
    assert summary["calibration_ceiling"] == 100


def test_a_draw_refuses_a_run_dir_that_already_holds_calls(tmp_path):
    (tmp_path / "calls.jsonl").write_text("{}\n")
    cli = FakeCLI()
    with pytest.raises(FileExistsError):
        s55.run_draw(items(1), run_dir=tmp_path, runner=cli, draw=1, ceiling=100)
    assert cli.calls == []
