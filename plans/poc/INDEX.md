# Plans index: poc (M1 to M7)

Spec: [specs/PRD.md](../../specs/PRD.md) §11.

| Slice | Milestone | Plan | Depends on | Size | Issue |
|---|---|---|---|---|---|
| 01 | M1 | [build data/axial/items.jsonl and assert every §5.1 sanity value](01-axial-items.md) | - | M | #6 |
| 02 | M2 | [turn the codebook into per-axis criteria and instructions](02-codebook-questions.md) | - | S | #7 |
| 03 | M2 | [Jev runner with spend guard, smoke-run on 5 Axial items](03-jev-runner-smoke.md) | 01, 02 | M | #8 |
| 04 | M2 | [Jev runs 1 and 2 on all 120 Axial items](04-jev-axial-runs.md) | 03, 05 | S | #9 |
| 05 | M3 | [S55 runner on claude -p, smoke-run on 5 Axial items](05-s55-runner-smoke.md) | 01, 02 | M | #10 |
| 06 | M3 | [S55 three independent draws on all 120 Axial items](06-s55-axial-draws.md) | 05, 03 | S | #11 |
| 07 | M4 | [read-only CIP schema dump and export, run by the builder](07-cip-export.md) | - | M | #12 |
| 08 | M4 | [stratified CIP sample of 200 + 200 with drop counts](08-cip-sample.md) | 07 | S | #13 |
| 09 | M4 | [freeze CIP option descriptions in options.yaml before any model call](09-cip-options.md) | - | S | #14 |
| 10 | M5 | [Jev smoke then runs 1 and 2 on C1 and C2](10-jev-cip-runs.md) | 03, 08, 09 | S | #15 |
| 11 | M5 | [S55 smoke then three draws on C1 and C2](11-s55-cip-draws.md) | 05, 08, 09 | S | #16 |
| 12 | M6 | [agreement, kappa and coder agreement with bootstrap intervals](12-metrics-agreement.md) | - | S | #17 |
| 13 | M6 | [contested AUROC, selective agreement, calibration and determinism](13-metrics-doubt.md) | 12 | S | #18 |
| 14 | M6 | [cost per 1,000 items and p50/p95 latency for both arms](14-metrics-cost-latency.md) | 13 | S | #19 |
| 15 | M6 | [results/metrics.json and chart-ready CSVs from the real runs](15-results-files.md) | 04, 06, 10, 11, 14 | M | #20 |
| 16 | M7 | [REPORT.md with verdict, bar table, Q1 to Q4, caveats and run log](16-report.md) | 15 | S | #21 |
| 17 | M7 | [PUBLISH.md under the §10 rules, with the grep gate and founder brief](17-publish.md) | 16 | S | #22 |
