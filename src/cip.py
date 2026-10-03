"""Turn the frozen CIP option descriptions into the C task questions (PRD §5.2, §6.1).

C1 asks `actor_type`; C2 asks `claim_type` then `claim_subject_type`. Each option's criterion
is its one-line description from data/cip/options.yaml, verbatim. Each instruction is one
sentence naming the axis; CIP's enums carry no decision rule to add. The state is the actor
name or the claim text, then the passage, with no id or metadata. This text is the single
source for the Jev request and the S55 prompt. Before any of it is built, the SHA-256 of
options.yaml is recomputed and must equal the one committed in manifests/cip_options.json.
No model call.
"""

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CIP = ROOT / "data" / "cip"
OPTIONS = CIP / "options.yaml"
MANIFEST = ROOT / "manifests" / "cip_options.json"
ITEMS = {"c1": CIP / "c1_items.jsonl", "c2": CIP / "c2_items.jsonl"}

INSTRUCTIONS = {
    "actor_type": "Which actor type is the actor named on the first line, as the passage shows it?",
    "claim_type": "Which claim type is the claim on the first line, as the passage shows it?",
    "claim_subject_type": "Which claim subject type is the claim on the first line about?",
}
TASKS = {"c1": ("actor_type",), "c2": ("claim_type", "claim_subject_type")}
SUBJECT = {"c1": ("Actor", "name"), "c2": ("Claim", "claim_text")}


class OptionsChanged(RuntimeError):
    """options.yaml no longer matches the SHA-256 frozen in the manifest."""


def verify_options(options=None, manifest=None):
    options, manifest = Path(options or OPTIONS), Path(manifest or MANIFEST)
    frozen = json.loads(manifest.read_text(encoding="utf-8"))["sha256"]
    actual = hashlib.sha256(options.read_bytes()).hexdigest()
    if actual != frozen:
        raise OptionsChanged(f"{options.name} SHA-256 {actual[:12]}... differs from the frozen "
                             f"{frozen[:12]}... in {manifest.name}; no call was made")
    return yaml.safe_load(options.read_text(encoding="utf-8"))


def questions(task, options=None, manifest=None):
    """{axis: {"type": "choice", "instructions": str, "criteria": {option: description}}}."""
    descriptions = verify_options(options, manifest)
    return {axis: {"type": "choice", "instructions": INSTRUCTIONS[axis],
                   "criteria": dict(descriptions[axis])}
            for axis in TASKS[task]}


def state(item, task):
    label, field = SUBJECT[task]
    return f"{label}: {item[field]}\n\nPassage: {item['passage']}"


def load_items(task, path=None, limit=None):
    with open(path or ITEMS[task], encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return [{"id": r["id"], "text": state(r, task)} for r in rows[:limit]]
