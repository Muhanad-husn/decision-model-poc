# Report

Internal, full. Sections follow PRD §11: verdict, bar table, Q1 to Q4, caveats, run log.
Nothing below the run log is filled until results exist.

## Verdict

Not yet run.

## Bar table

Bars frozen in `bars.json` at commit `9be94c890414eca356a17689fe13c3d7ab1c2c58`
(`9be94c8`, PR #3, 2 Oct 2026), before any model call.

| Bar | Pass when | Result |
|---|---|---|
| B1 | JEV ≥ PROD-A − 0.05 on `claim_type`, `field`, `empirical_scope`, `role_in_argument` | not run |
| B1b | JEV ≥ 0.50 on `theory_school` | not run |
| B3 | AUROC ≥ 0.70 on `theory_school` | not run |
| B4 | JEV cost per item ≤ 1/20 of S55 | not run |
| B5 | 100% identical argmax across two runs, both sets | not run |
| B6 | JEV ≥ S55 pairwise − 0.10, on at least two of three C questions | not run |

## Run log

| Date | Event |
|---|---|
| 2026-10-02 | Bars frozen (`9be94c8`). |
| 2026-10-02 | Axial DEC-77 recorded (Muhanad-husn/axial#885, `c02b94c`). |
| 2026-10-02 | 130 Axial input files copied read-only to `data/axial/`; SHA-256 manifest in `manifests/axial.json`. |
| 2026-10-02 | Jev smoke, 5 Axial items, run `smoke-axial-20261002`: `jev-1.13.0`, typesafe-sdk 0.7.2, 5 of 5 parsed, 27,313 input tokens, $0.0011. |
| 2026-10-02 | S55 smoke, 5 Axial items, run `smoke-20261002c`: `claude-sonnet-5-5` on Claude Code 2.1.288, 0 invalid, harness overhead 462 input tokens (ceiling 600). |
| 2026-10-03 | Jev runs 1 and 2, 120 Axial items each, runs `axial-run1-20261003` and `axial-run2-20261003`: `jev-1.13.0`, typesafe-sdk 0.7.2, 240 of 240 responses valid, request hashes identical item by item (and identical to the smoke run's 5), no retries, 652,448 input tokens and $0.0274 per run; cumulative TypeSafe spend $0.0560. |
