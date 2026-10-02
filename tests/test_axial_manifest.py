"""The Axial copy in data/axial/ matches its committed SHA-256 manifest and the source."""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifests" / "axial.json"
COPY = ROOT / "data" / "axial"
SOURCE = Path(r"D:\axial")

EXPECTED_FIXED = {
    "data/gold/label_sheet.xlsx",
    "data/gold/dispatch/out/blind_draw_1.json",
    "data/gold/dispatch/out/blind_draw_2.json",
    "data/gold/dispatch/out/blind_draw_3.json",
    "data/gold/dispatch/out/head_partition_1_out.json",
    "data/gold/dispatch/out/head_partition_2_out.json",
    "data/gold/dispatch/out/head_partition_3_out.json",
    "data/gold/dispatch/out/head_partition_4_out.json",
    "config/domains/syria/codebook.yaml",
    "docs/_archive/gold-coder.md",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entries():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]


def test_manifest_lists_every_prd_file():
    paths = set(entries())
    assert EXPECTED_FIXED <= paths
    chunks = {p for p in paths if p.startswith("data/gold/chunks/") and p.endswith(".json")}
    assert len(chunks) == 120
    assert paths == EXPECTED_FIXED | chunks


def test_copy_matches_manifest():
    if not COPY.exists():
        pytest.skip("data/axial/ not present on this machine")
    for rel, digest in entries().items():
        assert sha256(COPY / rel) == digest, rel


def test_source_still_matches_manifest():
    if not SOURCE.exists():
        pytest.skip("D:\\axial not present on this machine")
    for rel, digest in entries().items():
        assert sha256(SOURCE / rel) == digest, rel
