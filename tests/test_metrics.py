"""The PRD §7 metrics on toy data. Every expected value is worked by hand in the comment above
its assertion; the bootstrap tests re-derive the resampling from the seed so the method itself
is pinned, not just its stability."""

import math

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from src.metrics import (
    INVALID,
    RESAMPLES,
    SEED,
    agreement,
    agreement_ci,
    auroc_doubt,
    auroc_doubt_ci,
    best_of_3_abstention,
    bootstrap_ci,
    brier,
    coder_agreement,
    coder_agreement_ci,
    contested,
    determinism,
    ece,
    kappa,
    majority,
    selective_agreement,
)


def test_seed_and_resamples_are_the_prd_values():
    assert SEED == 20261002
    assert RESAMPLES == 2000


# --- slice 12: agreement, kappa, coder agreement, bootstrap ---------------------------------


def test_agreement_counts_only_referenced_items_and_invalid_is_a_miss():
    arm = ["a", "b", "a", INVALID, None, "c"]
    ref = ["a", "b", "b", "a", "a", None]
    # item 5 has no reference: 5 referenced. Matches on items 0 and 1; item 2 wrong,
    # item 3 invalid, item 4 missing: 2 / 5.
    assert agreement(arm, ref) == pytest.approx(0.4)


def test_agreement_with_no_referenced_item_is_none():
    assert agreement(["a"], [None]) is None


def test_kappa_on_referenced_items():
    arm = ["a", "a", "b", "b", "x"]
    ref = ["a", "b", "b", "b", None]
    # Item 4 unreferenced. po = 3/4. Arm marginals a .5, b .5; reference a .25, b .75.
    # pe = .5 * .25 + .5 * .75 = .5. kappa = (.75 - .5) / (1 - .5) = .5.
    assert kappa(arm, ref) == pytest.approx(0.5)


def test_kappa_counts_a_missing_arm_label_as_its_own_class():
    arm = ["a", None, "b", "b"]
    ref = ["a", "a", "b", "b"]
    # None becomes "invalid". po = 3/4. Arm: a .25, invalid .25, b .5; ref: a .5, b .5.
    # pe = .25 * .5 + 0 + .5 * .5 = .375. kappa = (.75 - .375) / .625 = .6.
    assert kappa(arm, ref) == pytest.approx(0.6)


D1 = ["a", "a", "b", "b"]
D2 = ["a", "b", "b", "b"]
D3 = ["a", "a", "a", "b"]
ARM = ["a", "a", "b", "a"]


def test_coder_agreement_beside_pairwise_draw_agreement():
    # Arm vs d1 3/4, vs d2 2/4, vs d3 2/4: mean 1.75 / 3.
    # d1-d2 3/4, d1-d3 3/4, d2-d3 2/4: mean 2/3.
    out = coder_agreement(ARM, [D1, D2, D3])
    assert out["arm_mean"] == pytest.approx(1.75 / 3)
    assert out["draws_pairwise"] == pytest.approx(2 / 3)


def test_pairwise_counts_an_invalid_draw_as_a_miss_not_a_match():
    # Item 1: both draws invalid, never a match; item 2 both None, no valid label, excluded.
    # d1-d2 over items 0 and 1: 1 / 2.
    out = coder_agreement(["a", "a", "a"], [["a", INVALID, None], ["a", INVALID, None]])
    assert out["draws_pairwise"] == pytest.approx(0.5)


def test_majority_and_contested():
    rows = [
        ["a", "a", "b"],
        ["a", "b", "c"],
        ["a", "a", "a"],
        ["a", INVALID, INVALID],
        ["a", "a", INVALID],
    ]
    # An invalid draw is no vote; it still breaks unanimity.
    assert [majority(r) for r in rows] == ["a", None, "a", None, "a"]
    assert [contested(r) for r in rows] == [True, True, False, True, True]


def _replay(stat, n, seed=SEED):
    """The documented method, re-derived: draw n indices with replacement 2,000 times from
    default_rng(seed), keep the statistic where it is defined, take the 2.5th and 97.5th
    percentiles."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(RESAMPLES):
        v = stat(rng.integers(0, n, size=n))
        if v is not None:
            vals.append(v)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


ARM_B = ["a", "b", "a", "a", "c", "b", "a", "b", "c", "a"]
REF_B = ["a", "b", "b", "a", "c", "a", "a", "b", "b", None]


def test_agreement_ci_is_the_seeded_percentile_bootstrap_and_repeats_exactly():
    first = agreement_ci(ARM_B, REF_B)
    assert first == agreement_ci(ARM_B, REF_B)
    expected = _replay(lambda idx: agreement([ARM_B[i] for i in idx], [REF_B[i] for i in idx]), 10)
    assert first == pytest.approx(expected)
    lo, hi = first
    assert lo <= agreement(ARM_B, REF_B) <= hi


def test_a_different_seed_moves_the_interval():
    # 200 items: fine-grained enough that the percentiles depend on which resamples are drawn
    # (on 10 items both seeds land on the same coarse values).
    arm = ["a", "b", "a", "c"] * 50
    ref = ["a", "b", "b", "c", "a"] * 40
    assert agreement_ci(arm, ref) != agreement_ci(arm, ref, seed=1)


def test_perfect_agreement_has_a_degenerate_interval():
    assert agreement_ci(["a", "b", "c"], ["a", "b", "c"]) == (1.0, 1.0)


def test_coder_agreement_ci_resamples_items_jointly():
    draws = [D1, D2, D3]
    first = coder_agreement_ci(ARM, draws)
    assert first == coder_agreement_ci(ARM, draws)

    def take(seq, idx):
        return [seq[i] for i in idx]

    exp_arm = _replay(lambda idx: coder_agreement(take(ARM, idx), [take(d, idx) for d in draws])["arm_mean"], 4)
    exp_pair = _replay(lambda idx: coder_agreement(take(ARM, idx), [take(d, idx) for d in draws])["draws_pairwise"], 4)
    assert first["arm_mean"] == pytest.approx(exp_arm)
    assert first["draws_pairwise"] == pytest.approx(exp_pair)


def test_bootstrap_ci_skips_undefined_resamples():
    # A statistic undefined on every resample has no interval.
    assert bootstrap_ci(lambda idx: None, 5) is None


# --- slice 13: doubt AUROC, selective agreement, calibration, determinism -------------------


CONF_A = [0.9, 0.5, 0.5, 0.2]
FLAG_A = [False, True, False, True]


def test_auroc_of_one_minus_confidence_predicting_contested():
    # Doubt = 1 - confidence = .1, .5, .5, .8. Contested doubts .5, .8; unanimous .1, .5.
    # Pairs (pos, neg): (.5,.1) 1, (.5,.5) tie .5, (.8,.1) 1, (.8,.5) 1 -> 3.5 / 4 = .875.
    assert auroc_doubt(CONF_A, FLAG_A) == pytest.approx(0.875)


def test_auroc_matches_sklearn_roc_auc_score_with_ties():
    rng = np.random.default_rng(7)
    conf = list(np.round(rng.random(60), 1))  # rounding forces many ties
    flags = list(rng.random(60) < 0.5)
    expected = roc_auc_score(flags, [1 - c for c in conf])
    assert auroc_doubt(conf, flags) == pytest.approx(expected)


def test_auroc_is_undefined_with_one_class():
    assert auroc_doubt([0.9, 0.2], [True, True]) is None


def test_auroc_ci_is_seed_stable_and_skips_one_class_resamples():
    first = auroc_doubt_ci(CONF_A, FLAG_A)
    assert first == auroc_doubt_ci(CONF_A, FLAG_A)

    def stat(idx):
        flags = [FLAG_A[i] for i in idx]
        if len(set(flags)) < 2:
            return None
        return auroc_doubt([CONF_A[i] for i in idx], flags)

    assert first == pytest.approx(_replay(stat, 4))


CONF_S = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.99]
ARM_S = ["a", "a", "a", "a", "a", "a", "a", "a", "a", "a", "a"]
REF_S = ["a", "a", "a", "a", "a", "a", "a", "b", "b", "b", None]


def test_selective_agreement_at_90_80_70_percent_coverage():
    # 10 referenced items (the 0.99 one has no reference and is not counted). Ordered by
    # confidence the first 7 are right, the last 3 wrong.
    # 90%: 9 kept, 7 right -> 7/9. 80%: 8 kept -> 7/8. 70%: 7 kept -> 7/7. (0.7 * 10 is
    # 7.000000000000001 in floating point; the count must still be 7, not 8.)
    out = selective_agreement(ARM_S, REF_S, CONF_S)
    assert out[0.9]["agreement"] == pytest.approx(7 / 9)
    assert out[0.8]["agreement"] == pytest.approx(7 / 8)
    assert out[0.7]["agreement"] == pytest.approx(1.0)
    assert out[0.7]["kept"] == 7
    assert out[0.9]["threshold"] == pytest.approx(0.55)


def test_selective_agreement_rounds_the_kept_count_up():
    # 5 referenced, 90% of 5 = 4.5 -> 5 kept (rounding up never answers below the coverage):
    # 4 right of 5 = .8. Rounding down would give 4/4 = 1.0.
    out = selective_agreement(["a"] * 5, ["a", "a", "a", "a", "b"], [0.9, 0.8, 0.7, 0.6, 0.5], (0.9,))
    assert out[0.9]["kept"] == 5
    assert out[0.9]["agreement"] == pytest.approx(0.8)


def test_selective_agreement_breaks_confidence_ties_by_input_order():
    # 60% of 3 = 1.8 -> 2 kept: item 1 (.9), then of the tied .8 items the first, item 0
    # (wrong). 1 right of 2 = .5.
    out = selective_agreement(["a", "a", "a"], ["b", "a", "a"], [0.8, 0.9, 0.8], (0.6,))
    assert out[0.6]["agreement"] == pytest.approx(0.5)


def test_best_of_3_abstention_answers_only_unanimous_items():
    d1 = ["a", "b", "a", "c", "a"]
    d2 = ["a", "b", "a", "c", "b"]
    d3 = ["a", "b", "b", "c", "c"]
    ref = ["a", "a", "a", "c", None]
    # 4 referenced (item 4 has none). Unanimous: items 0, 1, 3 -> coverage 3/4.
    # Answered right: items 0 and 3 -> 2/3.
    out = best_of_3_abstention([d1, d2, d3], ref)
    assert out["coverage"] == pytest.approx(0.75)
    assert out["agreement"] == pytest.approx(2 / 3)


def test_brier_against_one_hot_reference():
    probs = [{"a": 0.7, "b": 0.2, "c": 0.1}, {"a": 0.5, "b": 0.5, "c": 0.0}, {"a": 1.0, "b": 0.0, "c": 0.0}]
    ref = ["a", "b", None]
    # Item 0: .3^2 + .2^2 + .1^2 = .14. Item 1: .5^2 + .5^2 + 0 = .5. Item 2 unreferenced.
    # Mean (.14 + .5) / 2 = .32.
    assert brier(probs, ref) == pytest.approx(0.32)


def _ece_set(n_high=50, n_low=50, extra_unref=0):
    probs, ref = [], []
    for k in range(n_high):  # confidence .9, 45 of 50 right
        probs.append({"a": 0.9, "b": 0.1})
        ref.append("a" if k < n_high * 0.9 else "b")
    for k in range(n_low):  # confidence .6, 20 of 50 right
        probs.append({"a": 0.6, "b": 0.4})
        ref.append("a" if k < n_low * 0.4 else "b")
    for _ in range(extra_unref):
        probs.append({"a": 0.6, "b": 0.4})
        ref.append(None)
    return probs, ref


def test_ece_over_ten_bins():
    probs, ref = _ece_set()
    # Bin [.9, 1.0]: 50 items, accuracy .9, confidence .9, gap 0.
    # Bin [.6, .7): 50 items, accuracy .4, confidence .6, gap .2.
    # ECE = .5 * 0 + .5 * .2 = .1.
    assert ece(probs, ref) == pytest.approx(0.1)


def test_ece_is_withheld_under_100_referenced_items():
    probs, ref = _ece_set(n_low=49, extra_unref=1)  # 99 referenced, 100 rows
    assert ece(probs, ref) is None


def test_determinism_identical_argmax_and_max_probability_difference():
    run1 = [{"a": 0.6, "b": 0.4}, {"a": 0.3, "b": 0.7}, {"a": 0.5, "b": 0.5}]
    run2 = [{"a": 0.6, "b": 0.4}, {"a": 0.55, "b": 0.45}, {"a": 0.5, "b": 0.5}]
    # Argmax run 1: a, b, a (a tie goes to the first option); run 2: a, a, a -> 2/3 identical.
    # Largest difference: item 1, |.3 - .55| = .25.
    out = determinism(run1, run2)
    assert out["identical_argmax"] == pytest.approx(2 / 3)
    assert out["max_abs_diff"] == pytest.approx(0.25)


def test_determinism_counts_a_failed_item_as_not_identical():
    out = determinism([{"a": 0.6, "b": 0.4}, None], [{"a": 0.6, "b": 0.4}, {"a": 1.0, "b": 0.0}])
    assert out["identical_argmax"] == pytest.approx(0.5)
    assert out["max_abs_diff"] == pytest.approx(0.0)
    assert math.isfinite(out["max_abs_diff"])
