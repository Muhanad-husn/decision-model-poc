"""The CIP question builder (PRD §5.2, §6.1): one question per C task axis with options.yaml
as criteria, the state as actor name or claim text plus the passage, and a refusal when
options.yaml no longer matches its committed SHA-256. No model call."""

import hashlib
import json

import pytest
import yaml

from src import cip

if not cip.OPTIONS.exists():
    pytest.skip("data/cip/ not present on this machine", allow_module_level=True)
OPTIONS = yaml.safe_load(cip.OPTIONS.read_text(encoding="utf-8"))


def test_c1_asks_actor_type_and_c2_asks_claim_type_then_subject_type():
    assert list(cip.questions("c1")) == ["actor_type"]
    assert list(cip.questions("c2")) == ["claim_type", "claim_subject_type"]


def test_criteria_are_the_frozen_descriptions_verbatim():
    for task in ("c1", "c2"):
        for axis, q in cip.questions(task).items():
            assert q["type"] == "choice"
            assert q["criteria"] == OPTIONS[axis]
            assert q["instructions"].strip()


def test_state_is_the_actor_name_or_claim_text_then_the_passage():
    c1 = {"id": "a1", "name": "Some Actor", "passage": "A passage.", "event_id": "e", "prod_c": {}}
    c2 = {"id": "c1", "claim_text": "A claim.", "passage": "Its passage.", "claim_language": "fa"}
    assert cip.state(c1, "c1") == "Actor: Some Actor\n\nPassage: A passage."
    assert cip.state(c2, "c2") == "Claim: A claim.\n\nPassage: Its passage."


def test_items_carry_only_id_and_state(tmp_path):
    path = tmp_path / "c1_items.jsonl"
    rows = [{"id": f"x{n}", "name": f"N{n}", "passage": f"P{n}.", "prod_c": {"actor_type": "state"}}
            for n in range(3)]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    items = cip.load_items("c1", path=path, limit=2)
    assert items == [{"id": "x0", "text": "Actor: N0\n\nPassage: P0."},
                     {"id": "x1", "text": "Actor: N1\n\nPassage: P1."}]


def test_questions_refuse_when_options_differ_from_the_committed_hash(tmp_path):
    options = tmp_path / "options.yaml"
    options.write_bytes(cip.OPTIONS.read_bytes() + b"# edited after the freeze\n")
    manifest = tmp_path / "cip_options.json"
    manifest.write_text(json.dumps({"path": "data/cip/options.yaml",
                                    "sha256": hashlib.sha256(cip.OPTIONS.read_bytes()).hexdigest()}))
    with pytest.raises(cip.OptionsChanged, match="SHA-256"):
        cip.questions("c1", options=options, manifest=manifest)
