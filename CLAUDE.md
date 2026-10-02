# decision-model-poc: handbook

This repository tests one claim: that a small decision model (TypeSafe's Jev, pinned
`jev-1.13.0`) can take over the label-picking an LLM does inside an agent pipeline, at a
fraction of the cost, and that its probabilities show the doubt a single LLM answer hides.
It is a proof of concept with a fixed end: `REPORT.md`, `PUBLISH.md` and chart-ready CSVs
under `results/`.

## Where the truth lives

- **The PRD is the spec:** [`specs/PRD.md`](specs/PRD.md), copied from the master at
  `D:\The Merge Seat\research\decision-model-poc\PRD.md`. Every decision in it is taken;
  nothing is open.
- **`bars.json`** holds PRD §8 verbatim once M0 lands. It is frozen by commit before any
  model call and never edited after a result is seen.
- **`RULES.md`** carries the standing rules and the kill line.
- **`PLAN.md`** carries the milestone status table (M0 to M7). Update a row's `State` to
  `done` only when its "Done when" from PRD §11 actually holds.
- **`LEDGER.md`** books TypeSafe spend against the $5.00 credit.
- **`COMMITMENTS.md`** gets one row per session: the closing recommendation, judged at the
  next session start.

## Who may merge

Only the founder (Muhanad) decides a merge. `main` is protected: every change arrives by
pull request, admins included, with no required reviewer count because the founder is
the only reviewer. Claude opens pull requests and never merges one on its own judgement.
When the founder says "approved", "merge it" or equivalent, Claude merges, deletes the
branch locally and remotely, syncs `main` and reports the new SHA.

## When code and spec disagree

The PRD wins over the code, and the code is fixed. If the PRD itself produces an outcome
that is plainly wrong (a bar that cannot be computed as written, a sanity value the
source files cannot produce, a join the schema does not support), do not quietly work
around it: stop, state the conflict with the evidence, and put it to the founder. A bar
that turns out ill-posed is reported as ill-posed in `REPORT.md`, never adjusted.

## The arms

| Arm | Source |
|---|---|
| JEV | `POST https://api.typesafe.ai/v1/systemone` via `typesafe-sdk` (version pinned), key in `TYPESAFE_API_KEY` |
| S55 | Headless `claude -p --output-format json` on the subscription; record the resolved model id, stop if it is not Sonnet 5.5 |
| S5-REF | Existing Sonnet 5 draws copied from `D:\axial` |
| PROD-A | Axial production tagger labels inside the chunk files (not used on `theory_school`) |
| PROD-C | CIP's current production label (`is_current = 1`) |

## Data handling

- `D:\axial` is copied from, never written to. Copies land in `data/axial/` with a SHA-256
  manifest.
- `D:\CIP-data\db\cip.sqlite` is opened only as
  `sqlite3.connect("file:D:/CIP-data/db/cip.sqlite?mode=ro", uri=True)`, exported once to
  `data/cip/`, and all later work reads the export.
- `data/`, `runs/` and `.env` are git-ignored. No passage text, CIP text or key is ever
  committed, pasted into a PR body or quoted in an issue.
- The one Axial exception (passages may go to Jev for this experiment) is recorded as a
  DEC entry in `D:\axial\docs\DECISIONS.md` through that repository's own issue and PR
  route, at M0.

## Spend and pacing

- Jev: running cost from `usage.input_tokens` at $0.042 per million; hard abort past
  $2.00 cumulative. Concurrency 4 at most. Exponential backoff on 429 and 529; handle 401
  and 422 as failures to report.
- S55: paced to stay inside the plan's rate limits; three independent draws as separate
  processes.
- Smoke test (5 items per set, both arms) before every full run, checking parsing and cost.
- Every Jev response is stored raw in `runs/jev/<run_id>/responses.jsonl` with request
  hash, latency and input tokens.

## Building

- Python 3.13 with `uv`. Run tests with `uv run pytest` (recorded in `aeo-tests.json`).
- Metrics live in `src/metrics.py`, each one tested on toy data in `tests/test_metrics.py`.
- M1's test asserts every PRD §5.1 sanity value exactly. If it cannot, the kill line in
  `RULES.md` applies.
- Bootstrap intervals: 2,000 resamples, seed 20261002. Sampling seed is the same.
- Work happens on a branch per milestone or slice, merged by pull request.

## Out of scope

Other decision models, local GPUs, fine-tuning, prompt-injection tests, any change to
Axial or CIP code, any manual labelling.

## Publishing

`PUBLISH.md` follows PRD §10 to the letter: no passage or source text quoted; the first
paragraph says every reference label is an LLM label; CIP appears as results only (no
prompts, code, stage or agent names, schema, DEC numbers or source list); CIP sources are
"the platform's source feeds, open and primary"; any CIP shortfall carries its reason in
the same sentence; no em dash, "OSINT" or "open-source". A grep confirms the last three
before M7 closes.
