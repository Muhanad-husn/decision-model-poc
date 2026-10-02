"""Build data/axial/items.jsonl from the copied Axial files (PRD §5.1).

One row per passage: id, source, text, the reference per axis, the draws per axis, the
contested flag on the three-draw axes and the PROD-A labels. Verifies every input against
manifests/axial.json first. No model call. Run: uv run python src/axial_items.py
"""

import hashlib
import json
import re
import statistics
from collections import Counter
from itertools import combinations
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
COPY = ROOT / "data" / "axial"
MANIFEST = ROOT / "manifests" / "axial.json"
ITEMS = COPY / "items.jsonl"

GOLD = COPY / "data" / "gold"
SHEET = GOLD / "label_sheet.xlsx"
BLIND = [GOLD / "dispatch" / "out" / f"blind_draw_{n}.json" for n in (1, 2, 3)]
HEAD = [GOLD / "dispatch" / "out" / f"head_partition_{n}_out.json" for n in (1, 2, 3, 4)]

BLIND_AXES = ("claim_type", "theory_school")
HEAD_AXES = ("field", "empirical_scope", "role_in_argument")
AXES = HEAD_AXES + BLIND_AXES
# PRD §5.1 known limits: PROD-A predates `not-applicable`, so it is not used on theory_school.
PROD_A_AXES = ("claim_type",) + HEAD_AXES


def canonical_key(chunk_id):
    """The source hash and chunk suffix. The head-partition files name some sources by
    their older long titles; the 12-hex source hash and the chunk suffix are unchanged."""
    m = re.search(r"([0-9a-f]{12}_\d+_.+)$", chunk_id)
    if not m:
        raise ValueError(f"chunk id without a source hash: {chunk_id!r}")
    return m.group(1)


def majority(draws):
    label, count = Counter(draws).most_common(1)[0]
    return label if count >= 2 else None


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest():
    for rel, digest in _load(MANIFEST)["files"].items():
        if hashlib.sha256((COPY / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{rel} does not match manifests/axial.json")


def build_items():
    verify_manifest()
    rows = list(openpyxl.load_workbook(SHEET, read_only=True)["label_sheet"].iter_rows(values_only=True))
    sheet = [dict(zip(rows[0], r)) for r in rows[1:]]
    blind = [_load(p) for p in BLIND]
    head = {}
    for p in HEAD:
        for chunk_id, labels in _load(p).items():
            key = canonical_key(chunk_id)
            if key in head:
                raise SystemExit(f"{key} appears in two head partitions")
            head[key] = labels
    chunks = {c["chunk_id"]: c for c in map(_load, sorted((GOLD / "chunks").glob("*.json")))}

    ids = {r["chunk_id"] for r in sheet}
    if len(ids) != len(sheet) or any(set(f) != ids for f in [*blind, chunks]) \
            or {canonical_key(i) for i in ids} != set(head):
        raise SystemExit("label sheet, draws and chunk files disagree on chunk ids")

    items = []
    for r in sheet:
        cid, chunk, h = r["chunk_id"], chunks[r["chunk_id"]], head[canonical_key(r["chunk_id"])]
        draws = {a: [b[cid][a] for b in blind] for a in BLIND_AXES}
        draws.update({a: [h[a]] for a in HEAD_AXES})
        items.append({
            "id": cid,
            "source": chunk["source"],
            "text": chunk["chunk_text"],
            "reference": {a: r[f"{a}_gold"] or None for a in AXES},
            "draws": draws,
            "contested": {a: len(set(draws[a])) > 1 for a in BLIND_AXES},
            "prod_a": {a: chunk[a] for a in PROD_A_AXES},
        })
    return items


def sanity(items):
    """The PRD §5.1 sanity values, rounded as the PRD states them."""
    out = {}
    for a in BLIND_AXES:
        draws = [i["draws"][a] for i in items]
        refs = [i["reference"][a] for i in items]
        majorities = [majority(d) for d in draws]
        pairwise = [sum(d[x] == d[y] for d in draws) / len(draws) for x, y in combinations(range(3), 2)]
        out[a] = {
            "reference": sum(r is not None for r in refs),
            "no_majority": sum(m is None for m in majorities),
            "unanimous": sum(len(set(d)) == 1 for d in draws),
            "contested": sum(len(set(d)) > 1 for d in draws),
            "pairwise": [round(p, 3) for p in pairwise],
            "pairwise_mean": round(statistics.mean(pairwise), 3),
            "gold_mismatch": sum(r is not None and m is not None and r != m for r, m in zip(refs, majorities)),
        }
    lengths = [len(i["text"]) for i in items]
    out["median_length"] = statistics.median(lengths)
    out["max_length"] = max(lengths)
    return out


def write_items(items, path=ITEMS):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for i in items:
            f.write(json.dumps(i, ensure_ascii=False) + "\n")


def main():
    items = build_items()
    write_items(items)
    print(f"wrote {len(items)} items to {ITEMS.relative_to(ROOT).as_posix()}")
    print(json.dumps(sanity(items), indent=2))


if __name__ == "__main__":
    main()
