# PRD: Decision-model proof of concept on Axial and CIP data

Version 1.0 · 2 October 2026 · Owner: Muhanad Abulhusn · Builder: Claude Code
Status: approved for build. Every decision in this PRD is taken. Nothing below is open.

---

## 1. Purpose

The article "The Agent Is the New User" (Substack, 1 Oct 2026) claims that a small decision model can take over the picking that LLMs now do inside agent pipelines: it can do this at a fraction of the cost, and it can show the doubt that a single LLM answer hides. This experiment tests those claims on two real decision sets:

- the Axial passage-coding set, which has three independent LLM labels per passage;
- a sample of CIP's actor and claim classifications.

It is a proof of concept. One decision model (Jev) is compared with one current LLM (Sonnet 5.5) and with the labels that already exist.

The results feed:

- the follow-up article, which uses the Axial results in full and CIP results only;
- the CIP evidence line, which uses results only.

## 2. The four questions

| # | Question | Answered by |
|---|---|---|
| Q1 | Does Jev pick the same label an LLM coder picks, often enough to replace it on these tasks? | Agreement with reference labels (B1, B6) |
| Q2 | Do Jev's probabilities flag the passages where LLM coders disagree with each other? | Contested-item detection (B3) |
| Q3 | What does each answer cost, and how long does it take? | Cost and latency per item (B4) |
| Q4 | Does Jev give the same answer twice? | Two identical runs (B5) |

## 3. Scope

**In scope**

- Axial set A: all 120 passages, five coding axes.
- CIP set C:
  - C1, actor type: 200 actors, one question.
  - C2, claim classification: 200 claims, two questions.
- Arms:
  - Jev, through the TypeSafe API.
  - Sonnet 5.5, through the Claude Code subscription.
  - The existing labels.

**Out of scope**

- Other decision models (CLM, Clef, OpenAI Decisions).
- Local GPUs.
- Fine-tuning.
- Prompt-injection tests.
- Any change to Axial or CIP code.
- Any manual labelling.

## 4. Arms

| Arm | What | Access | Notes |
|---|---|---|---|
| **JEV** | TypeSafe Jev, pinned `jev-1.13.0` | `POST https://api.typesafe.ai/v1/systemone`, Python SDK `typesafe-sdk` (pin the installed version), key in `TYPESAFE_API_KEY` | $0.042 per million input tokens, output free. $5 credit on the account. |
| **S55** | Sonnet 5.5 | Headless `claude -p` from a script, `--output-format json`, on the Claude Code subscription | Record the resolved model id from the JSON output. If it is not a Sonnet 5.5 id, stop and report. |
| **S5-REF** | Three existing blind Sonnet 5 draws plus four single-draw partition labels (Axial only) | Files, see §5.1 | Produced July 2026 by dispatched Sonnet 5 subagents (Axial `docs/_archive/gold-coder.md`). |
| **PROD-A** | Axial's production tagger, single draw (`deepseek-v4-flash`, July 2026) | Fields inside `data/gold/chunks/*.json` | This is the out-of-family LLM comparator. |
| **PROD-C** | CIP's production label for each sampled item | CIP production database, read-only | One LLM extraction draw. |

Jev documentation was checked on 2 Oct 2026. The facts that shape the build:

- Each question type has its own fields:
  - `choice` takes `criteria` as an option-to-description map and returns `choice`, `probabilities` and `confidence`.
  - `score` takes ordered levels.
  - `noul` returns a single 0 to 1 value.
- One call carries many questions. The state is billed once and each question is evaluated independently.
- Context is 32k tokens for the state plus the longest question.
- Rate limits are 40 requests per second and 100K tokens per second.
- The errors to handle are 401, 422, 429 and 529. Back off exponentially on 429 and 529.
- No maximum number of questions per call is published. Keep each call within the 32k budget.

Sources: https://docs.typesafe.ai/api.md and https://docs.typesafe.ai/primitives.md.

## 5. Data

### 5.1 Axial set A (all 120 passages)

**Source files.** Copy these from `D:\axial`. Read only, never write back.

| File | Holds |
|---|---|
| `data/gold/label_sheet.xlsx` | 120 rows: `chunk_id`, `chunk_text`, the merged reference columns (`*_gold`) |
| `data/gold/dispatch/out/blind_draw_1.json` ... `_3.json` | Three independent Sonnet 5 draws of `claim_type` and `theory_school`, 120 items each |
| `data/gold/dispatch/out/head_partition_1_out.json` ... `_4_out.json` | Single Sonnet 5 draws of `field`, `empirical_scope` and `role_in_argument`, 30 items each |
| `data/gold/chunks/*.json` (120 files) | Passage text plus the production tagger's labels (PROD-A) |
| `config/domains/syria/codebook.yaml` | Definition, positive example and negative example for every option |
| `docs/_archive/gold-coder.md` | The exact Sonnet 5 coder prompt (reused for S55) |

**Axes.**

| Axis | Options | Reference | Reference draws |
|---|---|---|---|
| `field` | 3 | `field_gold` | 1 |
| `empirical_scope` | 5 | `empirical_scope_gold` | 1 |
| `role_in_argument` | 7 | `role_in_argument_gold` | 1 |
| `claim_type` | 22 | `claim_type_gold` = majority of 3 | 3 |
| `theory_school` | 30 (incl. `not-applicable`, `unlisted`) | `theory_school_gold` = majority of 3 | 3 |

**Sanity values.** Measured 2 Oct 2026 from these files; M1 must reproduce them exactly.

- `claim_type`:
  - reference present on 117 items, no majority on 3;
  - unanimous on 93, contested on 27;
  - pairwise draw agreement 0.842, 0.817, 0.867 (mean 0.842).
- `theory_school`:
  - reference present on 105 items, no majority on 15;
  - unanimous on 59, contested on 61;
  - pairwise draw agreement 0.650, 0.600, 0.608 (mean 0.619).
- Wherever both exist, the `*_gold` column equals the majority of the three draws on every item.
- Median passage length is 1,441 characters; the maximum is 2,964.

**Known limits of PROD-A.**

- 112 of the 120 chunks were tagged before `not-applicable` existed as a `theory_school` value, so PROD-A is not used on `theory_school`.
- PROD-A was tagged under an earlier codebook version. The tag ids are unchanged across versions.

### 5.2 CIP set C (400 items, results-only publication)

**Source.** The production SQLite database at `D:\CIP-data\db\cip.sqlite`.

- Open it read-only only: `sqlite3.connect("file:D:/CIP-data/db/cip.sqlite?mode=ro", uri=True)`.
- Never write, migrate or vacuum it.
- Export once to `data/cip/` and work only from the export.

**Tasks.**

| Task | State given to the model | Question(s) | Options |
|---|---|---|---|
| C1 actor type | Actor name plus one English source passage that mentions it (≤1,500 chars) | `actor_type` | 16: state, government, military, police, rebel_group, political_militia, ethnic_militia, religious_militia, criminal_group, political_party, international_organization, ngo, media_organization, civilian_group, private_military, unattributed |
| C2 claim | Claim text plus its English source passage (≤1,500 chars) | `claim_type` and `claim_subject_type` | 8: factual_assertion, attribution, denial, threat, announcement, accusation, justification, other. And 7: event_occurrence, casualty_count, actor_involvement, weapon_use, territorial_control, policy_intent, other |

**Option descriptions.**

- Take the one-line meaning of each option from CIP's own enum documentation.
- If none exists, write a neutral one-line description per option.
- Freeze all descriptions in `data/cip/options.yaml` before any model call.
- The same descriptions go to JEV and S55.

**Sampling.**

- Draw only from records whose label came from LLM extraction of free text. Exclude structured feeds that carry coded labels (for example ACLED, GDELT, UCDP, FIRMS, ADS-B, OpenSky). Use the provenance fields in the database to decide; record the rule used in `data/cip/SAMPLE.md`.
- Use the current assertion value (`is_current = 1`) as PROD-C.
- Stratify by PROD-C label:
  - up to 25 items per class;
  - fill the remainder at random to 200 per task;
  - seed 20261002.
- Drop items whose source passage is not English or is under 80 characters, and record how many were dropped.
- If C1 cannot be linked to a source passage through the event edges, stop and report the schema gap. Do not guess a join.

**Reference for C.** The majority of three S55 draws. PROD-C is a second comparator.

**Exposure.** The same passages already go to an API model through OpenRouter in production, so sending them to Jev adds no new kind of exposure.

## 6. Method

### 6.1 Jev calls

**One call per item.** Every question for that item goes in the call: five on Axial, one on C1, two on C2.

The **state** is the passage text as a plain string, with no title, source name or metadata. Axial measured that adding source context does not help: −0.01 on `theory_school` and +0.03 on `claim_type`.

**Criteria** for each option, built from the codebook:

```
"<option_id>": "<definition> Example: <positive_example> Not this: <negative_example>"
```

**Instructions** for each question: one sentence naming the axis, plus the axis's decision rule from the codebook:

- `theory_school`: decide `not-applicable` first; `unlisted` means a real school that is not listed.
- `empirical_scope`: choose the most specific level the claims rest on.

The same text goes into the S55 prompt.

**Example (Axial, shortened):**

```json
{"model": "jev-1.13.0",
 "state": "<passage text>",
 "questions": {
   "field": {"type": "choice", "instructions": "Which field is the object of this passage's explanation?",
             "criteria": {"state": "The state as object: ... Not this: ...", "violence": "...", "ideology": "..."}},
   "theory_school": {"type": "choice", "instructions": "...", "criteria": {"...": "..."}}
 }}
```

**Logging and runs.**

- Store the full raw response for every call in `runs/jev/<run_id>/responses.jsonl`, together with the request hash, wall-clock latency and `usage.input_tokens`.
- Run every set twice (run 1 and run 2) with identical requests.

### 6.2 S55 calls

- Reuse the gold-coder prompt from Axial `docs/_archive/gold-coder.md`. Merge the blind-axis and head-axis variants so that one call labels all of an item's questions.
- Inline the codebook (or `options.yaml`) and a batch of 10 items in the prompt. No tool use and no file reads.
- The output is one JSON object per item: `{id: {axis: label, ...}}`.
- Run three independent draws per set, as separate processes with no shared context.
- Log `duration_ms`, `usage` and the resolved model id for every call.
- Validate every label against the option list:
  - re-ask an invalid item once, alone;
  - if it is still invalid, record it as `invalid` (counts as a miss).
- Compute the API-equivalent cost from the logged token usage at the published Sonnet 5.5 list price on the run date. Cite the pricing page URL in the report.
- Report harness overhead tokens separately if the JSON output exposes them.

### 6.3 Freeze before running

At M0, before any model call:

1. Write `bars.json`, holding §8 verbatim.
2. Commit it.
3. Write the commit hash into `REPORT.md`.

The bars are not edited after any result is seen. A bar that turns out to be ill-posed is reported as such, not adjusted.

## 7. Metrics

All metrics are computed by `src/metrics.py`. The tests in `tests/test_metrics.py` cover each one on toy data.

| Metric | Definition |
|---|---|
| Agreement | Share of items where the arm's label equals the reference, over items with a reference. Also report Cohen's kappa. |
| Coder agreement | Mean agreement of the arm with each individual reference draw, set beside the mean pairwise agreement among the draws |
| Contested flag | An item is contested when its three draws are not unanimous (2-1 or no majority). Uses S5-REF on Axial and S55 on C. |
| AUROC (doubt) | AUROC of `1 − confidence` from Jev predicting contested vs unanimous |
| Selective agreement | Agreement on the items Jev answers with confidence ≥ t, at 90%, 80% and 70% coverage. Set beside S5-REF's best-of-3 abstention on Axial. |
| Calibration | Brier score of Jev's probability vector against the one-hot reference. ECE over 10 bins, reported only for axes with ≥100 referenced items. |
| Determinism | Share of items with an identical argmax in run 1 and run 2; maximum absolute difference in probabilities |
| Cost per 1,000 items | JEV: logged input tokens × $0.042 / 1M. S55: API-equivalent (§6.2). |
| Latency | p50 and p95 per item. JEV: per call. S55: batch duration ÷ batch size. |

**Confidence intervals.** Give 95% bootstrap intervals (2,000 resamples, seed 20261002) for every agreement figure and every AUROC.

## 8. Pre-registered bars

| Bar | Test | Pass when |
|---|---|---|
| B1 | Axial parity with an out-of-family LLM coder | On each of `claim_type`, `field`, `empirical_scope` and `role_in_argument`, JEV agreement with the reference ≥ PROD-A agreement − 0.05 |
| B1b | Axial `theory_school` | JEV agreement with the reference ≥ 0.50 (two frontier LLMs of different families agreed 0.49 on this axis in July) |
| B3 | Doubt flag | AUROC ≥ 0.70 on Axial `theory_school` (61 contested, 59 unanimous) |
| B4 | Cost | JEV cost per item ≤ 1/20 of S55's API-equivalent cost per item for a single draw |
| B5 | Determinism | 100% identical argmax across the two runs on both sets |
| B6 | CIP parity | On each C question, JEV mean agreement with the individual S55 draws ≥ the S55 mean pairwise draw agreement − 0.10 |

**Verdict line.**

- The concept **holds** when B1, B1b, B4 and B5 pass, and B6 passes on at least two of the three C questions.
- B3 is reported as its own finding, whatever the verdict.

**Why the tolerances differ.**

- Each 0.05 tolerance is about the size of the bootstrap interval at n = 120.
- B6 allows 0.10 because S55 draws agree with each other more than an outside coder can. Axial measured the gap: same-family agreement 0.75 against cross-family 0.49 on `claim_type`.

## 9. Budget and guards

**Jev**

- Expected: about 7k input tokens per Axial call (the codebook criteria dominate) and about 2.5k per CIP call.
- Two runs of each set come to roughly 3.7M tokens, or about $0.16.
- Hard stop: the script keeps a running cost from `usage` and aborts when the cumulative cost passes **$2.00**.
- Concurrency is 4 at most.

**S55**

- 36 calls for Axial (12 batches × 3 draws) and 120 for CIP.
- These run on the subscription. Pace them so the work does not hit the plan's rate limits.

**Smoke test.** Run 5 items per set through both arms and check the parsing and the cost before any full run.

## 10. Data handling and disclosure

**Working directory.** Create `D:\decision-model-poc\` as a fresh private git repo, with a `uv` project on Python 3.13.

Git-ignore:

- `data/`
- `runs/`
- `.env`

No passage text, CIP text or key is ever committed.

**This PRD.** The copy in the working directory is `specs/PRD.md`, taken from the master at `D:\The Merge Seat\research\decision-model-poc\PRD.md`.

**Axial exception.** Founder decision 2 Oct 2026: for this experiment only, the 120 passages may go to Jev, as an exception to Axial's rule that verbatim passage text never leaves the harness for an external model in the gold workstream. At M0, record it as a DEC entry in `D:\axial\docs\DECISIONS.md` through the repo's normal issue and PR route.

**Publishing rules**, applying to `PUBLISH.md` and anything quoted from it:

1. Never quote a passage or a source text. Refer to items by count and label only.
2. **Axial:**
   - may be described in full: method, codebook axes and options, metrics, model ids, costs;
   - is never described as validated by human experts. Every reference label is an LLM label; say so in the first paragraph.
3. **CIP, results only:**
   - May be stated:
     - the classification problem in plain words (task, option list, n, class distribution);
     - the metrics;
     - model ids;
     - costs.
   - Never published:
     - prompts or code;
     - pipeline stage or agent names;
     - schema file names;
     - DEC numbers;
     - database structure;
     - the source list.
   - Describe sources as "the platform's source feeds, open and primary". Never use "open-source" or "OSINT" for CIP.
   - Any CIP figure that reads as a shortfall carries its reason in the data, in the same sentence. Example: short news items name an actor without saying what kind of actor it is.
4. No em dashes in `PUBLISH.md`.

## 11. Build plan

| Milestone | Work | Done when |
|---|---|---|
| M0 Setup | Repo, `uv`, `.gitignore`, `.env` template, copy the §5.1 files into `data/axial/` with a SHA-256 manifest, freeze `bars.json`, file the Axial DEC entry | Manifest committed; `bars.json` commit hash recorded |
| M1 Axial items | Build `data/axial/items.jsonl` with: id, text, the reference per axis, the three draws, the contested flag, PROD-A labels | Every sanity value in §5.1 reproduced exactly; the test asserts them |
| M2 JEV on Axial | Smoke run (5 items), then runs 1 and 2 on all 120 | 240 valid responses; cost logged |
| M3 S55 on Axial | Smoke run, then three draws | 360 item-labels; invalid labels listed |
| M4 CIP export | Read-only export, sampling, `options.yaml`, `SAMPLE.md` | 200 + 200 items; drop counts recorded |
| M5 CIP runs | JEV runs 1 and 2, then S55 × 3, on C1 and C2 | All responses valid or listed |
| M6 Metrics | `src/metrics.py` with tests; `results/metrics.json`; chart-ready CSVs: agreement by axis and arm, selective-agreement curve, cost and latency | Tests green; every figure carries its interval |
| M7 Report | `REPORT.md` (internal, full) and `PUBLISH.md` (Axial in full, CIP results only, §10 rules applied); verdict line first | Every bar marked pass or fail with its number. A grep finds no em dash, "OSINT" or "open-source" in `PUBLISH.md` |

**`REPORT.md` order.**

1. Verdict.
2. Bar table.
3. Q1 to Q4, one short section each.
4. Caveats.
5. Run log: dates, model ids, SDK version, spend.

## 12. Caveats the report must state

- All reference labels are LLM labels. On Axial they come from Sonnet 5, which shares a family with S55, so S55's agreement figures are inflated. Axial measured +0.26 on `claim_type` for same-family pairs. JEV and PROD-A carry no such advantage.
- n = 120 on Axial. On `claim_type`, batch-to-batch variance (0.20) was larger than any effect Axial measured in July. Read the axis-level differences within their intervals.
- The reference uses a single draw on `field`, `empirical_scope` and `role_in_argument`, so these axes have no contested flag and are left out of B3.
- PROD-A was tagged under an earlier codebook version.
- Jev's `confidence` is used as returned. Its definition is TypeSafe's and is not reproduced here.

## 13. Deliverables to the founder

1. `REPORT.md` and `PUBLISH.md` in `D:\decision-model-poc\`.
2. `results/` CSVs, ready for the article charts.
3. A one-paragraph brief: verdict, the B3 finding, and spend against the $5 credit.
