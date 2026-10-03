"""The PRD §7 metrics, as small pure functions over per-item lists in one fixed item order.

Labels are strings. A reference of None or "invalid" means the item has no reference and is
left out; an arm label of None or "invalid" on a referenced item is a miss. Probability
vectors are dicts of option -> probability; the argmax of a tie is the first option in the
dict's order. Every agreement figure and every AUROC gets a 95% percentile bootstrap
interval: 2,000 resamples of the item indices with replacement from
numpy.random.default_rng(20261002), the statistic recomputed on each resample.

Slice 12: agreement, kappa, coder agreement, majority, contested, bootstrap.
Slice 13: doubt AUROC, selective agreement, best-of-3 abstention, Brier, ECE, determinism.
Slice 14: cost per 1,000 items and p50/p95 latency for both arms.
Applying them to the real runs is slice 15.
"""

import math
from itertools import combinations

import numpy as np
from sklearn.metrics import cohen_kappa_score

SEED = 20261002
RESAMPLES = 2000
INVALID = "invalid"
COVERAGES = (0.9, 0.8, 0.7)
ECE_BINS = 10
ECE_MIN_ITEMS = 100

JEV_USD_PER_MILLION = 0.042  # input tokens only; output is free (PRD §4)
# Sonnet 5.5 list price per million tokens, read from the pricing page on the run date. A cache
# write is billed by its TTL, a cache read at 0.1x input (PRD §6.2: API-equivalent cost).
S55_PRICE = {
    "model": "claude-sonnet-5-5",
    "source": "https://platform.claude.com/docs/en/about-claude/pricing",
    "as_of": "2026-10-03",
    "usd_per_million": {
        "input": 2.00, "cache_write_5m": 2.50, "cache_write_1h": 4.00, "cache_read": 0.20, "output": 10.00,
    },
}


def _valid(label):
    return label is not None and label != INVALID


def _take(seq, idx):
    return [seq[i] for i in idx]


def _argmax(probs):
    return max(probs, key=probs.get)  # max keeps the first of equal values


# --- slice 12 ------------------------------------------------------------------------------


def agreement(arm, ref):
    """Share of referenced items where the arm's label equals the reference; None when no
    item is referenced."""
    pairs = [(a, r) for a, r in zip(arm, ref, strict=True) if _valid(r)]
    if not pairs:
        return None
    return sum(a == r for a, r in pairs) / len(pairs)


def kappa(arm, ref):
    """Cohen's kappa over referenced items; a missing or invalid arm label is its own class."""
    pairs = [(a if _valid(a) else INVALID, r) for a, r in zip(arm, ref, strict=True) if _valid(r)]
    return float(cohen_kappa_score([a for a, _ in pairs], [r for _, r in pairs]))


def majority(draws):
    """The label more than half the draws give, else None. An invalid draw is no vote."""
    votes = [d for d in draws if _valid(d)]
    for label in dict.fromkeys(votes):
        if votes.count(label) * 2 > len(draws):
            return label
    return None


def contested(draws):
    """True unless every draw gives the same valid label (2-1 or no majority is contested)."""
    return not (all(_valid(d) for d in draws) and len(set(draws)) == 1)


def _pairwise(a, b):
    """Agreement between two draws as peers: items where either draw has a label (not None),
    a match only when both are valid and equal, so an invalid draw is a miss."""
    rows = [(x, y) for x, y in zip(a, b, strict=True) if x is not None or y is not None]
    if not rows:
        return None
    return sum(_valid(x) and x == y for x, y in rows) / len(rows)


def coder_agreement(arm, draws):
    """The arm's mean agreement with each individual draw (each draw as the reference),
    beside the draws' mean pairwise agreement."""
    per_draw = [agreement(arm, d) for d in draws]
    per_pair = [_pairwise(a, b) for a, b in combinations(draws, 2)]
    return {
        "arm_mean": _mean(per_draw),
        "draws_pairwise": _mean(per_pair),
    }


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def bootstrap_ci(statistic, n, resamples=RESAMPLES, seed=SEED):
    """95% percentile interval of statistic(indices) over resamples of n item indices drawn
    with replacement. A resample where the statistic is None (undefined) is skipped; None
    when no resample is defined."""
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(resamples):
        v = statistic(rng.integers(0, n, size=n))
        if v is not None:
            values.append(v)
    if not values:
        return None
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def agreement_ci(arm, ref, seed=SEED):
    return bootstrap_ci(lambda idx: agreement(_take(arm, idx), _take(ref, idx)), len(ref), seed=seed)


def coder_agreement_ci(arm, draws, seed=SEED):
    """Intervals for both coder-agreement figures; the arm and every draw are resampled on
    the same item indices."""
    n = len(arm)

    def figure(key):
        return lambda idx: coder_agreement(_take(arm, idx), [_take(d, idx) for d in draws])[key]

    return {key: bootstrap_ci(figure(key), n, seed=seed) for key in ("arm_mean", "draws_pairwise")}


# --- slice 13 ------------------------------------------------------------------------------


def auroc_doubt(confidence, flags):
    """AUROC of 1 - confidence predicting contested (True) against unanimous; None when only
    one class is present."""
    if len(set(flags)) < 2:
        return None
    pos = np.array([1 - c for c, f in zip(confidence, flags, strict=True) if f])
    neg = np.array([1 - c for c, f in zip(confidence, flags, strict=True) if not f])
    # Mann-Whitney count, a tie scoring one half: the value sklearn's roc_auc_score gives
    # (tests/test_metrics.py checks the two agree) at a fraction of its per-call cost, which
    # matters across 2,000 resamples.
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (len(pos) * len(neg)))


def auroc_doubt_ci(confidence, flags, seed=SEED):
    """Bootstrap interval of auroc_doubt. Resamples holding only contested or only unanimous
    items have no AUROC and are skipped, so the percentiles come from the defined ones."""
    return bootstrap_ci(
        lambda idx: auroc_doubt(_take(confidence, idx), _take(flags, idx)), len(flags), seed=seed
    )


def selective_agreement(arm, ref, confidence, coverages=COVERAGES):
    """Agreement on the most confident share of referenced items, per coverage.

    The kept count is coverage x referenced items rounded up, so the arm never answers fewer
    than the coverage asks. Items are ordered by confidence, highest first; equal confidences
    keep their input order, so the kept count is exact rather than growing with ties. The
    threshold reported is the confidence of the last item kept."""
    rows = [(c, a == r) for a, r, c in zip(arm, ref, confidence, strict=True) if _valid(r)]
    rows.sort(key=lambda row: -row[0])  # stable
    out = {}
    for cov in coverages:
        kept = min(len(rows), math.ceil(round(cov * len(rows), 9)))
        top = rows[:kept]
        out[cov] = {
            "kept": kept,
            "threshold": top[-1][0] if top else None,
            "agreement": sum(hit for _, hit in top) / kept if kept else None,
        }
    return out


def best_of_3_abstention(draws, ref):
    """The draws answer only where all of them give the same valid label, and abstain
    elsewhere. Coverage is the unanimous share of referenced items; agreement is the
    unanimous label against the reference on those items."""
    rows = [(col, r) for col, r in zip(zip(*draws, strict=True), ref, strict=True) if _valid(r)]
    answered = [(col[0], r) for col, r in rows if not contested(col)]
    return {
        "coverage": len(answered) / len(rows) if rows else None,
        "agreement": sum(a == r for a, r in answered) / len(answered) if answered else None,
    }


def brier(probs, ref):
    """Mean over referenced items of sum over options of (p - one-hot reference)^2."""
    scores = []
    for p, r in zip(probs, ref, strict=True):
        if not _valid(r) or p is None:
            continue
        scores.append(sum((q - (opt == r)) ** 2 for opt, q in p.items()) + (0.0 if r in p else 1.0))
    return sum(scores) / len(scores) if scores else None


def ece(probs, ref, bins=ECE_BINS, min_items=ECE_MIN_ITEMS):
    """Expected calibration error of the top probability over equal-width bins, each bin
    [k/10, (k+1)/10) with 1.0 in the last; None when fewer than min_items items are
    referenced."""
    rows = [(max(p.values()), _argmax(p) == r) for p, r in zip(probs, ref, strict=True) if _valid(r) and p]
    if len(rows) < min_items:
        return None
    total = 0.0
    for k in range(bins):
        members = [(c, hit) for c, hit in rows if min(int(c * bins), bins - 1) == k]
        if members:
            conf = sum(c for c, _ in members) / len(members)
            acc = sum(hit for _, hit in members) / len(members)
            total += len(members) / len(rows) * abs(acc - conf)
    return total


def determinism(run1, run2):
    """Share of items with the same argmax in both runs, and the largest absolute difference
    in any option's probability. An item missing from either run counts as not identical and
    adds nothing to the difference."""
    same, diffs = 0, [0.0]
    for p, q in zip(run1, run2, strict=True):
        if p is None or q is None:
            continue
        same += _argmax(p) == _argmax(q)
        diffs.extend(abs(p.get(opt, 0.0) - q.get(opt, 0.0)) for opt in p.keys() | q.keys())
    return {"identical_argmax": same / len(run1), "max_abs_diff": max(diffs)}


# --- slice 14 ------------------------------------------------------------------------------


def jev_cost_usd(input_tokens):
    """Logged input tokens, one count per call, at $0.042 per million."""
    return sum(input_tokens) * JEV_USD_PER_MILLION / 1_000_000


def s55_cost_usd(usage, price=S55_PRICE):
    """API-equivalent cost of one call from its logged usage, each bucket at its list rate. A
    cache write is split by TTL when the usage carries the split; without it every written
    token is priced at the 5-minute rate, the API's default TTL."""
    rate = price["usd_per_million"]
    split = usage.get("cache_creation")
    if isinstance(split, dict):
        w5, w1h = split.get("ephemeral_5m_input_tokens") or 0, split.get("ephemeral_1h_input_tokens") or 0
    else:
        w5, w1h = usage.get("cache_creation_input_tokens") or 0, 0
    total = ((usage.get("input_tokens") or 0) * rate["input"]
             + w5 * rate["cache_write_5m"] + w1h * rate["cache_write_1h"]
             + (usage.get("cache_read_input_tokens") or 0) * rate["cache_read"]
             + (usage.get("output_tokens") or 0) * rate["output"])
    return total / 1_000_000


def s55_draw_cost_usd(calls, price=S55_PRICE):
    """Cost of the calls that label items (batches and re-asks); the calibration call labels
    nothing and is left out."""
    return sum(s55_cost_usd(c["usage"], price) for c in calls if c["ids"])


def cost_per_1000(usd, items):
    return usd / items * 1000


def s55_item_latencies(calls):
    """One latency per labelled item: its call's duration_ms divided by the items in the call."""
    return [c["duration_ms"] / len(c["ids"]) for c in calls if c["ids"] for _ in c["ids"]]


def latency_percentiles(values):
    """p50 and p95 by numpy's default linear interpolation, over one value per item."""
    return {"n": len(values), "p50": float(np.percentile(values, 50)), "p95": float(np.percentile(values, 95))}
