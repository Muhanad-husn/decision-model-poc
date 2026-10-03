# Plan

Milestones from PRD §11. The oracle is a key and rubric: the pre-registered bars in PRD §8
(frozen in `bars.json` at M0), scored against the existing reference labels on Axial and
the majority of three S55 draws on CIP. A phase turns `done` only when its "Done when"
holds; the score column carries the measured figure that proves it.

## Status

| Phase | State | Score |
|---|---|---|
| 0 M0 Setup | done | 130-file manifest committed; bars.json frozen at 9be94c8 |
| 1 M1 Axial items | done | every §5.1 sanity value reproduced, asserted by tests/test_axial_items.py |
| 2 M2 JEV on Axial | done | 240 of 240 valid, request hashes identical across runs; $0.0548 booked (`jev.py --check`) |
| 3 M3 S55 on Axial | done | 360 item-labels, 0 invalid, every call `claude-sonnet-5-5` (run `axial-20261003b`) |
| 4 M4 CIP export | done | 200 C1 + 200 C2 items, identical across two runs; drop counts in REPORT.md run log; options.yaml frozen by SHA-256 |
| 5 M5 CIP runs | done | Jev 800 of 800 valid, request hashes identical across runs; S55 1,200 item-labels, 0 invalid, every call `claude-sonnet-5-5`; spend $0.0849 cumulative |
| 6 M6 Metrics | done | 167 tests green; every agreement figure and AUROC in `results/metrics.json` carries its 95% interval; §5.1 contested and pairwise values reproduced from the runs |
| 7 M7 Report | open | REPORT.md: every bar marked with its number, checked by tests/test_report.py (B1, B4 pass; B1b, B3, B5, B6 fail; the concept does not hold); PUBLISH.md and its grep gate open |

## Bars (PRD §8, summary)

B1 Axial parity with PROD-A (−0.05) on four axes · B1b `theory_school` ≥ 0.50 ·
B3 doubt AUROC ≥ 0.70 on `theory_school` · B4 JEV cost ≤ 1/20 of S55 ·
B5 100% identical argmax across two runs · B6 CIP parity with S55 draws (−0.10).
The concept holds when B1, B1b, B4 and B5 pass and B6 passes on at least two of three C
questions. B3 is reported on its own whatever the verdict.
