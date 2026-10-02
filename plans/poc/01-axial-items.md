# Slice 01: build data/axial/items.jsonl and assert every §5.1 sanity value

**Milestone:** M1 · **Size:** M · **Issue:** #6
**Spec:** [specs/PRD.md#51-axial-set-a-all-120-passages](../../specs/PRD.md#51-axial-set-a-all-120-passages) · **Depends on:** none

## Goal
`uv run python src/axial_items.py` reads the copied Axial files under `data/axial/` and writes `data/axial/items.jsonl`: one row per passage with id, text, the reference per axis, the three draws (claim_type, theory_school), the single head-partition draw (field, empirical_scope, role_in_argument), the contested flag and the PROD-A labels. A test reproduces every PRD §5.1 sanity value exactly. If any value cannot be reproduced, the kill line in RULES.md applies: stop and report, do not adjust.

## Mechanism
Library: `openpyxl` for `label_sheet.xlsx`, stdlib `json` for draws and chunk files. No model call.

## Acceptance criterion
Given the 130 manifest-verified files in `data/axial/`, when `items.jsonl` is built, then the test asserts exactly: claim_type reference on 117, no majority on 3, unanimous 93, contested 27, pairwise 0.842/0.817/0.867 (mean 0.842); theory_school reference on 105, no majority on 15, unanimous 59, contested 61, pairwise 0.650/0.600/0.608 (mean 0.619); every `*_gold` equals the draw majority where both exist; median passage length 1,441 and maximum 2,964 characters. PLAN.md row M1 turns `done` with that score.

## Files
```aeo-independence
slice: 01-axial-items
edits: pyproject.toml
edits: uv.lock
edits: PLAN.md
creates: src/axial_items.py
creates: tests/test_axial_items.py
```

## Out of scope
Any model call. Any edit to `data/axial/` inputs. PROD-A on theory_school (PRD §5.1 known limits).
