# Slice 15: results/metrics.json and chart-ready CSVs from the real runs

**Milestone:** M6 · **Size:** M · **Issue:** #20
**Spec:** [specs/PRD.md#11-build-plan](../../specs/PRD.md#11-build-plan) · **Depends on:** #9 (slice 04), #11 (slice 06), #15 (slice 10), #16 (slice 11), #19 (slice 14)

## Goal
`src/results.py` applies the metrics to the stored runs and writes `results/metrics.json` plus `agreement_by_axis_arm.csv`, `selective_agreement.csv` and `cost_latency.csv`, every figure with its interval. Axial reference is S5-REF, CIP reference the S55 draw majority; PROD-A and PROD-C appear as comparators; PROD-A is left out of theory_school.

## Mechanism
The slice 12 to 14 metrics; stdlib `csv` and `json`.

## Acceptance criterion
Given all runs, when results are built, then every agreement figure and AUROC in metrics.json carries a 95% interval, the CSVs hold no passage or CIP text, the full test suite is green, and PLAN.md M6 turns `done`.

## Files
```aeo-independence
slice: 15-results-files
edits: PLAN.md
creates: src/results.py
creates: tests/test_results.py
creates: results/metrics.json
creates: results/agreement_by_axis_arm.csv
creates: results/selective_agreement.csv
creates: results/cost_latency.csv
depends-on: 04-jev-axial-runs
depends-on: 06-s55-axial-draws
depends-on: 10-jev-cip-runs
depends-on: 11-s55-cip-draws
depends-on: 14-metrics-cost-latency
```

## Out of scope
Bar verdicts (slice 16).
