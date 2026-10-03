"""Apply the PRD §7 metrics to the stored runs and write results/ (slice 15): metrics.json and
the chart-ready agreement_by_axis_arm.csv, selective_agreement.csv and cost_latency.csv.

References. Axial is scored against S5-REF (the `reference` per axis in items.jsonl, with its
draws and contested flags); a CIP set against the majority of the three S55 draws, whose
disagreement is the contested flag there. PROD-A (Axial) and PROD-C (CIP) are comparators.
PROD-A is left out of `theory_school` (PRD §5.1: tagged before `not-applicable` existed).

Arms. JEV is run 1's choice, with its returned `confidence` as the doubt signal (PRD §12).
Run 2 enters only through determinism. On Axial, S55-maj is the majority of the three S55
draws (no majority is a miss) and S55-draw the mean agreement of the single draws. Every
agreement figure and every AUROC carries a 95% bootstrap interval from src/metrics.py; kappa,
Brier, ECE, cost and latency are point figures, as PRD §7 asks.

Cost. JEV is every logged call's input tokens at $0.042/M; S55 is each labelling call's logged
usage at the Sonnet 5.5 list price, beside the list cost the CLI itself reported for the same
calls. "single" is one pass over the set: the mean of JEV's two runs, the mean of S55's three
draws. Latency is per item: JEV per call, S55 call duration over the call's items; "single"
pools the runs or draws.

The outputs hold item counts, labels and figures only: no item id, passage, name or claim text.

Run: uv run python src/results.py
"""

import csv
import json
import math
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import metrics as m
from src.jev import parse_answers

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
JEV_RUNS = ROOT / "runs" / "jev"
S55_RUNS = ROOT / "runs" / "s55"

# The runs the report is scored on (REPORT.md run log names the ones set aside).
RUNS = {
    "axial": {"jev": ("axial-run1-20261003", "axial-run2-20261003"), "s55": "axial-20261003b"},
    "c1": {"jev": ("c1-run1-i15-20261003", "c1-run2-i15-20261003"), "s55": "c1-i16-20261003b"},
    "c2": {"jev": ("c2-run1-i15-20261003", "c2-run2-i15-20261003"), "s55": "c2-i16-20261003"},
}
PROD_A_EXCLUDED = {"theory_school"}
FULL_COVERAGE = 1.0

CSV_COLUMNS = {
    "agreement_by_axis_arm.csv": ["set", "axis", "arm", "reference", "n", "agreement", "ci_low", "ci_high", "kappa"],
    "selective_agreement.csv": ["set", "axis", "method", "coverage", "kept", "threshold", "agreement",
                                "ci_low", "ci_high"],
    "cost_latency.csv": ["set", "arm", "scope", "items", "calls", "cost_usd", "cost_per_1000_usd",
                         "latency_p50_ms", "latency_p95_ms"],
}


# --- loading -------------------------------------------------------------------------------


def _jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_jev(run_dir, questions):
    """({item_id: parsed answers}, every logged call). A later row for an item replaces an
    earlier one; every row is a billed call. Probabilities are keyed in option order."""
    rows = _jsonl(Path(run_dir) / "responses.jsonl")
    answers = {r["item_id"]: parse_answers(r.get("response") or {}, questions) for r in rows}
    # Jev orders the probability keys differently from run to run; the question's option order
    # makes a tied argmax break the same way in every run.
    for parsed in answers.values():
        for axis, a in parsed.items():
            a["probabilities"] = {o: a["probabilities"][o] for o in questions[axis]["criteria"]}
    return answers, rows


def load_s55(run_dir):
    """One entry per draw directory, in draw order: its labels by item, its calls, the list cost
    the CLI reported per call, and the harness overhead it measured."""
    draws = []
    for d in sorted(Path(run_dir).glob("draw_*"), key=lambda p: int(p.name.split("_")[1])):
        calls = _jsonl(d / "calls.jsonl")
        reported = [json.loads((d / "calls" / f"{c['n']:03d}-{c['kind']}.json").read_text(encoding="utf-8"))
                    .get("total_cost_usd") for c in calls]
        summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        draws.append({
            "labels": {r["id"]: r["labels"] for r in _jsonl(d / "labels.jsonl")},
            "calls": calls,
            "cli_usd": sum(u or 0.0 for c, u in zip(calls, reported) if c["ids"]),
            "harness_overhead_input_tokens": summary.get("harness_overhead_input_tokens"),
        })
    return draws


def default_config():
    from src import cip
    from src.codebook import questions as axial_questions

    config = {}
    for name, runs in RUNS.items():
        kind = "axial" if name == "axial" else "cip"
        config[name] = {
            "kind": kind,
            "items": ROOT / "data" / "axial" / "items.jsonl" if kind == "axial" else cip.ITEMS[name],
            "questions": axial_questions() if kind == "axial" else cip.questions(name),
            "jev": tuple(JEV_RUNS / r for r in runs["jev"]),
            "s55": S55_RUNS / runs["s55"],
        }
    return config


# --- figures -------------------------------------------------------------------------------


def _ci(stat, n):
    ci = m.bootstrap_ci(stat, n)
    return list(ci) if ci else None


def _vs_reference(arm, ref):
    return {"n": sum(m._valid(r) for r in ref), "agreement": m.agreement(arm, ref),
            "ci": list(m.agreement_ci(arm, ref) or ()) or None, "kappa": m.kappa(arm, ref)}


def _draw_mean(draws, ref):
    """Mean agreement of single draws with the reference, the draws resampled together."""
    def stat(idx):
        return m._mean([m.agreement(m._take(d, idx), m._take(ref, idx)) for d in draws])

    return {"n": sum(m._valid(r) for r in ref), "agreement": stat(range(len(ref))), "ci": _ci(stat, len(ref)),
            "kappa": m._mean([m.kappa(d, ref) for d in draws])}


def _coder(arms, draws):
    n = len(draws[0])
    pair = m.coder_agreement(draws[0], draws)["draws_pairwise"]
    pair_ci = m.coder_agreement_ci(draws[0], draws)["draws_pairwise"]
    out = {"draws": len(draws), "draws_pairwise": {"agreement": pair, "ci": list(pair_ci) if pair_ci else None},
           "arms": {}}
    for name, arm in arms.items():
        def stat(idx, arm=arm):
            return m.coder_agreement(m._take(arm, idx), [m._take(d, idx) for d in draws])["arm_mean"]

        out["arms"][name] = {"agreement": stat(range(n)), "ci": _ci(stat, n)}
    return out


def _doubt(confidence, flags):
    return {"contested": sum(flags), "unanimous": len(flags) - sum(flags),
            "auroc": m.auroc_doubt(confidence, flags), "ci": list(m.auroc_doubt_ci(confidence, flags) or ()) or None}


def _selective(arm, ref, confidence):
    n = len(ref)
    rows = []
    for cov, fig in m.selective_agreement(arm, ref, confidence).items():
        def stat(idx, cov=cov):
            return m.selective_agreement(m._take(arm, idx), m._take(ref, idx), m._take(confidence, idx),
                                         coverages=(cov,))[cov]["agreement"]

        rows.append({"coverage": cov, **fig, "ci": _ci(stat, n)})
    full = _vs_reference(arm, ref)
    rows.append({"coverage": FULL_COVERAGE, "kept": full["n"], "threshold": None,
                 "agreement": full["agreement"], "ci": full["ci"]})
    return sorted(rows, key=lambda r: -r["coverage"])


def _best_of_3(draws, ref):
    fig = m.best_of_3_abstention(draws, ref)

    def stat(idx):
        return m.best_of_3_abstention([m._take(d, idx) for d in draws], m._take(ref, idx))["agreement"]

    return {**fig, "ci": _ci(stat, len(ref))}


def _argmax(probs):
    return max(probs, key=probs.get)  # the tie rule of src/metrics.py


def determinism_figures(p1_by_axis, p2_by_axis, c1_by_axis, c2_by_axis):
    """Per axis from metrics.determinism, and over the set: an item is identical only when
    every one of its questions has the same argmax in both runs. Jev's returned choice is not
    always the argmax of its rounded probabilities, so identical choice is reported beside it."""
    axes = list(p1_by_axis)
    n = len(p1_by_axis[axes[0]])
    per_axis = {}
    for a in axes:
        same_choice = sum(x == y for x, y in zip(c1_by_axis[a], c2_by_axis[a], strict=True))
        per_axis[a] = {**m.determinism(p1_by_axis[a], p2_by_axis[a]), "identical_choice": same_choice / n}
    argmax = sum(all(_argmax(p1_by_axis[a][i]) == _argmax(p2_by_axis[a][i]) for a in axes) for i in range(n))
    choice = sum(all(c1_by_axis[a][i] == c2_by_axis[a][i] for a in axes) for i in range(n))
    return {"items": n, "identical_argmax": argmax / n, "identical_choice": choice / n,
            "max_abs_diff": max(d["max_abs_diff"] for d in per_axis.values())}, per_axis


def set_metrics(cfg):
    """Every agreement, doubt, selective, calibration and determinism figure for one set."""
    items = _jsonl(cfg["items"])
    ids = [it["id"] for it in items]
    questions = cfg["questions"]
    (jev1, _), (jev2, _) = (load_jev(d, questions) for d in cfg["jev"])
    s55 = load_s55(cfg["s55"])
    for name, got in [("JEV run 1", jev1), ("JEV run 2", jev2)] + [(f"S55 draw {k}", d["labels"])
                                                                   for k, d in enumerate(s55, 1)]:
        missing = [i for i in ids if i not in got]
        if missing:
            raise ValueError(f"{name} has no answer for {len(missing)} of {len(ids)} items in {cfg['items']}")
    axial = cfg["kind"] == "axial"
    out = {"items": len(ids), "reference": "S5-REF" if axial else "S55 draw majority", "axes": {}}
    p1_all, p2_all, c1_all, c2_all = {}, {}, {}, {}
    for axis in questions:
        jev = [jev1[i][axis]["choice"] for i in ids]
        conf = [jev1[i][axis]["confidence"] for i in ids]
        p1_all[axis] = [jev1[i][axis]["probabilities"] for i in ids]
        p2_all[axis] = [jev2[i][axis]["probabilities"] for i in ids]
        c1_all[axis], c2_all[axis] = jev, [jev2[i][axis]["choice"] for i in ids]
        s55_draws = [[d["labels"][i].get(axis) for i in ids] for d in s55]
        if axial:
            ref = [it["reference"].get(axis) for it in items]
            ref_draws = [list(col) for col in zip(*(it["draws"][axis] for it in items))]
            flags = [it["contested"][axis] for it in items] if len(ref_draws) > 1 else None
            arms = {"JEV": jev}
            if axis not in PROD_A_EXCLUDED:
                arms["PROD-A"] = [it["prod_a"].get(axis) for it in items]
            arms["S55-maj"] = [m.majority(col) for col in zip(*s55_draws)]
        else:
            ref = [m.majority(col) for col in zip(*s55_draws)]
            ref_draws = s55_draws
            flags = [m.contested(col) for col in zip(*s55_draws)]
            arms = {"JEV": jev, "PROD-C": [it["prod_c"].get(axis) for it in items]}
        fig = {"vs_reference": {name: _vs_reference(arm, ref) for name, arm in arms.items()}}
        if axial:
            fig["vs_reference"]["S55-draw"] = _draw_mean(s55_draws, ref)
        if len(ref_draws) > 1:
            fig["coder_agreement"] = _coder(arms, ref_draws)
            fig["doubt"] = _doubt(conf, flags)
        fig["selective"] = {"JEV": _selective(jev, ref, conf)}
        if axial and len(ref_draws) == 3:
            fig["best_of_3"] = {"S5-REF": _best_of_3(ref_draws, ref)}
        fig["calibration"] = {"brier": m.brier(p1_all[axis], ref), "ece": m.ece(p1_all[axis], ref)}
        out["axes"][axis] = fig
    out["determinism"], per_axis = determinism_figures(p1_all, p2_all, c1_all, c2_all)
    for axis, det in per_axis.items():
        out["axes"][axis]["determinism"] = det
    return out


def _pass(items, calls, usd, latencies):
    calls = int(calls) if float(calls).is_integer() else calls
    return {"items": items, "calls": calls, "cost_usd": usd, "cost_per_1000_usd": m.cost_per_1000(usd, items),
            "latency_ms": m.latency_percentiles(latencies)}


def cost_latency(cfg):
    """JEV per run and S55 per draw, each with its single-pass figure."""
    items = len(_jsonl(cfg["items"]))
    jev_runs = [load_jev(d, cfg["questions"])[1] for d in cfg["jev"]]
    s55 = load_s55(cfg["s55"])
    jev = {f"run{k}": _pass(items, len(rows), m.jev_cost_usd(r["input_tokens"] for r in rows),
                            [r["latency_ms"] for r in rows])
           for k, rows in enumerate(jev_runs, 1)}
    jev["single"] = _pass(items, sum(len(r) for r in jev_runs) / len(jev_runs),
                          m._mean([p["cost_usd"] for k, p in jev.items()]),
                          [r["latency_ms"] for rows in jev_runs for r in rows])
    s55_out = {}
    for k, d in enumerate(s55, 1):
        labelling = [c for c in d["calls"] if c["ids"]]
        s55_out[f"draw{k}"] = {**_pass(items, len(labelling), m.s55_draw_cost_usd(d["calls"]),
                                       m.s55_item_latencies(d["calls"])),
                               "cli_reported_usd": d["cli_usd"],
                               "harness_overhead_input_tokens": d["harness_overhead_input_tokens"]}
    draws = list(s55_out.values())
    s55_out["single"] = {**_pass(items, m._mean([p["calls"] for p in draws]), m._mean([p["cost_usd"] for p in draws]),
                                 [v for d in s55 for v in m.s55_item_latencies(d["calls"])]),
                         "cli_reported_usd": m._mean([p["cli_reported_usd"] for p in draws])}
    return {"JEV": {**jev["single"], "scopes": jev}, "S55": {**s55_out["single"], "scopes": s55_out}}


def _pooled(per_set):
    """One single pass over every set: summed items, calls and cost, latencies pooled."""
    out = {}
    for arm in ("JEV", "S55"):
        parts = [s[arm] for s in per_set.values()]
        items = sum(p["items"] for p in parts)
        usd = sum(p["cost_usd"] for p in parts)
        lat = {"n": sum(p["latency_ms"]["n"] for p in parts)}
        out[arm] = {"items": items, "calls": sum(p["calls"] for p in parts), "cost_usd": usd,
                    "cost_per_1000_usd": m.cost_per_1000(usd, items), "latency_ms": lat}
    return out


def build(config=None):
    config = config or default_config()
    sets = {name: set_metrics(cfg) for name, cfg in config.items()}
    cl = {name: cost_latency(cfg) for name, cfg in config.items()}
    cl["all"] = _pooled(cl)
    # Latency percentiles over the pooled sets need the raw values, so recompute them here.
    for arm in ("JEV", "S55"):
        values = []
        for cfg in config.values():
            if arm == "JEV":
                values += [r["latency_ms"] for d in cfg["jev"] for r in load_jev(d, cfg["questions"])[1]]
            else:
                values += [v for d in load_s55(cfg["s55"]) for v in m.s55_item_latencies(d["calls"])]
        cl["all"][arm]["latency_ms"] = m.latency_percentiles(values)
    for name, c in cl.items():
        c["jev_to_s55_cost_ratio"] = c["JEV"]["cost_usd"] / c["JEV"]["items"] / (c["S55"]["cost_usd"] / c["S55"]["items"])
    return {
        "generated_by": "src/results.py",
        "bootstrap": {"resamples": m.RESAMPLES, "seed": m.SEED, "interval": "95% percentile"},
        "runs": {name: {"jev": [Path(d).name for d in cfg["jev"]], "s55": Path(cfg["s55"]).name}
                 for name, cfg in config.items()},
        "prices": {"jev_usd_per_million_input": m.JEV_USD_PER_MILLION, "s55": m.S55_PRICE},
        "sets": sets,
        "cost_latency": cl,
    }


# --- writing -------------------------------------------------------------------------------


def _round(x, places=6):
    if isinstance(x, float):
        return None if math.isnan(x) else round(x, places)
    if isinstance(x, dict):
        return {k: _round(v, places) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, places) for v in x]
    return x


def _ci_cols(ci):
    return (ci[0], ci[1]) if ci else (None, None)


def csv_rows(data):
    agreement, selective, cost = [], [], []
    for set_name, s in data["sets"].items():
        for axis, fig in s["axes"].items():
            for arm, f in fig["vs_reference"].items():
                agreement.append([set_name, axis, arm, s["reference"], f["n"], f["agreement"],
                                  *_ci_cols(f["ci"]), f["kappa"]])
            for arm, f in fig.get("coder_agreement", {}).get("arms", {}).items():
                agreement.append([set_name, axis, f"{arm} vs single draws", "reference draws",
                                  s["items"], f["agreement"], *_ci_cols(f["ci"]), None])
            if "coder_agreement" in fig:
                f = fig["coder_agreement"]["draws_pairwise"]
                agreement.append([set_name, axis, "reference draws pairwise", "reference draws",
                                  s["items"], f["agreement"], *_ci_cols(f["ci"]), None])
            for method, curve in fig["selective"].items():
                for r in curve:
                    selective.append([set_name, axis, method, r["coverage"], r["kept"], r["threshold"],
                                      r["agreement"], *_ci_cols(r["ci"])])
            for method, r in fig.get("best_of_3", {}).items():
                selective.append([set_name, axis, f"{method} best-of-3", r["coverage"], None, None,
                                  r["agreement"], *_ci_cols(r["ci"])])
    for set_name, c in data["cost_latency"].items():
        for arm in ("JEV", "S55"):
            scopes = c[arm].get("scopes", {"single": c[arm]})
            for scope, p in scopes.items():
                cost.append([set_name, arm, scope, p["items"], p["calls"], p["cost_usd"], p["cost_per_1000_usd"],
                             p["latency_ms"]["p50"], p["latency_ms"]["p95"]])
    return {"agreement_by_axis_arm.csv": agreement, "selective_agreement.csv": selective, "cost_latency.csv": cost}


def write(data, out_dir=RESULTS):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(_round(data), indent=2) + "\n", encoding="utf-8")
    for name, rows in csv_rows(data).items():
        with open(out_dir / name, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(CSV_COLUMNS[name])
            w.writerows([["" if v is None else (round(v, 4) if isinstance(v, float) else v) for v in row]
                         for row in rows])


def main():
    data = build()
    write(data)
    for name, s in data["sets"].items():
        print(f"{name}: {s['items']} items, determinism {s['determinism']['identical_argmax']:.3f}")
    for name, c in data["cost_latency"].items():
        print(f"{name}: JEV ${c['JEV']['cost_per_1000_usd']:.4f}/1k, S55 ${c['S55']['cost_per_1000_usd']:.4f}/1k, "
              f"ratio {c['jev_to_s55_cost_ratio']:.5f}")
    print(f"wrote {RESULTS}")


if __name__ == "__main__":
    main()
