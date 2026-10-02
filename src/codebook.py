"""Turn the copied Axial codebook into one choice question per axis (PRD §6.1).

Each option's criterion is "<definition> Example: <positive> Not this: <negative>". Each
instruction is one sentence naming the axis, plus the axis decision rule where the codebook
has one. This text is the single source for the Jev request and the S55 prompt. No model call.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CODEBOOK = ROOT / "data" / "axial" / "config" / "domains" / "syria" / "codebook.yaml"

PARTS = ("definition", "positive_example", "negative_example")

# Axis order follows src/axial_items.py: head axes, then blind axes.
INSTRUCTIONS = {
    "field": "Which field is the object of this passage's explanation?",
    "empirical_scope": (
        "Which empirical scope does this passage work at? "
        "Choose the most specific level the claims actually rest on."
    ),
    "role_in_argument": "Which role in argument does this passage play in the author's own argument?",
    "claim_type": "Which claim type does this passage advance?",
    "theory_school": (
        "Which theory school does this passage's argument draw on? "
        "Decide `not-applicable` first: does the passage advance any theoretical position at all? "
        "`unlisted` means a real school that is not listed; never use either marker as a hedge."
    ),
}


def load_codebook(path=CODEBOOK):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def criterion(entry):
    definition, positive, negative = (str(entry[p]).strip() for p in PARTS)
    return f"{definition} Example: {positive} Not this: {negative}"


def build_questions(codebook):
    """{axis: {"type": "choice", "instructions": str, "criteria": {option: str}}}, in
    INSTRUCTIONS order, options in codebook order. Refuses an unknown axis or a missing part."""
    axes = codebook["axes"]
    unknown = set(axes) - set(INSTRUCTIONS)
    if unknown:
        raise ValueError(f"codebook axis with no instruction: {sorted(unknown)}")
    questions = {}
    for axis in INSTRUCTIONS:
        if axis not in axes:
            continue
        for option, entry in axes[axis].items():
            missing = [p for p in PARTS if not str(entry.get(p) or "").strip()]
            if missing:
                raise ValueError(f"{axis}/{option} lacks {', '.join(missing)}")
        questions[axis] = {
            "type": "choice",
            "instructions": INSTRUCTIONS[axis],
            "criteria": {option: criterion(entry) for option, entry in axes[axis].items()},
        }
    return questions


def questions(path=CODEBOOK):
    return build_questions(load_codebook(path))
