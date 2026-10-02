# Slice 16: REPORT.md with verdict, bar table, Q1 to Q4, caveats and run log

**Milestone:** M7 · **Size:** S · **Issue:** #21
**Spec:** [specs/PRD.md#11-build-plan](../../specs/PRD.md#11-build-plan) · **Depends on:** #20 (slice 15)

## Goal
REPORT.md filled in PRD §11 order: verdict line first, every bar marked pass or fail with its number from `results/metrics.json`, Q1 to Q4 one short section each, the five §12 caveats, and the run log (dates, model ids, SDK version, spend). An ill-posed bar is reported as ill-posed.

## Mechanism
Written from `results/metrics.json`; a test reads the bar table and checks each figure against the JSON.

## Acceptance criterion
Given results, when the report test runs, then all six bars show pass or fail with the number that decided it, the verdict follows the PRD §8 rule from those marks, and each §12 caveat is present.

## Files
```aeo-independence
slice: 16-report
edits: REPORT.md
creates: tests/test_report.py
depends-on: 15-results-files
```

## Out of scope
The public write-up (slice 17).
