"""Copy the PRD §5.1 Axial files into data/axial/ and write manifests/axial.json.

Reads D:\\axial only; never writes there. Run: uv run python src/copy_axial.py
"""

import hashlib
import json
import shutil
from pathlib import Path

SOURCE = Path(r"D:\axial")
ROOT = Path(__file__).resolve().parent.parent
COPY = ROOT / "data" / "axial"
MANIFEST = ROOT / "manifests" / "axial.json"

FIXED = [
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
]


def main():
    chunks = sorted(p.relative_to(SOURCE).as_posix() for p in (SOURCE / "data/gold/chunks").glob("*.json"))
    if len(chunks) != 120:
        raise SystemExit(f"expected 120 chunk files, found {len(chunks)}")
    files = {}
    for rel in FIXED + chunks:
        src, dst = SOURCE / rel, COPY / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        files[rel] = hashlib.sha256(dst.read_bytes()).hexdigest()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"source": str(SOURCE), "files": files}, indent=2) + "\n", encoding="utf-8")
    print(f"copied {len(files)} files; manifest at {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
