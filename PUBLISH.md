# Can a small decision model take over an LLM's label-picking?

**Verdict: the concept does not hold.** TypeSafe's decision model Jev (`jev-1.13.0`) was given
the label-picking an LLM does inside an agent pipeline, on 120 passages from Axial and 400
items from CIP, against six bars written down before any model was called. It answers at
under 1/20 of Sonnet 5.5's cost per item and agrees with Axial's reference more often than
Axial's own production tagger on four of five axes, but it misses the floor on the fifth axis
(`theory_school`), it does not give the same answer twice to identical requests, and on CIP it
stays further from Sonnet 5.5 than the bar allows, because many CIP items fit two of the
offered options at once and Jev and Sonnet 5.5 resolve that overlap differently. Every
reference label in this study is an LLM label, not a human expert's, so "agreement" below
means agreement with another model, not correctness.

## What was tested

The claim under test, from "The Agent Is the New User" (1 Oct 2026): a small decision model
can do the picking LLMs now do in agent pipelines, at a fraction of the cost, and its
probabilities show the doubt that a single LLM answer hides. Four questions:

- **Q1** Does Jev pick the label an LLM coder picks, often enough to replace it?
- **Q2** Do Jev's probabilities flag the items where LLM coders disagree with each other?
- **Q3** What does each answer cost, and how long does it take?
- **Q4** Does Jev give the same answer twice?

| Arm | What | Used on |
|---|---|---|
| JEV | TypeSafe Jev `jev-1.13.0` through the TypeSafe API (typesafe-sdk 0.7.2); one call per item carrying every question for that item; $0.042 per million input tokens, output free | both sets, two runs |
| S55 | Sonnet 5.5 (`claude-sonnet-5-5` on every call) through Claude Code 2.1.288, headless, on a subscription; 10 items per call; three independent draws | both sets |
| S5-REF | Sonnet 5, July 2026: three independent draws on `claim_type` and `theory_school`, one draw on the other three axes | Axial reference |
| PROD-A | Axial's production tagger, `deepseek-v4-flash`, one draw, July 2026 | Axial comparator |
| PROD-C | CIP's production label, one LLM draw | CIP comparator |

The bars were frozen in the repository at commit `9be94c8` on 2 Oct 2026, before the first
model call, and none was changed after a result was seen. Every interval below is a 95%
bootstrap interval (2,000 resamples, seed 20261002).

## Bar table

The concept holds when B1, B1b, B4 and B5 pass and B6 passes on at least two of three CIP
questions. B3 is reported on its own whatever the verdict.

| Bar | Pass when | Figure | Result |
|---|---|---|---|
| B1 | JEV ≥ PROD-A − 0.05 on `claim_type`, `field`, `empirical_scope`, `role_in_argument` | JEV against PROD-A: `claim_type` 0.632 vs 0.487, `field` 0.817 vs 0.783, `empirical_scope` 0.792 vs 0.750, `role_in_argument` 0.592 vs 0.575. JEV is above PROD-A on all four. | **pass** |
| B1b | JEV ≥ 0.50 on `theory_school` | 0.486 [0.390, 0.583] on the 105 items with a reference; the interval spans the line. | **fail** |
| B3 | Doubt AUROC ≥ 0.70 on `theory_school` | 0.617 [0.512, 0.717] on 61 contested and 59 unanimous items. Reported on its own; not part of the verdict. | **fail** |
| B4 | JEV cost per item ≤ 1/20 of S55 | 0.046 pooled over all 520 items (JEV $0.080 against S55 $1.756 per 1,000 items, one draw), S55 priced from its logged usage. Axial alone fails at 0.078, because Jev bills the full five-axis codebook (about 5,400 input tokens) on every item while S55 sends it once per batch of 10 from cache. With cache writes priced at the 5-minute rate the pooled ratio is 0.065, and with no caching 0.055. | **pass** |
| B5 | 100% identical argmax across two runs, both sets | Axial 0.892 (107 of 120 items identical on every question), C1 0.985 (197 of 200), C2 0.925 (185 of 200), from byte-identical requests; on CIP the answer moved because those items sat on a near-tie, with a median gap of 0.03 between Jev's top two options against 0.58 or more on the items that held. | **fail** |
| B6 | JEV ≥ S55 pairwise − 0.10, on at least two of three CIP questions | 0 of 3 pass. JEV mean agreement with single S55 draws against the draws' agreement with each other: `actor_type` 0.712 vs 0.872 (line 0.772), `claim_type` 0.597 vs 0.890 (line 0.790), `claim_subject_type` 0.680 vs 0.937 (line 0.837). It falls short because its misses gather on options that overlap (see CIP results), and CIP's own production labels, also one LLM draw, fall below the same lines at 0.735, 0.633 and 0.722. | **fail** |

## Axial

**The set.** All 120 passages of Axial's passage-coding set: extracts from 27 scholarly
works on the state, violence and ideology, published 1978 to 2026, the largest share (37
passages) from the four volumes of Michael Mann's *The Sources of Social Power*, with others
from Kalyvas, Malešević, Hall, Heydemann, Ayubi, Caspersen, Gellner, Bayat and Tilly among
them. Passages run to a median of 1,441 characters, the longest 2,964. Each is coded on five
axes from Axial's codebook, which gives every option a definition, a positive example and a
negative example.

| Axis | Options | Reference |
|---|---|---|
| `field` | 3: state, violence, ideology | one Sonnet 5 draw |
| `empirical_scope` | 5: general, comparative, regional, country-case, sub-national | one Sonnet 5 draw |
| `role_in_argument` | 7: setup, claim, evidence, counter-position, synthesis, methodological, digression | one Sonnet 5 draw |
| `claim_type` | 22: state-formation, state-capacity, state-autonomy, state-society-relations, legitimacy-and-legitimation, sovereignty-and-recognition, statehood-gradations, violence-logic, violence-actors, civilian-targeting, mobilization-and-recruitment, war-and-state, nationalism-theory, identity-and-group-formation, ideology-as-system, ideology-as-practice, legitimating-narratives, religion-and-politics, power-typology, revolution-and-contention, comparative-method, normative-political-theory | majority of three Sonnet 5 draws; present on 117 items |
| `theory_school` | 30: colonial-postcolonial, marxist-political-economy, cultural-ideational, bellicist, neo-bellicist, external-statebuilding, neo-marxist, modernization-developmental, institutionalist-state-centered, structuralist, state-in-society, constructivist, opportunity-feasibility, constructivist-anti-essentialist, biological-evolutionary, structural-violence, civilizing-decline, state-centered-organizational, micro-sociological, interpretive-constructivist, marxist-critical-pol-econ, postcolonial-decolonial, criminological, materialist, systematic, discursive, historical-sociological, subject-centered, not-applicable, unlisted | majority of three Sonnet 5 draws; present on 105 items |

An item is contested where the three draws do not all agree: 27 of 120 on `claim_type`, 61
on `theory_school`. The draws agree with each other 0.842 of the time on `claim_type` and
0.619 on `theory_school`.

**What a hard case looks like.** Three passages:

- A passage from a 2006 volume on Mann's work opens: "Mann's basic argument is that contra
  Marxism, militarism does not derive from capitalism or social processes, but from the logic
  of inter-state geopolitics", and goes on to show how close this runs to neorealism. All
  three Sonnet 5 draws give `claim_type` war-and-state. On `theory_school` they split three
  ways (unlisted, bellicist, structuralist), so the passage has no reference label. Jev
  answers unlisted at 0.58, bellicist 0.28, structuralist 0.12: its probability falls on the
  same three schools the draws picked.
- A passage from Kalyvas's 2006 study of civil war is, in full: "This decision was often
  induced by violence (used by competing guerrilla bands) and reinforced by schooling through
  a concerted school-building effort made by the various Balkan states." What the decision
  was is in the sentence before, which no coder saw. All three draws give `claim_type`
  identity-and-group-formation, but on `theory_school` they give micro-sociological,
  constructivist-anti-essentialist and not-applicable. Jev gives
  constructivist-anti-essentialist 0.37 and bellicist 0.30.
- A passage from Bayat (2017) compares the 2011 Egyptian and Tunisian uprisings with
  Georgia's and Ukraine's colour revolutions and asks whether they were reform or revolution.
  Two draws say unlisted, one not-applicable, so the reference is unlisted. Jev agrees, but
  at 0.25 against 0.24 for opportunity-feasibility: right, and nearly a coin toss.

`theory_school` is the axis where the July coders themselves disagreed most, and it is the
axis where Jev misses the bar.

**Method.** Jev received the passage text alone as its state, with no title or source. Each
option's criterion was its codebook definition, positive example and negative example; each
question carried one sentence naming the axis plus the codebook's decision rule for it
(`theory_school`: decide `not-applicable` first, and `unlisted` means a real school that is not
listed; `empirical_scope`: choose the most specific level the claims rest on). S55 received
the same coder prompt the July Sonnet 5 reference was produced with, the codebook inline, and
10 passages per call, with no tools. Jev ran twice with identical request bytes; S55 ran three
draws as separate processes with no shared context. PROD-A was tagged under an earlier
codebook version with unchanged tag ids, and is not used on `theory_school`, where 112 of the
120 passages were tagged before `not-applicable` existed.

**Q1, agreement with the reference.**

| Axis | JEV | PROD-A | S55 majority | n |
|---|---|---|---|---|
| `field` | 0.817 [0.750, 0.883] | 0.783 | 0.883 | 120 |
| `empirical_scope` | 0.792 [0.717, 0.867] | 0.750 | 0.717 | 120 |
| `role_in_argument` | 0.592 [0.500, 0.675] | 0.575 | 0.733 | 120 |
| `claim_type` | 0.632 [0.546, 0.716] | 0.487 | 0.684 | 117 |
| `theory_school` | 0.486 [0.390, 0.583] | not used | 0.629 | 105 |

Jev beats the out-of-family production tagger on every axis where both exist, by 0.145 on
`claim_type`; on `field`, `empirical_scope` and `role_in_argument` its lead (0.017 to 0.042)
is inside the interval. S55 scores higher than Jev on four of five axes, but S55 shares a
family with the Sonnet 5 reference, which inflates its figures (Axial measured +0.26 on
`claim_type` for same-family pairs). On `theory_school` Jev's 0.486 is level with the 0.49
that two frontier LLMs of different families reached in July, and 0.014 under the bar.

**Q2, doubt.** Jev's confidence separates contested from unanimous passages with an AUROC of
0.617 [0.512, 0.717] on `theory_school` (the B3 bar is 0.70) and 0.698 [0.591, 0.796] on
`claim_type`. It does sort its own right answers from its wrong ones: keeping the 70% of
items it is most confident on raises agreement on `field` from 0.817 to 0.940,
`empirical_scope` 0.792 to 0.893, `role_in_argument` 0.592 to 0.655, `claim_type` 0.632 to
0.707 and `theory_school` 0.486 to 0.595. For comparison, abstaining wherever the three
Sonnet 5 draws split keeps 0.795 of `claim_type` items and 0.562 of `theory_school` items at
1.000, which holds by construction because the reference is those draws' majority. Expected
calibration error runs from 0.074 (`field`) to 0.124 (`role_in_argument`).

## CIP results

**The problems, in plain words.** The items come from the platform's source feeds, open and
primary: English news items of 80 to 1,500 characters, 292 of the 400 naming Israel, Gaza,
Lebanon, Iran, Yemen or Syria. They are drawn from what the platform held when its data was
exported on 3 Oct 2026; the export carries no publication dates, so no time span is stated.
Only items whose existing label was read from free text by an LLM were drawn; nothing that
arrives already coded is in the sample.

- **C1, actor type.** Given an actor's name and one passage that mentions it, pick what kind
  of actor it is from 16 options: state, government, military, police, rebel_group,
  political_militia, ethnic_militia, religious_militia, criminal_group, political_party,
  international_organization, ngo, media_organization, civilian_group, private_military,
  unattributed. n = 200, drawn 13 per class by the production label (government 14,
  ethnic_militia 4, the only four eligible).
- **C2, claim.** Given a claim and the passage it comes from, answer two questions. Claim type,
  8 options: factual_assertion, attribution, denial, threat, announcement, accusation,
  justification, other; n = 200, drawn 25 per class. Claim subject, 7 options:
  event_occurrence, casualty_count, actor_involvement, weapon_use, territorial_control,
  policy_intent, other; by production label policy_intent 91, actor_involvement 42,
  event_occurrence 28, other 18, territorial_control 13, casualty_count 6, weapon_use 2.

The reference is the majority of three Sonnet 5.5 draws. PROD-C is CIP's production label,
one LLM draw. Both arms received the same one-line description of each option.

**What a hard case looks like.** Each item with every coder's label; a claim in quotes is
the exact text that was labelled, and the news item around it is summarised:

- *Armed movements that are also religious.* Gaza's Qassam Brigades, named in a channel post
  marking the killing of one of their commanders, and Yemen's Houthis, named in an update on
  a joint missile attack on central Israel. All three Sonnet 5.5 draws call both rebel_group.
  Jev calls them religious_militia (0.69 and 0.72), and CIP's own production label already
  has the Qassam Brigades as religious_militia. The option list offers rebel_group,
  political_militia and religious_militia, and these actors fit more than one.
- *Companies.* The list has no option for a business. SpaceX, in a report on a dispute with
  the Pentagon over satellite internet for Iran: the draws and the production label say
  private_military, Jev says civilian_group (0.67). Lufthansa, in a post on flights to Iran
  resuming: the three draws say unattributed, the production label says private_military, and
  Jev says civilian_group (0.83). Three coders, three answers for an airline.
- *Announcement or fact.* A channel post relays that the Israeli military has announced an
  officer's death, and the claim reads: "David Hazutt, a platoon commander in the 12th
  Battalion of the Golani Brigade, was killed in Deir Seryan in southern Lebanon last night."
  Two draws say announcement, one factual_assertion; Jev says factual_assertion at 0.91. The
  claim is both.
- *Evacuation orders.* "Israel has issued renewed forced displacement orders for residents of
  Houmine al-Fawqa, Bnaafoul, Arab Salim, Roumine, Azzeh, Irkay, and Jbaa." All three draws
  say announcement for `claim_type` and policy_intent for `claim_subject_type`. Jev splits
  factual_assertion 0.47 against attribution 0.46, and its second run, sent the same bytes,
  flipped to attribution: this is what a B5 miss looks like. On the subject it says
  event_occurrence (0.72).
- *Doubt where the draws agreed.* From a market report quoting a post by the US president:
  "Iran took too long to negotiate a deal that would have been beneficial to it." All three
  draws say accusation. Jev spreads its answer over attribution 0.37, accusation 0.31 and
  factual_assertion 0.30.
- *A plain miss.* From Israel's prime minister on X: "Iran will never obtain nuclear
  weapons." All three draws say policy_intent; Jev says event_occurrence at 0.84.

**Q1, agreement.**

| Question | JEV vs reference | PROD-C vs reference | Draws vs each other | B6 line | JEV vs single draws | Why, in the data |
|---|---|---|---|---|---|---|
| C1 `actor_type` | 0.716 [0.652, 0.778] | 0.751 | 0.872 | 0.772 | 0.712 | Short because the options overlap for many actors: the largest misses read the reference's rebel_group as religious_militia or political_militia (8 items) and its private_military or unattributed as civilian_group (10), and the three draws themselves split on 37 of 200. |
| C2 `claim_type` | 0.601 [0.531, 0.665] | 0.641 | 0.890 | 0.790 | 0.597 | Short because one claim often fits two options at once (an announcement or an accusation also asserts a fact): Jev puts 80 of 200 claims on factual_assertion and 35 on attribution, where the reference puts 46 and 9. |
| C2 `claim_subject_type` | 0.690 [0.620, 0.750] | 0.735 | 0.937 | 0.837 | 0.680 | Short because a claim about what an actor intends often reports an event too: 14 of Jev's 62 misses read the reference's policy_intent as event_occurrence. |

CIP's production labels sit 0.035 to 0.045 above Jev against the reference, and below the B6
line on all three questions too (0.735, 0.633 and 0.722 against single draws), because they
are an outside coder held to a line set by Sonnet 5.5's agreement with itself; the 0.10
allowance was meant for that gap, which came out at 0.14 to 0.26 for the production labels
and 0.16 to 0.29 for Jev.

**Q2, doubt.**

| Question | Contested | Unanimous | AUROC |
|---|---|---|---|
| C1 `actor_type` | 37 | 163 | 0.733 [0.650, 0.804] |
| C2 `claim_type` | 32 | 168 | 0.526 [0.420, 0.636], at chance because Jev is unsure on many items the draws agree on: it differs from the unanimous draws on 60 of 168, at a mean confidence of 0.551 |
| C2 `claim_subject_type` | 19 | 181 | 0.708 [0.578, 0.819] |

Keeping the 70% of items Jev is most confident on raises agreement on `actor_type` from 0.716
to 0.877, on `claim_type` from 0.601 to 0.676 and on `claim_subject_type` from 0.690 to 0.800,
because its misses gather where it is least sure, on the overlapping options above.

**Q4, the same answer twice.** Jev's answer was identical across the two runs on 0.985 of C1
items and 0.925 of C2 items (per question 0.950 for `claim_type` and 0.975 for
`claim_subject_type`), short of the 100% bar because the items that moved sat on a near-tie:
the median gap between Jev's top two options was 0.03 on those items. The largest shift in
any option's probability between runs was 0.19 on C1 and 0.14 on C2.

## Cost and speed

| Set | JEV $ per 1,000 | S55 $ per 1,000, one draw | Ratio | JEV p50 / p95 ms | S55 p50 / p95 ms |
|---|---|---|---|---|---|
| Axial | 0.228 | 2.911 | 0.078 | 325 / 381 | 369 / 492 |
| C1 | 0.037 | 1.277 | 0.029 | 284 / 332 | 193 / 554 |
| C2 | 0.034 | 1.543 | 0.022 | 282 / 330 | 254 / 608 |
| All 520 | 0.080 | 1.756 | 0.046 | 290 / 357 | 256 / 601 |

- JEV is logged input tokens at $0.042 per million. S55 is each call's logged usage at the
  Sonnet 5.5 list price read on 2026-10-03 ($2 input, $2.50 5-minute cache write, $4 1-hour
  cache write, $0.20 cache read, $10 output per million tokens), which reproduces the cost
  Claude Code itself reported for every draw.
- Jev's median latency is above S55's on CIP because S55's figure is a batch's duration
  divided by its 10 items: any one S55 answer waits for its whole batch, while each Jev figure
  is one item's own call.
- Jev costs more per item on Axial because the codebook criteria go out with every item;
  CIP's option lists are short.
- Spend: Jev cost $0.0849 of a $5.00 credit across both sets, smoke tests and both runs. S55
  ran on a subscription; its list-price equivalent over the nine scored draws is $2.74
  (Axial $1.048, C1 $0.766, C2 $0.926), not cash.

## Caveats

- Every reference label is an LLM label. On Axial the reference is Sonnet 5, which shares a
  family with S55; on CIP it is S55's own majority, so B6 sets Jev against a coder's agreement
  with itself.
- n = 120 on Axial. Read axis-level differences within their intervals.
- The reference has a single draw on `field`, `empirical_scope` and `role_in_argument`, so
  those axes have no contested flag and are left out of B3.
- Jev's `confidence` is used as returned; its definition is TypeSafe's.
- B4 passes on the pooled ratio with S55 priced from its logged usage, which includes Claude
  Code writing each batch's instructions to the 1-hour cache. Axial alone fails.
- "Argmax" and Jev's own `choice` differ on 7 of 2,000 answers (ties and 0.01 roundings);
  B5 fails on either reading.
- S55 replies were read under three parsing rules found during the runs; draws that hit a
  rule before it existed were rerun, and no figure here uses an invalid or re-asked label.
