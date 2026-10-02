# Slice 06: S55 three independent draws on all 120 Axial items

**Milestone:** M3 · **Size:** S · **Issue:** #11
**Spec:** [specs/PRD.md#11-build-plan](../../specs/PRD.md#11-build-plan) · **Depends on:** #10 (slice 05), #8 (slice 03)

## Goal
Three draws as separate processes (12 batches each, 36 calls), paced inside the subscription limits, with the invalid labels listed. The builder runs them under the allow rule; starts only after both arms' Axial smoke runs (slices 03 and 05) have passed, per PRD §9.

## Mechanism
The slice 05 runner, three separate invocations.

## Acceptance criterion
Given both arms' Axial smoke runs passed, when three draws complete, then there are 360 item-labels (120 x 3, each valid or listed as invalid), every call's model id is Sonnet 5.5, the draws are in REPORT.md's run log, and PLAN.md M3 turns `done`.

## Files
```aeo-independence
slice: 06-s55-axial-draws
edits: src/s55.py
edits: REPORT.md
edits: PLAN.md
depends-on: 05-s55-runner-smoke
depends-on: 03-jev-runner-smoke
```

## Out of scope
Metrics on the draws.
