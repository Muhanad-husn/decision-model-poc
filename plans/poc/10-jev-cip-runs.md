# Slice 10: Jev smoke then runs 1 and 2 on C1 and C2

**Milestone:** M5 · **Size:** S · **Issue:** #15
**Spec:** [specs/PRD.md#61-jev-calls](../../specs/PRD.md#61-jev-calls) · **Depends on:** #8 (slice 03), #13 (slice 08), #14 (slice 09)

## Goal
The Jev runner takes CIP items: one call per item with the C1 question or the two C2 questions, criteria from options.yaml, state as the actor name or claim text plus the passage. Smoke on 5 items per set; full runs 1 and 2 on all 400 start only after both arms' CIP smoke has passed (this slice and slice 11). The runner recomputes the SHA-256 of options.yaml and refuses to run if it differs from `manifests/cip_options.json`.

## Mechanism
The slice 03 runner extended with a CIP question builder.

## Acceptance criterion
Given the sample and options, when the smoke and both runs complete, then there are 800 responses, a test shows the runner refusing on an options hash mismatch, the full runs started after both arms' CIP smoke passed, each valid or listed, spend is booked in LEDGER.md and stays under the $2.00 stop, and the runs are in REPORT.md's run log.

## Files
```aeo-independence
slice: 10-jev-cip-runs
edits: src/jev.py
edits: tests/test_jev.py
edits: LEDGER.md
edits: REPORT.md
depends-on: 03-jev-runner-smoke
depends-on: 08-cip-sample
depends-on: 09-cip-options
```

## Out of scope
S55 on CIP (slice 11).
