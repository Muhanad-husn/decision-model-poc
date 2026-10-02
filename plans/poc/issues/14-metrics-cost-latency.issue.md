# feat(poc): cost per 1,000 items and p50/p95 latency for both arms [slice 14]

**Spec:** [specs/PRD.md#7-metrics](https://github.com/Muhanad-husn/decision-model-poc/blob/main/specs/PRD.md#7-metrics) · **Plan:** [plans/poc/14-metrics-cost-latency.md](https://github.com/Muhanad-husn/decision-model-poc/blob/main/plans/poc/14-metrics-cost-latency.md)
**Depends on:** #18 (slice 13)
**Labels:** M6

## Deliverable
Adds to `src/metrics.py`: JEV cost from input tokens at $0.042/M; S55 API-equivalent cost from logged usage at the Sonnet 5.5 list price on the run date (price and pricing-page URL recorded as constants); p50 and p95 latency per item (JEV per call, S55 batch duration / batch size).

## Mechanism
The `claude-api` skill for the current Sonnet 5.5 list price and its URL; `numpy` percentiles.

## Acceptance criterion
Given toy usage logs, when the tests run, then cost per 1,000 and p50/p95 match hand values, and the S55 price constant carries its source URL.

## Files
```aeo-independence
slice: 14-metrics-cost-latency
edits: src/metrics.py
edits: tests/test_metrics.py
depends-on: 13-metrics-doubt
```

## Out of scope
The B4 verdict (slice 16).
