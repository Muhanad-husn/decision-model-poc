# Slice 08: stratified CIP sample of 200 + 200 with drop counts

**Milestone:** M4 · **Size:** S · **Issue:** #13
**Spec:** [specs/PRD.md#52-cip-set-c-400-items-results-only-publication](../../specs/PRD.md#52-cip-set-c-400-items-results-only-publication) · **Depends on:** #12 (slice 07)

## Goal
From the export only: drop items whose passage is not English or under 80 characters (counted), stratify by PROD-C label (up to 25 per class), fill at random to 200 per task with seed 20261002, write the C1 and C2 item files and `data/cip/SAMPLE.md` recording the provenance rule and the drop counts. SAMPLE.md stays in the git-ignored `data/cip/`; the provenance rule and the drop counts are copied into REPORT.md (internal).

## Mechanism
Stdlib `random` with the fixed seed; the passage language field if the export carries one, else a language-detection library chosen in the plan.

## Acceptance criterion
Given the export, when sampling runs twice, then it yields the identical 200 C1 and 200 C2 items both times, no class exceeds 25 before the random fill, and the drop counts appear in SAMPLE.md and REPORT.md's run log. PLAN.md M4 turns `done` once slice 09 has also landed.

## Files
```aeo-independence
slice: 08-cip-sample
edits: pyproject.toml
edits: uv.lock
edits: REPORT.md
edits: PLAN.md
creates: src/cip_sample.py
creates: tests/test_cip_sample.py
depends-on: 07-cip-export
```

## Out of scope
Option descriptions (slice 09).

## Founder rulings (2026-10-03)
PRD §5.2's "up to 25 per class, fill the remainder to 200" cannot hold on C1: 16 actor_type
classes of up to 25 make 372 eligible items. Ruled: every class takes the largest equal quota
k <= 25 whose strata fit 200 (13 on C1), then random fill. C2 is stratified by `claim_type`
(8 x 25 = 200, no fill). A passage over 1,500 characters (the PRD §5.2 task-table cap) makes it
ineligible and is counted beside the non-English and under-80 drops, not truncated. The
passage language is detected with langid, since the export's language fields describe the
source and the original claim, not the passage.
