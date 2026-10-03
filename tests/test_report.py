"""Slice 16: REPORT.md read against results/metrics.json and bars.json.

Every bar's mark and the figures that decided it are recomputed here from the two JSON
files, so the report cannot say pass where the numbers say fail, or quote a figure the
results do not hold."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPORT = (ROOT / "REPORT.md").read_text(encoding="utf-8")
METRICS = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
FROZEN = json.loads((ROOT / "bars.json").read_text(encoding="utf-8"))
BARS = {b["id"]: b for b in FROZEN["bars"]}

SECTIONS = ["Verdict", "Bar table", "Q1", "Q2", "Q3", "Q4", "Caveats", "Run log"]
# B5's "cip" set is the two CIP item files; B6's questions live in one of them each.
B5_SETS = {"axial": ["axial"], "cip": ["c1", "c2"]}
B6_SETS = {"actor_type": "c1", "claim_type": "c2", "claim_subject_type": "c2"}


def _f(x):
    return f"{x:.3f}"


def _headings():
    return [line[3:].strip() for line in REPORT.splitlines() if line.startswith("## ")]


def _section(prefix):
    lines = REPORT.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {prefix}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1:end])


def _bar_rows():
    rows = {}
    for line in _section("Bar table").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if re.fullmatch(r"B\d+b?", cells[0]):
            rows[cells[0]] = {"figure": cells[2], "result": cells[3].strip("*").strip().lower()}
    return rows


def _b6_questions():
    bar, out = BARS["B6"], {}
    for q in bar["questions"]:
        coder = METRICS["sets"][B6_SETS[q]]["axes"][q]["coder_agreement"]
        jev, pairwise = coder["arms"]["JEV"]["agreement"], coder["draws_pairwise"]["agreement"]
        out[q] = (jev >= pairwise - bar["tolerance"], [jev, pairwise])
    return out


def expected():
    """{bar: (passes, figures that decided it)} from the frozen rules and the results."""
    axial = METRICS["sets"]["axial"]["axes"]
    out = {}

    b1 = BARS["B1"]
    passes, figures = True, []
    for axis in b1["axes"]:
        ref = axial[axis]["vs_reference"]
        jev, prod = ref["JEV"]["agreement"], ref["PROD-A"]["agreement"]
        passes &= jev >= prod - b1["tolerance"]
        figures += [jev, prod]
    out["B1"] = (passes, figures)

    b1b = BARS["B1b"]
    jev = axial[b1b["axis"]]["vs_reference"]["JEV"]["agreement"]
    out["B1b"] = (jev >= b1b["min_agreement"], [jev])

    b3 = BARS["B3"]
    auroc = axial[b3["axis"]]["doubt"]["auroc"]
    out["B3"] = (auroc >= b3["min_auroc"], [auroc])

    b4 = BARS["B4"]
    cost = METRICS["cost_latency"]
    pooled = cost["all"]["jev_to_s55_cost_ratio"]
    # The founder's ruling (PR #33): pooled over all sets, S55 priced from logged usage. The
    # Axial ratio is carried in the same row because it fails on its own.
    out["B4"] = (pooled <= b4["max_cost_ratio"], [pooled, cost["axial"]["jev_to_s55_cost_ratio"]])

    b5 = BARS["B5"]
    shares = [METRICS["sets"][s]["determinism"]["identical_argmax"] for group in b5["sets"] for s in B5_SETS[group]]
    out["B5"] = (all(x >= b5["min_identical_argmax"] for x in shares), shares)

    questions = _b6_questions()
    passing = sum(ok for ok, _ in questions.values())
    out["B6"] = (passing >= FROZEN["verdict"]["B6_min_questions_passing"],
                 [x for _, figs in questions.values() for x in figs])
    return out


def test_sections_follow_prd_order():
    heads = _headings()
    found = [next(h for h in heads if h.startswith(s)) for s in SECTIONS]
    assert [heads.index(h) for h in found] == sorted(heads.index(h) for h in found)
    assert heads[0] == "Verdict"


@pytest.mark.parametrize("bar", sorted(BARS))
def test_every_bar_marked_with_its_deciding_number(bar):
    row = _bar_rows()[bar]
    passes, figures = expected()[bar]
    assert row["result"] == ("pass" if passes else "fail")
    for x in figures:
        assert _f(x) in row["figure"], f"{bar}: {_f(x)} missing from {row['figure']!r}"


def test_b6_names_how_many_questions_pass():
    passing = sum(ok for ok, _ in _b6_questions().values())
    assert f"{passing} of {len(BARS['B6']['questions'])}" in _bar_rows()["B6"]["figure"]


def test_b4_row_carries_the_ruling_caveats():
    figure = _bar_rows()["B4"]["figure"]
    assert "pooled" in figure and "5-minute" in figure and "no caching" in figure


def test_verdict_follows_the_prd_rule_from_the_marks():
    marks = expected()
    holds = all(marks[b][0] for b in FROZEN["verdict"]["must_pass"]) and marks["B6"][0]
    first = next(line for line in _section("Verdict").splitlines() if line.strip())
    assert first.startswith("**The concept holds.**" if holds else "**The concept does not hold.**")


def test_b3_is_reported_on_its_own():
    first = next(line for line in _section("Verdict").splitlines() if line.strip())
    assert "B3" not in first
    assert "B3" in _section("Verdict")


# PRD §12, one phrase per caveat that the caveat cannot be stated without.
CAVEATS = {
    "llm_labels": ["All reference labels are LLM labels", "+0.26"],
    "n_120": ["n = 120", "0.20"],
    "single_draw_axes": ["single draw", "no contested flag"],
    "prod_a_codebook": ["earlier codebook version"],
    "jev_confidence": ["`confidence` is used as returned"],
}


@pytest.mark.parametrize("caveat", sorted(CAVEATS))
def test_each_prd_12_caveat_is_present(caveat):
    text = _section("Caveats")
    for phrase in CAVEATS[caveat]:
        assert phrase in text, f"{caveat}: {phrase!r} missing"


def test_run_log_names_models_sdk_and_spend():
    log = _section("Run log")
    for needle in ("jev-1.13.0", "claude-sonnet-5-5", "typesafe-sdk 0.7.2", "$0.0849"):
        assert needle in log
