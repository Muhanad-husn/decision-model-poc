"""Slice 17: PUBLISH.md held to PRD §10's publishing rules.

The gate greps what a reader outside the repo would see: no em dash, no "OSINT" or
"open-source", the LLM-label statement in the first paragraph, nothing about CIP beyond its
results, and a reason in the same sentence as every CIP figure that reads as a shortfall.
The bar marks are read against REPORT.md, which test_report.py holds to the results."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PUBLISH_PATH = ROOT / "PUBLISH.md"
REPORT = (ROOT / "REPORT.md").read_text(encoding="utf-8")
METRICS = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
FROZEN = json.loads((ROOT / "bars.json").read_text(encoding="utf-8"))
BARS = {b["id"]: b for b in FROZEN["bars"]}

LLM_LABEL = "Every reference label in this study is an LLM label"
CIP_SOURCES = "the platform's source feeds, open and primary"
REASON = "because"

# PRD §10 rule 3 and 4: never anywhere in the document.
BANNED = {
    "em dash": "—",
    "OSINT": r"(?i)\bOSINT\b",
    "open-source": r"(?i)\bopen[- ]source\b",
}
# PRD §10 rule 2: Axial is never described as validated by human experts.
NOT_VALIDATED = [r"(?i)\bvalidated\b", r"(?i)\bgold\b", r"(?i)ground truth"]
# PRD §10 rule 3, never published for CIP: DEC numbers, schema file names, database structure,
# pipeline stages and the source list. None has a place on the Axial side either.
CIP_NEVER = [
    r"\bDEC-?\d+", r"(?i)schema", r"(?i)\bstages?\b", r"\.ya?ml\b", r"\.sqlite\b", r"\.jsonl?\b",
    r"is_current", r"(?i)\bevent edges?\b", r"(?i)\bprovenance\b",
    r"(?i)\bACLED\b", r"(?i)\bGDELT\b", r"(?i)\bUCDP\b", r"(?i)\bFIRMS\b", r"(?i)\bADS-B\b",
    r"(?i)\bOpenSky\b", r"(?i)\bOpenRouter\b",
]
# ...and, inside the CIP section, no prompt and no agent.
CIP_SECTION_NEVER = [r"(?i)\bprompts?\b", r"(?i)\bagents?\b"]


def _text():
    assert PUBLISH_PATH.exists(), "PUBLISH.md is missing"
    return PUBLISH_PATH.read_text(encoding="utf-8")


def _blocks(text):
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def _first_paragraph(text):
    return next(b for b in _blocks(text) if not b.startswith("#"))


def _section(text, prefix):
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {prefix}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1:end])


def _units(text):
    """Every table row, and every sentence of prose (a bullet is its own unit of sentences)."""
    units = []
    for block in _blocks(text):
        if block.startswith("#"):
            continue
        if block.startswith("|"):
            units += block.splitlines()
            continue
        for item in re.split(r"\n(?=- )", block):
            joined = " ".join(line.strip() for line in item.splitlines())
            units += re.split(r"(?<=[.!?])\s+", joined)
    return units


def _f(x):
    return f"{x:.3f}"


def cip_shortfalls():
    """Point figures for CIP that read as a shortfall: agreement below the B6 line, any
    identical-argmax share below 100%, and a doubt AUROC below B3's 0.70."""
    line, floor = BARS["B6"]["tolerance"], BARS["B3"]["min_auroc"]
    out = set()
    for name in ("c1", "c2"):
        s = METRICS["sets"][name]
        if s["determinism"]["identical_argmax"] < 1:
            out.add(_f(s["determinism"]["identical_argmax"]))
        for axis in s["axes"].values():
            coder = axis["coder_agreement"]
            bar = coder["draws_pairwise"]["agreement"] - line
            for arm, fig in coder["arms"].items():
                if fig["agreement"] < bar:
                    out.add(_f(fig["agreement"]))
                    out.add(_f(axis["vs_reference"][arm]["agreement"]))
            if axis["determinism"]["identical_argmax"] < 1:
                out.add(_f(axis["determinism"]["identical_argmax"]))
            if axis["doubt"]["auroc"] < floor:
                out.add(_f(axis["doubt"]["auroc"]))
    return out


def _marks(text):
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 3 and re.fullmatch(r"B\d+b?", cells[0]):
            rows[cells[0]] = cells[-1].strip("*").strip().lower()
    return rows


@pytest.mark.parametrize("name", BANNED)
def test_no_banned_term(name):
    hits = re.findall(BANNED[name], _text())
    assert not hits, f"PUBLISH.md uses {name} {len(hits)} times"


@pytest.mark.parametrize("pattern", NOT_VALIDATED)
def test_axial_never_described_as_validated(pattern):
    assert not re.search(pattern, _text()), pattern


def test_first_paragraph_says_every_reference_label_is_an_llm_label():
    assert LLM_LABEL in _first_paragraph(_text())


def test_verdict_comes_first():
    first = _first_paragraph(_text())
    verdict = "does not hold" if "the concept does not hold" in REPORT.lower() else "holds"
    assert f"the concept {verdict}" in first.lower()


@pytest.mark.parametrize("pattern", CIP_NEVER)
def test_nothing_about_cip_beyond_its_results(pattern):
    hits = re.findall(pattern, _text())
    assert not hits, f"{pattern}: {hits}"


@pytest.mark.parametrize("pattern", CIP_SECTION_NEVER)
def test_cip_section_names_no_prompt_or_agent(pattern):
    hits = re.findall(pattern, _section(_text(), "CIP"))
    assert not hits, f"{pattern}: {hits}"


def test_cip_sources_described_as_the_rule_says():
    assert CIP_SOURCES in _section(_text(), "CIP")


def test_shortfall_figures_known():
    # The gate below is empty if nothing reads as a shortfall; on these results plenty does.
    assert {"0.716", "0.601", "0.690", "0.985", "0.925", "0.526"} <= cip_shortfalls()


def test_every_cip_shortfall_carries_its_reason_in_the_same_sentence():
    figures = cip_shortfalls()
    bare = []
    for unit in _units(_text()):
        points = re.sub(r"\[[^\]]*\]", "", unit)  # an interval bound is not a figure on its own
        named = [f for f in figures if re.search(rf"(?<![\d.]){re.escape(f)}(?!\d)", points)]
        if named and REASON not in unit:
            bare.append((named, unit))
    assert not bare, bare


def test_every_cip_shortfall_figure_is_stated_with_a_reason():
    text = _text()
    missing = [f for f in sorted(cip_shortfalls()) if f not in text]
    assert not missing, f"CIP figures in results/metrics.json but not in PUBLISH.md: {missing}"


def test_bar_marks_match_report():
    published, reported = _marks(_text()), _marks(_section(REPORT, "Bar table"))
    assert published == reported


def test_plan_closes_m7():
    plan = (ROOT / "PLAN.md").read_text(encoding="utf-8")
    row = next(line for line in plan.splitlines() if line.startswith("| 7 M7"))
    assert row.split("|")[2].strip() == "done"
