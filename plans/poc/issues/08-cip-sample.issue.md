# feat(poc): stratified CIP sample of 200 + 200 with drop counts [slice 08]

**Spec:** [specs/PRD.md#52-cip-set-c-400-items-results-only-publication](https://github.com/Muhanad-husn/decision-model-poc/blob/main/specs/PRD.md#52-cip-set-c-400-items-results-only-publication) · **Plan:** [plans/poc/08-cip-sample.md](https://github.com/Muhanad-husn/decision-model-poc/blob/main/plans/poc/08-cip-sample.md)
**Depends on:** #12 (slice 07)
**Labels:** M4

## Deliverable
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
