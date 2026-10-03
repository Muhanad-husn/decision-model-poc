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
| 2026-10-03 | S55 draw 1 under run `axial-20261003` stopped after 2 batches: the model wrote `role_in_argument` without its `role:` prefix, so every item was re-asked alone, breaking the 12-batch design. The runner now maps an option id missing only its prefix onto that option and counts it (`prefix_restored`); the stopped draw is not used. |
| 2026-10-03 | S55 draws 1 to 3, 120 Axial items each, run `axial-20261003b`: every call `claude-sonnet-5-5` on Claude Code 2.1.288, 12 batches per draw (36 calls plus 3 calibration calls), 0 re-asked, 0 invalid of 360 item-labels; prefixes restored 100, 140, 140; harness overhead 462, 460, 461 input tokens (ceiling 600). |
| 2026-10-03 | CIP export (slice 07, `src/cip_export.py`, read-only URI): C1 pool 3,869 actors, C2 pool 41,293 claims. Provenance rule: the record was created by one of CIP's LLM extraction agents (the database holds no finer per-label provenance), and no coded feed is involved: an event sourced by a coded feed (PRD §5.2 list; 3,446 events) is never a passage, an actor with an ACLED or UCDP id is out, and a claim made by or asserting an event from a coded feed is out. Excluded: C1 2,391 no event edge, 429 no passage naming the actor, 107 coded-feed events only; C2 94 coded feed, 3 no passage. C2 PROD-C is the claim row's value, since CIP keeps no assertions for `claim_type` or `claim_subject_type`. |
| 2026-10-03 | CIP option descriptions frozen: `data/cip/options.yaml`, SHA-256 `4ea083d1…` in `manifests/cip_options.json`. 31 ids from CIP's schema artifact; 4 meanings from CIP, 27 neutral one-liners. |
| 2026-10-03 | Founder rulings on PRD §5.2 sampling, which cannot hold as written (16 actor_type classes of up to 25 make 372 C1 items, not 200): every class takes the largest equal quota under 25 that fits 200, then random fill; C2 is stratified by `claim_type`; a passage over 1,500 characters makes it ineligible and is counted, not truncated. |
| 2026-10-03 | CIP sample (slice 08, `src/cip_sample.py`, seed 20261002, langid on the passage): C1 200 items, quota 13 per class (`ethnic_militia` 4 of 4), 199 stratified + 1 fill; dropped 232 over 1,500, 13 under 80, 1 not English. C2 200 items, 25 per `claim_type` class, no fill; dropped 1,322 no label, 4,772 over 1,500, 304 under 80, 196 not English. Two runs gave byte-identical item files. |
| 2026-10-03 | CIP runners (slices 10, 11): `src/cip.py` builds the C1 (`actor_type`) and C2 (`claim_type`, `claim_subject_type`) questions from `options.yaml` after checking its SHA-256 against `manifests/cip_options.json`; both runners refuse before any call on a mismatch. State is the actor name or claim text, then the passage. Jev now maps an option id missing only its prefix onto that option, the S55 rule, through one shared helper. |
| 2026-10-03 | CIP smoke, 5 C1 + 5 C2 items, both arms, before any full run. Jev runs `smoke-c1-i15-20261003`, `smoke-c2-i15-20261003`: 10 of 10 parsed, 8,340 input tokens, $0.0004. S55 runs `smoke-c1-i16-20261003`, `smoke-c2-i16-20261003`: `claude-sonnet-5-5`, 0 invalid, 0 re-asked, harness overhead 462 and 461 input tokens. |
| 2026-10-03 | Jev runs 1 and 2, 200 C1 + 200 C2 items each, runs `c1-run1-i15-20261003`, `c2-run1-i15-20261003`, `c1-run2-i15-20261003`, `c2-run2-i15-20261003`: `jev-1.13.0`, typesafe-sdk 0.7.2, 800 of 800 responses valid, request hashes identical item by item across runs (and to the smoke's 10), no retries, 0 prefixes restored; 177,070 (C1) and 163,151 (C2) input tokens per run, $0.0143 per run; cumulative TypeSafe spend $0.0849. |
| 2026-10-03 | S55 C1 draw 1 under run `c1-i16-20261003` is not used. In 3 of its 20 batch replies the model wrote its JSON object, a correction note, then a second object; the parser read none of them, so 30 items were re-asked alone, and 11 of those got a label other than the model's corrected batch answer. One reply also gave bare option ids on the one-question task. The runner now reads a reply's later objects as overriding the items they name (`self_corrected`) and, with one question only, a bare option id as that label (`bare_values`). The draw 2 started under that run was stopped after 10 calls. Re-parsing the raw replies of the three C2 draws under the new rule gives identical labels, 600 of 600. |
| 2026-10-03 | S55 draws 1 to 3, 200 C2 items each, run `c2-i16-20261003`, and 200 C1 items each, run `c1-i16-20261003b`: every call `claude-sonnet-5-5` on Claude Code 2.1.288, 21 calls per draw (calibration plus 20 batches), 0 re-asked, 0 invalid of 1,200 item-labels, 0 prefixes restored; C1 replies self-corrected 0, 2, 0 and bare values 10, 10, 0; harness overhead 461 or 462 input tokens per draw (ceiling 600). |
