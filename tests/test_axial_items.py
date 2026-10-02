"""data/axial/items.jsonl reproduces every PRD §5.1 sanity value exactly (the M1 kill line)."""

import json
from pathlib import Path

import pytest

from src.axial_items import ITEMS, build_items, canonical_key, majority, sanity, write_items

ROOT = Path(__file__).resolve().parent.parent
COPY = ROOT / "data" / "axial"


# Toy data: the logic, on any machine.

def test_majority_needs_two_of_three():
    assert majority(["a", "a", "b"]) == "a"
    assert majority(["a", "a", "a"]) == "a"
    assert majority(["a", "b", "c"]) is None


def test_canonical_key_joins_renamed_sources_on_hash_and_chunk():
    old = "Some Author - Long Title (2013, Polity)-5d3ec1809b12_13_the-salience-of-nationalism_001"
    new = "malesevic-2013-5d3ec1809b12_13_the-salience-of-nationalism_001"
    assert canonical_key(old) == canonical_key(new) == "5d3ec1809b12_13_the-salience-of-nationalism_001"


def test_sanity_on_toy_items():
    items = [
        {"text": "x" * 10, "reference": {"claim_type": "a", "theory_school": "p"},
         "draws": {"claim_type": ["a", "a", "a"], "theory_school": ["p", "p", "q"]}},
        {"text": "x" * 20, "reference": {"claim_type": None, "theory_school": "r"},
         "draws": {"claim_type": ["a", "b", "c"], "theory_school": ["r", "r", "r"]}},
    ]
    s = sanity(items)
    assert s["claim_type"] == {"reference": 1, "no_majority": 1, "unanimous": 1, "contested": 1,
                               "pairwise": [0.5, 0.5, 0.5], "pairwise_mean": 0.5, "gold_mismatch": 0}
    assert s["theory_school"]["pairwise"] == [1.0, 0.5, 0.5]
    assert s["median_length"] == 15
    assert s["max_length"] == 20


# The real files: the PRD §5.1 values, exactly.

@pytest.fixture(scope="module")
def items():
    if not COPY.exists():
        pytest.skip("data/axial/ not present on this machine")
    return build_items()


def test_one_row_per_passage(items):
    assert len(items) == 120
    assert len({i["id"] for i in items}) == 120
    for i in items:
        assert len(i["draws"]["claim_type"]) == len(i["draws"]["theory_school"]) == 3
        assert all(len(i["draws"][a]) == 1 for a in ("field", "empirical_scope", "role_in_argument"))
        assert set(i["prod_a"]) == {"claim_type", "field", "empirical_scope", "role_in_argument"}


def test_claim_type_sanity(items):
    assert sanity(items)["claim_type"] == {
        "reference": 117, "no_majority": 3, "unanimous": 93, "contested": 27,
        "pairwise": [0.842, 0.817, 0.867], "pairwise_mean": 0.842, "gold_mismatch": 0,
    }


def test_theory_school_sanity(items):
    assert sanity(items)["theory_school"] == {
        "reference": 105, "no_majority": 15, "unanimous": 59, "contested": 61,
        "pairwise": [0.650, 0.600, 0.608], "pairwise_mean": 0.619, "gold_mismatch": 0,
    }


def test_passage_lengths(items):
    s = sanity(items)
    # PRD §5.1 states 1,441. The 60th and 61st sorted lengths are 1,439 and 1,444, so the
    # median is 1,441.5; the PRD figure is that value with the half dropped. Asserted as
    # measured, with the PRD's integer alongside, pending the founder's call (PR body).
    assert s["median_length"] == 1441.5
    assert int(s["median_length"]) == 1441
    assert s["max_length"] == 2964


def test_written_file_round_trips(items, tmp_path):
    out = tmp_path / "items.jsonl"
    write_items(items, out)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert rows == items
    assert ITEMS == COPY / "items.jsonl"
