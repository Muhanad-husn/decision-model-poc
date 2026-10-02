# docs(poc): PUBLISH.md under the §10 rules, with the grep gate and founder brief [slice 17]

**Spec:** [specs/PRD.md#10-data-handling-and-disclosure](https://github.com/Muhanad-husn/decision-model-poc/blob/main/specs/PRD.md#10-data-handling-and-disclosure) · **Plan:** [plans/poc/17-publish.md](https://github.com/Muhanad-husn/decision-model-poc/blob/main/plans/poc/17-publish.md)
**Depends on:** #21 (slice 16)
**Labels:** M7

## Deliverable
PUBLISH.md: Axial in full, CIP results only, verdict first, first paragraph saying every reference label is an LLM label, CIP sources as "the platform's source feeds, open and primary", every CIP shortfall with its reason in the same sentence. A test greps for em dash, "OSINT" and "open-source". The one-paragraph founder brief (verdict, B3, spend against $5) goes in the PR body.

## Mechanism
Written from REPORT.md; pytest grep gate.

## Acceptance criterion
Given REPORT.md, when the publish test runs, then PUBLISH.md has no em dash, "OSINT" or "open-source", its first paragraph contains the LLM-label statement, and it names no prompt, schema file, stage, DEC number or source list for CIP; PLAN.md M7 turns `done`.

## Files
```aeo-independence
slice: 17-publish
edits: PLAN.md
creates: PUBLISH.md
creates: tests/test_publish.py
depends-on: 16-report
```

## Out of scope
Publishing anywhere outside the repo.
