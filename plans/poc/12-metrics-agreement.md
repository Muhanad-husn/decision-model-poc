# Slice 12: agreement, kappa and coder agreement with bootstrap intervals

**Milestone:** M6 · **Size:** S · **Issue:** #17
**Spec:** [specs/PRD.md#7-metrics](../../specs/PRD.md#7-metrics) · **Depends on:** none

## Goal
`src/metrics.py` computes agreement over referenced items, Cohen's kappa, coder agreement (mean against each draw beside the draws' mean pairwise agreement) and a 95% bootstrap interval (2,000 resamples, seed 20261002) for every agreement figure.

## Mechanism
Library: `numpy` and `scikit-learn` (`cohen_kappa_score`).

## Acceptance criterion
Given toy label sets with hand-computed answers, when the tests run, then every metric equals its hand value and the bootstrap interval is identical across two calls with the seed.

## Files
```aeo-independence
slice: 12-metrics-agreement
edits: pyproject.toml
edits: uv.lock
creates: src/metrics.py
creates: tests/test_metrics.py
```

## Out of scope
Doubt, calibration, determinism (slice 13); cost and latency (slice 14).
