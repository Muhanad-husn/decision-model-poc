"""The frozen CIP option descriptions (PRD §5.2): data/cip/options.yaml carries exactly the
PRD option ids per question, one non-empty one-line description each, and its SHA-256 equals
the one committed in manifests/cip_options.json. data/ is git-ignored, so the committed hash is
what proves the freeze."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
OPTIONS = ROOT / "data" / "cip" / "options.yaml"
MANIFEST = ROOT / "manifests" / "cip_options.json"

PRD_OPTIONS = {
    "actor_type": [
        "state", "government", "military", "police", "rebel_group", "political_militia",
        "ethnic_militia", "religious_militia", "criminal_group", "political_party",
        "international_organization", "ngo", "media_organization", "civilian_group",
        "private_military", "unattributed",
    ],
    "claim_type": [
        "factual_assertion", "attribution", "denial", "threat", "announcement", "accusation",
        "justification", "other",
    ],
    "claim_subject_type": [
        "event_occurrence", "casualty_count", "actor_involvement", "weapon_use",
        "territorial_control", "policy_intent", "other",
    ],
}


@pytest.fixture
def options_file():
    if not OPTIONS.exists():
        pytest.skip("data/cip/ not present on this machine")
    return OPTIONS


def test_each_question_has_exactly_its_prd_options_with_one_line_each(options_file):
    options = yaml.safe_load(options_file.read_text(encoding="utf-8"))
    assert list(options) == list(PRD_OPTIONS)
    for question, ids in PRD_OPTIONS.items():
        assert list(options[question]) == ids, question
        for option, text in options[question].items():
            assert isinstance(text, str) and text.strip(), (question, option)
            assert "\n" not in text.strip(), (question, option)


def test_manifest_names_the_options_file():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["path"] == "data/cip/options.yaml"
    assert len(manifest["sha256"]) == 64


def test_options_file_matches_the_committed_hash(options_file):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert hashlib.sha256(options_file.read_bytes()).hexdigest() == manifest["sha256"]
