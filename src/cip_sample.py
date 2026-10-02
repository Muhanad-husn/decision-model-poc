"""Draw the CIP set C from the slice 07 export: 200 C1 and 200 C2 items (PRD §5.2).

Reads data/cip/c1_pool.jsonl, c2_pool.jsonl and export_summary.json; never the database.
Writes data/cip/c1_items.jsonl, c2_items.jsonl and SAMPLE.md. No model call.

Eligibility. An item keeps its first passage (in event-id order) that is English and 80 to
1,500 characters long; with none it is dropped and counted under its closest miss (over_1500,
then under_80, then not_english). The language is the passage's own, detected by langid
restricted to CIP's language enum, because the export's source language is the source's
declared one and `claim_language` records the language of the original claim, while
`claim_text` itself is English. A C2 item without a claim_type label is dropped as no_label.

Strata (founder rulings, 2026-10-03, because PRD §5.2's "up to 25 per class, fill to 200"
cannot hold for C1: 16 classes of up to 25 make 372). Every class gets the same quota k, the
largest k <= 25 for which the strata fit in the target; a class smaller than k gives all its
items. The rest is filled at random from the eligible items left. C1 is stratified by
actor_type, C2 by claim_type. Items are ordered by id before every draw and one
random.Random(20261002) serves each task, so a rerun yields the same items.

Run: uv run python src/cip_sample.py
"""

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import langid

ROOT = Path(__file__).resolve().parent.parent
CIP = ROOT / "data" / "cip"

SEED = 20261002
TARGET = 200
CAP = 25
MIN_CHARS, MAX_CHARS = 80, 1500
LANGUAGES = ["en", "fa", "ar", "he", "fr", "ru", "tr"]  # CIP's language enum, less 'other'
TASKS = {"c1": "actor_type", "c2": "claim_type"}
MISSES = ("over_1500", "under_80", "not_english")  # closest miss first

langid.set_languages(LANGUAGES)


def passage_miss(p):
    if langid.classify(p["text"])[0] != "en":
        return "not_english"
    if p["chars"] < MIN_CHARS:
        return "under_80"
    if p["chars"] > MAX_CHARS:
        return "over_1500"
    return None


def eligible_passage(passages):
    """(the first eligible passage, None), or (None, the closest miss)."""
    misses = []
    for p in passages:
        miss = passage_miss(p)
        if miss is None:
            return p, None
        misses.append(miss)
    return None, min(misses, key=MISSES.index) if misses else "no_passage"


def quota(sizes, target=TARGET, cap=CAP):
    """The largest equal per-class quota k <= cap with sum(min(size, k)) <= target."""
    k = 0
    while k < cap and sum(min(s, k + 1) for s in sizes) <= target:
        k += 1
    return k


def draw(rows, key, target=TARGET, cap=CAP, seed=SEED):
    """Stratified draw then random fill. Returns (items sorted by id with `drawn_by`, info)."""
    rng = random.Random(seed)
    by_class = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["id"]):
        by_class[row["prod_c"][key]].append(row)
    classes = sorted(by_class)
    k = quota([len(by_class[c]) for c in classes], target, cap)
    chosen, stratified = {}, {}
    for c in classes:
        picks = rng.sample(by_class[c], min(k, len(by_class[c])))
        stratified[c] = len(picks)
        chosen.update({r["id"]: {**r, "drawn_by": "stratum"} for r in picks})
    rest = [r for c in classes for r in by_class[c] if r["id"] not in chosen]
    fill = rng.sample(rest, min(target - len(chosen), len(rest)))
    chosen.update({r["id"]: {**r, "drawn_by": "fill"} for r in fill})
    items = [chosen[i] for i in sorted(chosen)]
    return items, {"quota": k, "stratified": stratified, "fill": len(fill),
                   "eligible": {c: len(by_class[c]) for c in classes}}


def item(row, p):
    out = {k: v for k, v in row.items() if k != "passages"}
    return {**out, "passage": p["text"], "event_id": p["event_id"], "chars": p["chars"]}


def task(pool, key, target, cap):
    rows, dropped = [], Counter()
    for row in pool:
        if row["prod_c"].get(key) is None:
            dropped["no_label"] += 1
            continue
        p, miss = eligible_passage(row["passages"])
        if p is None:
            dropped[miss] += 1
            continue
        rows.append(item(row, p))
    items, info = draw(rows, key, target, cap)
    labels = Counter(r["prod_c"][key] for r in items)
    return items, {"pool": len(pool), "dropped": dict(sorted(dropped.items())),
                   "eligible_total": len(rows), **info,
                   "sampled": dict(sorted(labels.items()))}


def sample_md(summary, rule):
    lines = [
        "# CIP set C sample", "",
        "Written by src/cip_sample.py from the slice 07 export. Internal: data/cip/ is git-ignored.", "",
        "## Provenance rule (from export_summary.json)", "", rule, "",
        "## Method", "",
        f"- Seed {SEED}; target {summary['target']} per task; cap {summary['cap']} per class.",
        f"- Passage eligible when English (langid over {', '.join(LANGUAGES)}) and "
        f"{MIN_CHARS} to {MAX_CHARS} characters; the first eligible passage by event id is used.",
        "- Equal per-class quota: the largest k <= cap whose strata fit the target (founder ruling "
        "2026-10-03; PRD §5.2's 25 per class cannot fit 200 on C1), then random fill.",
        "- C1 strata: actor_type. C2 strata: claim_type (founder ruling 2026-10-03).", "",
    ]
    for name, key in TASKS.items():
        s = summary[name]
        lines += [
            f"## {name.upper()} ({key})", "",
            f"- Pool {s['pool']}; dropped {s['dropped']}; eligible {s['eligible_total']}.",
            f"- quota {s['quota']} per class; stratified {sum(s['stratified'].values())}; "
            f"random fill {s['fill']}; sampled {sum(s['sampled'].values())}.", "",
            "| Class | Eligible | Stratum | Sampled |", "|---|---|---|---|",
        ]
        lines += [f"| {c} | {s['eligible'][c]} | {s['stratified'][c]} | {s['sampled'].get(c, 0)} |"
                  for c in s["eligible"]]
        lines.append("")
    return "\n".join(lines)


def run(cip_dir=CIP, target=TARGET, cap=CAP):
    rule = json.loads((cip_dir / "export_summary.json").read_text(encoding="utf-8"))["provenance_rule"]
    summary = {"seed": SEED, "target": target, "cap": cap}
    for name, key in TASKS.items():
        with open(cip_dir / f"{name}_pool.jsonl", encoding="utf-8") as f:
            pool = [json.loads(line) for line in f]
        items, summary[name] = task(pool, key, target, cap)
        with open(cip_dir / f"{name}_items.jsonl", "w", encoding="utf-8", newline="\n") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in items)
    (cip_dir / "SAMPLE.md").write_text(sample_md(summary, rule), encoding="utf-8")
    return summary


def main():
    summary = run()
    print(json.dumps({k: {x: v for x, v in summary[k].items() if x != "eligible"}
                      for k in TASKS}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
