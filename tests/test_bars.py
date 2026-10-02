"""bars.json is PRD §8 frozen: verbatim text plus the thresholds M6 reads."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BARS = ROOT / "bars.json"
PRD = Path(r"D:\The Merge Seat\research\decision-model-poc\PRD.md")


def load_bars():
    return json.loads(BARS.read_text(encoding="utf-8"))


def prd_section_8():
    text = PRD.read_text(encoding="utf-8")
    match = re.search(r"^## 8\. Pre-registered bars\n.*?(?=^## 9\.)", text, re.S | re.M)
    assert match, "PRD §8 not found in the master copy"
    return match.group(0).strip()


def test_verbatim_equals_prd_section_8():
    if not PRD.exists():
        pytest.skip("PRD master copy not on this machine")
    assert load_bars()["verbatim"] == prd_section_8()


def test_bar_ids():
    assert [b["id"] for b in load_bars()["bars"]] == ["B1", "B1b", "B3", "B4", "B5", "B6"]


def test_thresholds():
    bars = {b["id"]: b for b in load_bars()["bars"]}
    assert bars["B1"]["axes"] == ["claim_type", "field", "empirical_scope", "role_in_argument"]
    assert bars["B1"]["comparator"] == "PROD-A"
    assert bars["B1"]["tolerance"] == 0.05
    assert bars["B1b"]["axis"] == "theory_school"
    assert bars["B1b"]["min_agreement"] == 0.50
    assert bars["B3"]["axis"] == "theory_school"
    assert bars["B3"]["min_auroc"] == 0.70
    assert bars["B4"]["max_cost_ratio"] == 0.05
    assert bars["B5"]["min_identical_argmax"] == 1.0
    assert bars["B5"]["sets"] == ["axial", "cip"]
    assert bars["B6"]["questions"] == ["actor_type", "claim_type", "claim_subject_type"]
    assert bars["B6"]["tolerance"] == 0.10


def test_verdict_rule():
    verdict = load_bars()["verdict"]
    assert verdict["must_pass"] == ["B1", "B1b", "B4", "B5"]
    assert verdict["B6_min_questions_passing"] == 2
    assert verdict["reported_separately"] == ["B3"]
