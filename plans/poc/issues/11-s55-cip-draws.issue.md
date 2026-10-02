# feat(poc): S55 smoke then three draws on C1 and C2 [slice 11]

**Spec:** [specs/PRD.md#62-s55-calls](https://github.com/Muhanad-husn/decision-model-poc/blob/main/specs/PRD.md#62-s55-calls) · **Plan:** [plans/poc/11-s55-cip-draws.md](https://github.com/Muhanad-husn/decision-model-poc/blob/main/plans/poc/11-s55-cip-draws.md)
**Depends on:** #10 (slice 05), #13 (slice 08), #14 (slice 09)
**Labels:** M5

## Deliverable
The S55 runner takes CIP items with options.yaml inlined; smoke on 5 items per set; the three full draws (120 calls, builder-run under the allow rule) start only after both arms' CIP smoke has passed (this slice and slice 10). The runner recomputes the SHA-256 of options.yaml and refuses to run if it differs from `manifests/cip_options.json`.

## Mechanism
The slice 05 runner extended with a CIP prompt builder.

## Acceptance criterion
Given the sample and options, when the three draws complete, then there are 1,200 item-labels (400 items x 3 draws), each valid or listed as invalid, a test shows the runner refusing on an options hash mismatch, the full draws started after both arms' CIP smoke passed, every model id is Sonnet 5.5, the draws are in REPORT.md's run log, and PLAN.md M5 turns `done` once slice 10 has also landed.

## Files
```aeo-independence
slice: 11-s55-cip-draws
edits: src/s55.py
edits: tests/test_s55.py
edits: REPORT.md
edits: PLAN.md
depends-on: 05-s55-runner-smoke
depends-on: 08-cip-sample
depends-on: 09-cip-options
```

## Out of scope
Using the S55 majority anywhere outside metrics.
