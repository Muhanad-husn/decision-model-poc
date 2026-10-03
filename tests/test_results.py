"""results.py on toy runs laid out as the runners write them: a two-axis Axial-shaped set and a
one-question C1-shaped set, small enough that every asserted figure is worked by hand in the
comment above it. The committed results/ files are checked for intervals and for text."""

import csv
import json
from pathlib import Path

import pytest

from src import results

ROOT = Path(__file__).resolve().parent.parent

FIELD = ["state", "violence", "ideology"]
SCHOOL = ["A", "B", "C"]
ACTOR = ["state", "military", "ngo"]
Q = lambda options: {"type": "choice", "instructions": "x", "criteria": {o: o for o in options}}  # noqa: E731

AXIAL_TEXT = [f"TOY AXIAL PASSAGE {n} KAPPA" for n in range(6)]
CIP_NAMES = ["Alpha Unit", "Bravo Wing", "Charlie Aid", "Delta Corps"]
CIP_PASSAGES = [f"TOY CIP PASSAGE {n} ZETA" for n in range(4)]

# Axial-shaped items: field has one reference draw, theory_school three. PROD-A carries a
# theory_school value on purpose, to show it is left out of that axis.
AXIAL = [
    # field ref, school ref, school draws, contested, PROD-A field
    ("state", "A", ["A", "A", "A"], False, "state"),
    ("violence", "B", ["B", "B", "C"], True, "state"),
    ("ideology", "A", ["A", "A", "A"], False, "ideology"),
    ("state", None, ["A", "B", "C"], True, "state"),
    ("violence", "C", ["C", "C", "C"], False, "violence"),
    ("state", "B", ["B", "A", "B"], True, "violence"),
]
# Jev picks and confidences, run 1. field: misses on items 2 and 5. theory_school: miss on 1.
JEV_FIELD = [("state", 0.5), ("violence", 0.5), ("state", 0.5), ("state", 0.5), ("violence", 0.5), ("ideology", 0.5)]
JEV_SCHOOL = [("A", 0.9), ("C", 0.3), ("A", 0.8), ("B", 0.2), ("C", 0.7), ("B", 0.4)]

# C1-shaped items: three S55 draws per item; the reference is their majority.
C1_DRAWS = [["state"] * 3, ["military", "military", "ngo"], ["ngo"] * 3, ["state", "military", "ngo"]]
C1_PROD = ["state", "ngo", "ngo", "state"]
JEV_ACTOR = [("state", 0.9), ("military", 0.4), ("state", 0.8), ("ngo", 0.1)]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def answer(options, pick, confidence, bump=0.0):
    rest = 0.4 / (len(options) - 1)
    probs = {o: (0.6 - bump if o == pick else rest + bump / (len(options) - 1)) for o in options}
    return {"type": "choice", "choice": pick, "confidence": confidence, "probabilities": probs}


def jev_run(path, ids, answers_by_axis, options_by_axis, bump_first=0.0):
    rows = []
    for n, item_id in enumerate(ids):
        answers = {axis: answer(options_by_axis[axis], *picks[n], bump=bump_first if n == 0 else 0.0)
                   for axis, picks in answers_by_axis.items()}
        rows.append({"item_id": item_id, "request_hash": "h", "status": 200, "latency_ms": 100.0 * (n + 1),
                     "attempts": 1, "input_tokens": 1000, "parsed": True, "error": None,
                     "response": {"model": "jev-1.13.0", "answers": answers}})
    write_jsonl(path / "responses.jsonl", rows)


def s55_run(path, ids, labels_per_draw):
    for k, labels in enumerate(labels_per_draw, 1):
        d = path / f"draw_{k}"
        write_jsonl(d / "labels.jsonl", [{"id": i, "draw": k, "labels": lab, "reasked": False}
                                         for i, lab in zip(ids, labels)])
        calls = [
            {"n": 1, "kind": "calibration", "ids": [], "duration_ms": 500, "usage": {"input_tokens": 462}},
            {"n": 2, "kind": "batch", "ids": list(ids), "duration_ms": 1000 * len(ids),
             "usage": {"output_tokens": 100_000}},  # $1.00 at $10/M output
        ]
        write_jsonl(d / "calls.jsonl", calls)
        (d / "calls").mkdir()
        (d / "calls" / "001-calibration.json").write_text(json.dumps({"total_cost_usd": 0.000924}), encoding="utf-8")
        (d / "calls" / "002-batch.json").write_text(json.dumps({"total_cost_usd": 1.0}), encoding="utf-8")
        (d / "summary.json").write_text(json.dumps({"harness_overhead_input_tokens": 462}), encoding="utf-8")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("toy")
    axial_ids = [f"ax-{n}" for n in range(6)]
    write_jsonl(tmp / "axial.jsonl", [
        {"id": i, "source": "s", "text": AXIAL_TEXT[n],
         "reference": {"field": f, "theory_school": t},
         "draws": {"field": [f], "theory_school": d},
         "contested": {"theory_school": c},
         "prod_a": {"field": p, "theory_school": t}}
        for n, (i, (f, t, d, c, p)) in enumerate(zip(axial_ids, AXIAL))])
    axial_q = {"field": Q(FIELD), "theory_school": Q(SCHOOL)}
    opts = {"field": FIELD, "theory_school": SCHOOL}
    picks = {"field": JEV_FIELD, "theory_school": JEV_SCHOOL}
    jev_run(tmp / "jev" / "ax1", axial_ids, picks, opts)
    jev_run(tmp / "jev" / "ax2", axial_ids, picks, opts, bump_first=0.05)
    # S55 on Axial: field equals the reference except draw 3 on item 0; theory_school copies
    # the S5-REF draws.
    s55_ax = []
    for k in range(3):
        s55_ax.append([{"field": ("violence" if (k == 2 and n == 0) else f), "theory_school": d[k]}
                       for n, (f, t, d, c, p) in enumerate(AXIAL)])
    s55_run(tmp / "s55" / "ax", axial_ids, s55_ax)

    c1_ids = [f"c1-{n}" for n in range(4)]
    write_jsonl(tmp / "c1.jsonl", [
        {"id": i, "name": CIP_NAMES[n], "prod_c": {"actor_type": C1_PROD[n]}, "passage": CIP_PASSAGES[n],
         "event_id": "e", "chars": 20, "drawn_by": "stratum"} for n, i in enumerate(c1_ids)])
    jev_run(tmp / "jev" / "c11", c1_ids, {"actor_type": JEV_ACTOR}, {"actor_type": ACTOR})
    jev_run(tmp / "jev" / "c12", c1_ids, {"actor_type": JEV_ACTOR}, {"actor_type": ACTOR})
    s55_run(tmp / "s55" / "c1", c1_ids, [[{"actor_type": d[k]} for d in C1_DRAWS] for k in range(3)])

    config = {
        "axial": {"kind": "axial", "items": tmp / "axial.jsonl", "questions": axial_q,
                  "jev": (tmp / "jev" / "ax1", tmp / "jev" / "ax2"), "s55": tmp / "s55" / "ax"},
        "c1": {"kind": "cip", "items": tmp / "c1.jsonl", "questions": {"actor_type": Q(ACTOR)},
               "jev": (tmp / "jev" / "c11", tmp / "jev" / "c12"), "s55": tmp / "s55" / "c1"},
    }
    out = tmp / "results"
    data = results.build(config)
    results.write(data, out)
    return data, out


def test_agreement_with_the_reference_per_axis_and_arm(built):
    data, _ = built
    field = data["sets"]["axial"]["axes"]["field"]["vs_reference"]
    # JEV field: items 0, 1, 3, 4 right of 6 -> 4/6.
    assert field["JEV"]["agreement"] == pytest.approx(4 / 6)
    # PROD-A field: wrong on items 1 and 5 -> 4/6.
    assert field["PROD-A"]["agreement"] == pytest.approx(4 / 6)
    # S55 majority: draw 3's slip on item 0 is outvoted -> 6/6. Single draws: 6/6, 6/6, 5/6,
    # mean 17/18.
    assert field["S55-maj"]["agreement"] == pytest.approx(1.0)
    assert field["S55-draw"]["agreement"] == pytest.approx(17 / 18)
    # theory_school is referenced on 5 items (item 3 has no majority); JEV misses item 1 -> 4/5.
    school = data["sets"]["axial"]["axes"]["theory_school"]["vs_reference"]
    assert school["JEV"]["n"] == 5
    assert school["JEV"]["agreement"] == pytest.approx(0.8)


def test_prod_a_is_left_out_of_theory_school(built):
    data, out = built
    assert "PROD-A" not in data["sets"]["axial"]["axes"]["theory_school"]["vs_reference"]
    rows = list(csv.DictReader(open(out / "agreement_by_axis_arm.csv", encoding="utf-8")))
    assert not [r for r in rows if r["axis"] == "theory_school" and r["arm"] == "PROD-A"]
    assert [r for r in rows if r["axis"] == "field" and r["arm"] == "PROD-A"]


def test_doubt_auroc_on_contested_items(built):
    data, _ = built
    doubt = data["sets"]["axial"]["axes"]["theory_school"]["doubt"]
    # 1 - confidence: contested .7, .8, .6 all above unanimous .1, .2, .3 -> AUROC 1.0.
    assert (doubt["contested"], doubt["unanimous"]) == (3, 3)
    assert doubt["auroc"] == pytest.approx(1.0)
    assert "doubt" not in data["sets"]["axial"]["axes"]["field"]  # one reference draw, no flag


def test_cip_reference_is_the_s55_draw_majority_and_prod_c_a_comparator(built):
    data, _ = built
    c1 = data["sets"]["c1"]["axes"]["actor_type"]
    # Majority: state, military, ngo, none. JEV right on items 0 and 1 of 3 referenced -> 2/3.
    # PROD-C: state, ngo, ngo -> right on 0 and 2 -> 2/3.
    assert c1["vs_reference"]["JEV"]["agreement"] == pytest.approx(2 / 3)
    assert c1["vs_reference"]["PROD-C"]["agreement"] == pytest.approx(2 / 3)
    # JEV against each draw: 2/4, 2/4, 2/4 -> 0.5. Draws pairwise: 3/4, 2/4, 2/4 -> 7/12.
    coder = c1["coder_agreement"]
    assert coder["arms"]["JEV"]["agreement"] == pytest.approx(0.5)
    assert coder["draws_pairwise"]["agreement"] == pytest.approx(7 / 12)
    # Contested: items 1 and 3 (doubt .6, .9) above unanimous 0 and 2 (.1, .2) -> 1.0.
    assert c1["doubt"]["auroc"] == pytest.approx(1.0)


def test_determinism_across_the_two_runs(built):
    data, _ = built
    # Run 2 shifts item 0's probabilities by .05 without moving any argmax.
    det = data["sets"]["axial"]["determinism"]
    assert det["identical_argmax"] == pytest.approx(1.0)
    assert det["max_abs_diff"] == pytest.approx(0.05)


def test_cost_per_1000_and_latency(built):
    data, out = built
    jev = data["cost_latency"]["axial"]["JEV"]
    # 1,000 input tokens per item at $0.042/M -> $0.042 per 1,000 items.
    assert jev["cost_per_1000_usd"] == pytest.approx(0.042)
    # Latencies 100..600 ms in both runs: p50 350, p95 at rank 0.95 x 11 = 10.45 of the twelve
    # pooled values -> 600.
    assert jev["latency_ms"]["p50"] == pytest.approx(350.0)
    assert jev["latency_ms"]["p95"] == pytest.approx(600.0)
    s55 = data["cost_latency"]["axial"]["S55"]
    # $1.00 per draw for 6 items -> $166.67 per 1,000; the CLI's own list cost agrees.
    assert s55["cost_per_1000_usd"] == pytest.approx(1000 / 6)
    assert s55["cli_reported_usd"] == pytest.approx(s55["cost_usd"])
    # One batch of 6 in 6,000 ms -> 1,000 ms per item.
    assert s55["latency_ms"]["p50"] == pytest.approx(1000.0)
    # Pooled over both sets: JEV 10 items x $0.000042, S55 10 items x $1/6 or $1/4 per draw.
    pooled = data["cost_latency"]["all"]
    assert pooled["JEV"]["cost_per_1000_usd"] == pytest.approx(0.042)
    assert pooled["S55"]["cost_per_1000_usd"] == pytest.approx(2 / 10 * 1000)
    rows = list(csv.DictReader(open(out / "cost_latency.csv", encoding="utf-8")))
    assert {(r["set"], r["arm"], r["scope"]) for r in rows} >= {("axial", "JEV", "single"), ("all", "S55", "single")}


def _figures(node, path=""):
    """Every dict in the tree that holds an agreement or AUROC figure."""
    if isinstance(node, dict):
        if any(isinstance(node.get(k), (int, float)) for k in ("agreement", "auroc")):
            yield path, node
        for k, v in node.items():
            yield from _figures(v, f"{path}/{k}")
    elif isinstance(node, list):
        for n, v in enumerate(node):
            yield from _figures(v, f"{path}/{n}")


def _assert_intervals(data):
    found = list(_figures(data))
    assert found
    for path, node in found:
        ci = node.get("ci")
        assert ci is not None and len(ci) == 2 and ci[0] <= ci[1], path


def test_every_agreement_and_auroc_carries_a_95_percent_interval(built):
    data, out = built
    _assert_intervals(data)
    _assert_intervals(json.loads((out / "metrics.json").read_text(encoding="utf-8")))


def test_outputs_hold_no_passage_or_cip_text(built):
    _, out = built
    for f in out.iterdir():
        body = f.read_text(encoding="utf-8")
        for text in AXIAL_TEXT + CIP_NAMES + CIP_PASSAGES:
            assert text not in body, (f.name, text)


def test_csv_columns_are_fixed():
    assert results.CSV_COLUMNS == {
        "agreement_by_axis_arm.csv": ["set", "axis", "arm", "reference", "n", "agreement", "ci_low", "ci_high", "kappa"],
        "selective_agreement.csv": ["set", "axis", "method", "coverage", "kept", "threshold", "agreement",
                                    "ci_low", "ci_high"],
        "cost_latency.csv": ["set", "arm", "scope", "items", "calls", "cost_usd", "cost_per_1000_usd",
                             "latency_p50_ms", "latency_p95_ms"],
    }


COMMITTED = ROOT / "results"


@pytest.mark.skipif(not (COMMITTED / "metrics.json").exists(), reason="results not built yet")
def test_committed_results_carry_intervals_and_no_item_text():
    _assert_intervals(json.loads((COMMITTED / "metrics.json").read_text(encoding="utf-8")))
    for name, columns in results.CSV_COLUMNS.items():
        with open(COMMITTED / name, encoding="utf-8") as f:
            assert next(csv.reader(f)) == columns
    texts = []
    for path, keys in ((ROOT / "data" / "axial" / "items.jsonl", ("text",)),
                       (ROOT / "data" / "cip" / "c1_items.jsonl", ("name", "passage")),
                       (ROOT / "data" / "cip" / "c2_items.jsonl", ("claim_text", "passage"))):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                texts += [row[k] for k in keys if len(row[k]) >= 12]
    bodies = [f.read_text(encoding="utf-8") for f in COMMITTED.iterdir()]
    assert not [t for t in texts if any(t in b for b in bodies)]
