# Report

## Verdict

**The concept does not hold.** Of the four bars that must pass, B1 and B4 pass but B1b fails
(`theory_school` agreement 0.486 against 0.50) and B5 fails (identical argmax on 0.892 of
Axial items, 0.985 of C1 and 0.925 of C2, against 100%). B6 passes on 0 of the 3 C
questions, where two were needed.

B3, reported on its own: Jev's doubt does not flag the contested `theory_school` passages
to the bar. AUROC is 0.617 [0.512, 0.717] against 0.70. On the other questions with a
contested flag it reaches 0.733 (C1 `actor_type`), 0.708 (C2 `claim_subject_type`) and
0.698 (Axial `claim_type`), and sits at chance on C2 `claim_type` (0.526).

What does hold: on the four single-label Axial axes Jev agrees with the reference more
often than Axial's out-of-family production tagger, at under 1/20 of Sonnet 5.5's cost per
item over all 520 items. What does not: it falls short of the 0.50 floor on
`theory_school`, it does not give the same answer twice, and on CIP it sits 0.16 to 0.29
below how often Sonnet 5.5's own draws agree with each other.

## Bar table

Bars frozen in `bars.json` at commit `9be94c890414eca356a17689fe13c3d7ab1c2c58`
(`9be94c8`, PR #3, 2 Oct 2026), before any model call. Every figure comes from
`results/metrics.json`; intervals are 95% bootstrap (2,000 resamples, seed 20261002).
`tests/test_report.py` recomputes each mark and figure from that file and `bars.json`.

| Bar | Pass when | Figure | Result |
|---|---|---|---|
| B1 | JEV ≥ PROD-A − 0.05 on `claim_type`, `field`, `empirical_scope`, `role_in_argument` | JEV against PROD-A: `claim_type` 0.632 vs 0.487, `field` 0.817 vs 0.783, `empirical_scope` 0.792 vs 0.750, `role_in_argument` 0.592 vs 0.575. JEV is above PROD-A on all four, so above the line by 0.067 to 0.195. | **pass** |
| B1b | JEV ≥ 0.50 on `theory_school` | 0.486 [0.390, 0.583] on the 105 items with a reference; the interval spans the line. | **fail** |
| B3 | AUROC ≥ 0.70 on `theory_school` | 0.617 [0.512, 0.717] on 61 contested and 59 unanimous items. Reported on its own; not part of the verdict. | **fail** |
| B4 | JEV cost per item ≤ 1/20 of S55 | 0.046 pooled over all 520 items (JEV $0.080 against S55 $1.756 per 1,000 items, one draw), S55 priced from its logged usage, which is the founder's ruling on PR #33; Axial alone fails at 0.078 because Jev bills the full five-axis codebook (about 5,400 input tokens) on every item while S55 sends it once per batch of 10 from cache, and the pooled ratio is 0.065 with cache writes priced at the 5-minute rate and 0.055 with no caching. | **pass** |
| B5 | 100% identical argmax across two runs, both sets | Axial 0.892 (107 of 120 items identical on all five axes), C1 0.985 (197 of 200), C2 0.925 (185 of 200), from byte-identical requests. | **fail** |
| B6 | JEV ≥ S55 pairwise − 0.10, on at least two of three C questions | 0 of 3 pass. JEV mean agreement with the single S55 draws against the draws' pairwise agreement: `actor_type` 0.712 vs 0.872 (line 0.772), `claim_type` 0.597 vs 0.890 (line 0.790), `claim_subject_type` 0.680 vs 0.937 (line 0.837). | **fail** |

None of the six bars proved ill-posed. Two needed a reading, both settled without changing
a number: B4 names no set and no cache-write price (ruled on PR #33: pooled, logged usage),
and B5's "argmax" can differ from Jev's own `choice` in 7 of 2,000 answers (ties and
0.01 roundings), which leaves every B5 share below 100% either way.

## Q1 Does Jev pick the label an LLM coder picks?

On Axial, against the out-of-family coder: yes on four axes, no on the fifth. Against
Sonnet 5.5 on CIP: no.

| Axial axis | JEV | PROD-A | S55 majority | n |
|---|---|---|---|---|
| `field` | 0.817 [0.750, 0.883] | 0.783 | 0.883 | 120 |
| `empirical_scope` | 0.792 [0.717, 0.867] | 0.750 | 0.717 | 120 |
| `role_in_argument` | 0.592 [0.500, 0.675] | 0.575 | 0.733 | 120 |
| `claim_type` | 0.632 [0.546, 0.716] | 0.487 | 0.684 | 117 |
| `theory_school` | 0.486 [0.390, 0.583] | not used | 0.629 | 105 |

- Jev beats PROD-A on every axis where both exist, by 0.145 on `claim_type`. S55 scores
  higher than Jev on four of five axes, but S55 shares a family with the Sonnet 5
  reference (see Caveats), so that gap is not a clean comparison.
- On `theory_school` Jev's 0.486 is level with the 0.49 two frontier LLMs of different
  families agreed in July, and 0.014 under the bar.
- On CIP the reference is the majority of three S55 draws. Jev agrees with it 0.716
  (`actor_type`), 0.601 (`claim_type`) and 0.690 (`claim_subject_type`). CIP's production
  labels (PROD-C, one LLM extraction draw) agree 0.751, 0.641 and 0.735, 0.035 to 0.045
  above Jev, and also below the B6 line on all three (mean agreement with single draws 0.735,
  0.633, 0.722 against lines of 0.772, 0.790, 0.837). The 0.10 allowance in B6 was set
  for the gap between same-family draws and an outside coder; that gap came out at 0.14 to
  0.26 for PROD-C and 0.16 to 0.29 for Jev.

## Q2 Do Jev's probabilities flag where LLM coders disagree?

Not to the bar on `theory_school`; better on the CIP questions where the draws rarely
split.

| Question | Contested | Unanimous | AUROC |
|---|---|---|---|
| Axial `theory_school` (B3) | 61 | 59 | 0.617 [0.512, 0.717] |
| Axial `claim_type` | 27 | 93 | 0.698 [0.591, 0.796] |
| C1 `actor_type` | 37 | 163 | 0.733 [0.650, 0.804] |
| C2 `claim_type` | 32 | 168 | 0.526 [0.420, 0.636] |
| C2 `claim_subject_type` | 19 | 181 | 0.708 [0.578, 0.819] |

Jev's confidence does sort its own right answers from its wrong ones. Keeping the 70% of
items it is most confident on raises agreement on every question: `field` 0.817 to 0.940,
`empirical_scope` 0.792 to 0.893, `role_in_argument` 0.592 to 0.655, Axial `claim_type`
0.632 to 0.707, `theory_school` 0.486 to 0.595, `actor_type` 0.716 to 0.877, C2
`claim_type` 0.601 to 0.676 and `claim_subject_type` 0.690 to 0.800 (curves in
`results/selective_agreement.csv`). S5-REF's best-of-3 abstention keeps 0.795 of
`claim_type` items and 0.562 of `theory_school` items at 1.000, which holds by construction
because the reference is those draws' majority. Expected calibration error runs from 0.074
(`field`) to 0.130 (C2 `claim_type`).

## Q3 What does each answer cost, and how long does it take?

| Set | JEV $ per 1,000 | S55 $ per 1,000, one draw | Ratio | JEV p50 / p95 ms | S55 p50 / p95 ms |
|---|---|---|---|---|---|
| Axial | 0.228 | 2.911 | 0.078 | 325 / 381 | 369 / 492 |
| C1 | 0.037 | 1.277 | 0.029 | 284 / 332 | 193 / 554 |
| C2 | 0.034 | 1.543 | 0.022 | 282 / 330 | 254 / 608 |
| All 520 | 0.080 | 1.756 | 0.046 | 290 / 357 | 256 / 601 |

- JEV is logged input tokens at $0.042 per million. S55 is each labelling call's logged
  usage at the Sonnet 5.5 list price read on 2026-10-03 from
  https://platform.claude.com/docs/en/about-claude/pricing ($2 input, $2.50 5-minute cache
  write, $4 1-hour cache write, $0.20 cache read, $10 output per million tokens). The
  formula reproduces the cost Claude Code itself reported for every draw.
- Jev's latency is per call, one item per call. S55's is a batch's duration divided by
  its 10 items, as PRD §7 defines it; any one S55 answer waits for its whole batch.
- Axial costs Jev more per item because its codebook criteria go out with every item;
  CIP's option lists are short.

## Q4 Does Jev give the same answer twice?

No. Run 2 sent the same request bytes as run 1 (request hashes identical item by item) and
the argmax moved on 13 of 120 Axial items, 3 of 200 C1 items and 15 of 200 C2 items. The
largest shift in any option's probability was 0.09 on Axial, 0.19 on C1 and 0.14 on C2.
Per question, the identical share runs from 0.950 (C2 `claim_type`) and 0.958
(`theory_school`) to 0.992 (`field`, `empirical_scope`). Reading Jev's own `choice`
instead of the argmax gives 0.883, 0.985 and 0.920: the same answer.

## Caveats

- All reference labels are LLM labels. On Axial they come from Sonnet 5, which shares a
  family with S55, so S55's agreement figures are inflated. Axial measured +0.26 on
  `claim_type` for same-family pairs. JEV and PROD-A carry no such advantage. On CIP the
  reference is S55's own majority, so B6 sets Jev against a coder's agreement with itself.
- n = 120 on Axial. On `claim_type`, batch-to-batch variance (0.20) was larger than any
  effect Axial measured in July. Read the axis-level differences within their intervals:
  Jev's lead over PROD-A on `field`, `empirical_scope` and `role_in_argument` (0.017 to
  0.042) is inside them.
- The reference uses a single draw on `field`, `empirical_scope` and `role_in_argument`,
  so these axes have no contested flag and are left out of B3.
- PROD-A was tagged under an earlier codebook version. The tag ids are unchanged.
- Jev's `confidence` is used as returned. Its definition is TypeSafe's and is not
  reproduced here.
- B4 passes on the pooled ratio with S55 priced from logged usage, which includes Claude
  Code's choice to write the batch prompt to the 1-hour cache. Axial alone, or another
  pricing basis, fails (see the bar table).
- S55 replies needed three parsing rules found in the runs (`prefix_restored`,
  `self_corrected`, `bare_values`). The draws that hit a rule before it existed are not used
  and were rerun under the fixed runner; the C2 draws re-parse to identical labels under it.
  No draw used in the figures has an invalid or re-asked label.

## Run log

Models: Jev `jev-1.13.0` through typesafe-sdk 0.7.2; S55 `claude-sonnet-5-5` on Claude
Code 2.1.288, every call; S5-REF Sonnet 5 (July 2026); PROD-A `deepseek-v4-flash` (July
2026). Spend: TypeSafe $0.0849 of the $5.00 credit, balance $4.9151 (`LEDGER.md`). S55
ran on the subscription; its API-equivalent cost over the nine scored draws is $2.74
(Axial $1.048, C1 $0.766, C2 $0.926), not cash.

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
| 2026-10-03 | Metrics (slices 12 to 15, PRs #29 and #33): `results/metrics.json` and three chart CSVs from the scored runs, no model call; 167 tests green. The runs reproduce the PRD §5.1 contested counts (27/93, 61/59) and pairwise draw agreement (0.842, 0.619). |
| 2026-10-03 | Founder ruling on B4, with PR #33: scored on the pooled ratio over all 520 items, S55 priced from logged usage (PRD §6.2 as written), the Axial-only and other-pricing ratios stated beside it. |
| 2026-10-03 | REPORT.md filled (slice 16): B1 and B4 pass, B1b, B3, B5 and B6 fail; the concept does not hold. $0 TypeSafe. |
