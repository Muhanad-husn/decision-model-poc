"""The codebook becomes one Jev question per Axial axis, in the PRD §6.1 form."""

import re

import pytest

from src.codebook import CODEBOOK, build_questions, load_codebook, questions

CRITERION = re.compile(r"^(?P<definition>.+) Example: (?P<positive>.+) Not this: (?P<negative>.+)$")


# Toy data: the logic, on any machine.

TOY = {
    "axes": {
        "field": {
            "state": {"definition": "The state.", "positive_example": "A tax.", "negative_example": "A war."},
            "violence": {"definition": "Violence.", "positive_example": "A war.", "negative_example": "A tax."},
        },
    },
}


def test_criterion_joins_the_three_parts_in_prd_form():
    q = build_questions(TOY)
    assert q["field"]["type"] == "choice"
    assert q["field"]["criteria"] == {
        "state": "The state. Example: A tax. Not this: A war.",
        "violence": "Violence. Example: A war. Not this: A tax.",
    }


def test_options_keep_codebook_order():
    assert list(build_questions(TOY)["field"]["criteria"]) == ["state", "violence"]


def test_missing_part_is_refused():
    broken = {"axes": {"field": {"state": {"definition": "The state.", "positive_example": "A tax."}}}}
    with pytest.raises(ValueError, match="negative_example"):
        build_questions(broken)


def test_unknown_axis_is_refused():
    with pytest.raises(ValueError, match="artifact_role"):
        build_questions({"axes": {"artifact_role": TOY["axes"]["field"]}})


# The real codebook: PRD §5.1 option counts and the §6.1 decision rules.

@pytest.fixture(scope="module")
def real():
    if not CODEBOOK.exists():
        pytest.skip("data/axial/ not present on this machine")
    return questions()


def test_each_axis_has_its_prd_option_count(real):
    counts = {axis: len(q["criteria"]) for axis, q in real.items()}
    assert counts == {"field": 3, "empirical_scope": 5, "role_in_argument": 7, "claim_type": 22, "theory_school": 30}


def test_theory_school_carries_both_markers(real):
    assert {"not-applicable", "unlisted"} <= set(real["theory_school"]["criteria"])


def test_every_criterion_has_all_three_parts_verbatim(real):
    book = load_codebook()["axes"]
    for axis, q in real.items():
        for option, text in q["criteria"].items():
            m = CRITERION.match(text)
            assert m, f"{axis}/{option}: {text!r}"
            entry = book[axis][option]
            assert m["definition"] == entry["definition"].strip()
            assert m["positive"] == entry["positive_example"].strip()
            assert m["negative"] == entry["negative_example"].strip()


def test_every_instruction_names_its_axis(real):
    for axis, q in real.items():
        assert axis.replace("_", " ") in q["instructions"], axis


def test_theory_school_instruction_decides_not_applicable_first(real):
    text = real["theory_school"]["instructions"]
    assert re.search(r"`not-applicable` first", text)
    assert re.search(r"`unlisted` means a real school that is not listed", text)


def test_empirical_scope_instruction_picks_most_specific_level(real):
    assert "most specific level" in real["empirical_scope"]["instructions"]


def test_other_axes_carry_no_decision_rule(real):
    for axis in ("field", "role_in_argument", "claim_type"):
        text = real[axis]["instructions"]
        assert "first" not in text and "most specific" not in text, axis
