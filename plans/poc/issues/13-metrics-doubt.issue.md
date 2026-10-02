# feat(poc): contested AUROC, selective agreement, calibration and determinism [slice 13]

**Spec:** [specs/PRD.md#7-metrics](https://github.com/Muhanad-husn/decision-model-poc/blob/main/specs/PRD.md#7-metrics) · **Plan:** [plans/poc/13-metrics-doubt.md](https://github.com/Muhanad-husn/decision-model-poc/blob/main/plans/poc/13-metrics-doubt.md)
**Depends on:** #17 (slice 12)
**Labels:** M6

## Deliverable
Adds to `src/metrics.py`: AUROC of `1 - confidence` predicting contested, with a bootstrap interval; selective agreement at 90/80/70% coverage beside best-of-3 abstention; Brier score, and ECE over 10 bins only for axes with at least 100 referenced items; determinism as identical-argmax share and maximum absolute probability difference.

## Mechanism
Library: `scikit-learn` (`roc_auc_score`), `numpy`.

## Acceptance criterion
Given toy confidences, flags and probability vectors with hand-computed answers, when the tests run, then each metric matches, ECE is withheld under 100 items, and AUROC intervals are seed-stable.

## Files
```aeo-independence
slice: 13-metrics-doubt
edits: src/metrics.py
edits: tests/test_metrics.py
depends-on: 12-metrics-agreement
```

## Out of scope
Applying them to real runs (slice 15).
