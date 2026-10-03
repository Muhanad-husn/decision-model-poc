# decision-model-poc

Can a small decision model take over the label-picking an LLM does inside an agent
pipeline, at a fraction of the cost, with probabilities that show the doubt a single LLM
answer hides? This repository tests that claim, from "The Agent Is the New User"
(1 Oct 2026), on TypeSafe's Jev (`jev-1.13.0`) against Sonnet 5.5 and against the labels
that already exist, scored by bars frozen before any model call.

**Status: completed 3 Oct 2026.** All eight milestones (M0 to M7) are done and no
further runs are planned. **The concept does not hold:** Jev passes on cost and on agreement with Axial's production tagger, but misses the
`theory_school` floor, does not give the same answer twice to identical requests, and on
CIP stays further from Sonnet 5.5 than the bar allows. Every reference label here is an LLM
label, so "agreement" means agreement with another model, not correctness.

## Read this first

| File | What it holds |
|---|---|
| [`REPORT.md`](REPORT.md) | The result: verdict, bar table, Q1 to Q4, caveats, run log. Every figure is checked by `tests/test_report.py`. |
| [`PUBLISH.md`](PUBLISH.md) | The publishable write-up under PRD §10, with worked examples. Gated by `tests/test_publish.py`. |
| [`specs/PRD.md`](specs/PRD.md) | The spec. Every decision in it is taken; where code and PRD disagree, the PRD wins. |
| [`bars.json`](bars.json) | PRD §8 verbatim, frozen at `9be94c8` (PR #3, 2 Oct 2026) before any model call. |
| [`results/`](results/) | `metrics.json` and three chart-ready CSVs: agreement by axis and arm, selective agreement, cost and latency. |
| [`RULES.md`](RULES.md) | Standing rules and the kill line. |
| [`PLAN.md`](PLAN.md) | Milestone status table, each row with the figure that proves it. |
| [`LEDGER.md`](LEDGER.md) | TypeSafe spend against the $5.00 credit: $0.0849 used. |
| [`COMMITMENTS.md`](COMMITMENTS.md) | One closing recommendation per session, judged at the next. |
| [`plans/poc/`](plans/poc/INDEX.md) | The 17 slice plans and their issue bodies. |

## Results at a glance

The concept holds when B1, B1b, B4 and B5 pass and B6 passes on at least two of three CIP
questions. B3 is reported on its own. Intervals are 95% bootstrap (2,000 resamples, seed
20261002); full figures and readings are in [`REPORT.md`](REPORT.md).

| Bar | Pass when | Figure | Result |
|---|---|---|---|
| B1 | JEV ≥ PROD-A − 0.05 on four Axial axes | JEV above PROD-A on all four (0.592 to 0.817 against 0.487 to 0.783) | **pass** |
| B1b | JEV ≥ 0.50 on `theory_school` | 0.486 [0.390, 0.583] | **fail** |
| B3 | Doubt AUROC ≥ 0.70 on `theory_school` | 0.617 [0.512, 0.717] | **fail** (not in verdict) |
| B4 | JEV cost per item ≤ 1/20 of S55 | 0.046 pooled over 520 items; Axial alone 0.078 | **pass** |
| B5 | 100% identical argmax across two runs | Axial 0.892, C1 0.985, C2 0.925, from byte-identical requests | **fail** |
| B6 | JEV ≥ S55 pairwise − 0.10 on two of three CIP questions | 0 of 3 (shortfalls 0.06 to 0.19 below the line) | **fail** |

## What was compared

| Arm | Source |
|---|---|
| JEV | TypeSafe Jev `jev-1.13.0` via `typesafe-sdk` 0.7.2, one call per item carrying all its questions; two runs per set |
| S55 | Sonnet 5.5 through headless `claude -p` on the subscription, 10 items per call; three independent draws per set |
| S5-REF | Sonnet 5 draws from July 2026, copied from Axial; the Axial reference |
| PROD-A | Axial's production tagger (`deepseek-v4-flash`); comparator, not used on `theory_school` |
| PROD-C | CIP's current production label; comparator |

| Set | Items | Questions | Reference |
|---|---|---|---|
| Axial | 120 passages | `field`, `empirical_scope`, `role_in_argument`, `claim_type`, `theory_school` | S5-REF |
| C1 | 200 CIP actors | `actor_type` | majority of three S55 draws |
| C2 | 200 CIP claims | `claim_type`, `claim_subject_type` | majority of three S55 draws |

## Setup

Python 3.13 with [`uv`](https://docs.astral.sh/uv/).

```sh
uv sync
cp .env.example .env        # then fill in TYPESAFE_API_KEY
uv run pytest               # 217 tests here; 143 pass and 18 skip on a fresh clone
```

The S55 arm also needs the `claude` CLI logged in to a subscription. `data/`, `runs/` and
`.env` are git-ignored, so a fresh clone holds the committed results but no passage text or
raw responses. Tests that read `data/axial/`, `data/cip/` or the source repositories skip
when those are absent.

## Pipeline

Each step reads what earlier steps wrote. Run from the repository root.

| Step | Command | Writes |
|---|---|---|
| 1. Copy Axial inputs | `uv run python src/copy_axial.py` | `data/axial/`, `manifests/axial.json` (SHA-256) |
| 2. Build Axial items | `uv run python src/axial_items.py` | `data/axial/items.jsonl`; asserts every PRD §5.1 sanity value |
| 3. Dump CIP schema | `uv run python src/cip_schema_dump.py --db "file:<path>?mode=ro"` | `data/cip/schema.txt` |
| 4. Export CIP pools | `uv run python src/cip_export.py --db "file:<path>?mode=ro"` | `data/cip/c1_pool.jsonl`, `c2_pool.jsonl`, `export_summary.json` |
| 5. Sample CIP items | `uv run python src/cip_sample.py` | `data/cip/c1_items.jsonl`, `c2_items.jsonl`, `SAMPLE.md` |
| 6. Jev run | `uv run python src/jev.py --set {axial,c1,c2} --run-id <id> [--limit 5]` | `runs/jev/<id>/responses.jsonl`, `summary.json` |
| 7. Jev determinism check | `uv run python src/jev.py --set <set> --check <run1> <run2>` | nothing; compares request hashes and validates, no calls |
| 8. S55 draw | `uv run python src/s55.py --set {axial,c1,c2} --run-id <id> --draw {1,2,3} [--limit 5]` | `runs/s55/<id>/draw_<n>/` |
| 9. Metrics | `uv run python src/results.py` | `results/metrics.json` and the three CSVs |

Notes:

- The CIP database is opened only through a read-only URI passed as `--db`; the path is
  never written into source. `data/cip/options.yaml` (the option descriptions) is
  hand-written from CIP's schema artifact and frozen by the SHA-256 in
  `manifests/cip_options.json`; both runners refuse to start on a mismatch.
- `--limit 5` is the smoke run, required on both arms before every full run.
- `s55.py --calibrate` measures the input tokens the CLI adds around a near-empty prompt.
  Every draw opens with that call and aborts past the ceiling of 600.
- `results.py` scores the run ids fixed in its `RUNS` table, the ones listed in the
  `REPORT.md` run log.

## Source

| Module | Role |
|---|---|
| `src/copy_axial.py` | Copies the PRD §5.1 files from Axial, read-only, with a manifest |
| `src/axial_items.py` | One row per passage: reference, draws, contested flag, PROD-A labels |
| `src/codebook.py` | Axial codebook to one choice question per axis; shared by both arms |
| `src/cip_schema_dump.py` | Read-only schema dump; stops on a WAL database it cannot open read-only |
| `src/cip_export.py` | C1 and C2 candidate pools under the LLM-extraction provenance rule |
| `src/cip_sample.py` | Stratified 200 + 200 sample with drop counts, seed 20261002 |
| `src/cip.py` | CIP option descriptions to questions, after the SHA-256 check |
| `src/jev.py` | Jev runner: spend guard, concurrency 4, backoff on 429 and 529, raw response log |
| `src/s55.py` | S55 runner: isolated `claude -p` calls, model-id check, reply parsing rules |
| `src/metrics.py` | The PRD §7 metrics as pure functions, each tested on toy data |
| `src/results.py` | Applies the metrics to the stored runs and writes `results/` |

## Rules that held throughout

The full list is in [`RULES.md`](RULES.md).

- **Kill line.** If the PRD §5.1 sanity values could not be reproduced exactly, or S55
  resolved to a model other than Sonnet 5.5, the work stopped. Neither happened. A failed
  bar is a result, never a reason to stop.
- **Frozen bars.** No bar was edited after a result was seen. Two needed a reading (B4's
  pooling and pricing, B5's argmax); both are recorded in `REPORT.md` and neither changed a
  number.
- **Spend guard.** Jev cost is tracked from `usage.input_tokens` at $0.042 per million,
  with a hard stop at $2.00 cumulative. Actual spend: $0.0849.
- **Read-only sources.** Axial and CIP are copied or exported from, never written to.
- **No text in git.** No passage text, CIP text or key is committed, pasted into a pull
  request or quoted in an issue. The one exception is the worked examples `PUBLISH.md`
  quotes under PRD §10 rule 1.
- **Merges.** `main` is protected; every change arrives by pull request, merged by the
  founder.
