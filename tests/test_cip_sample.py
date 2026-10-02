"""The CIP sample (PRD §5.2, founder rulings of 2026-10-03): passage drops (not English, under
80 or over 1,500 characters), the equal per-class quota under the cap of 25, the random fill,
and the same items on every run with the seed. Toy pools only; the real export is not read."""

import json

import pytest

from src.cip_sample import draw, eligible_passage, quota, run

EN = "The ministry said the strike hit a fuel depot near the border crossing late on Tuesday night."
FA = "وزارت اعلام کرد که حمله به یک انبار سوخت در نزدیکی گذرگاه مرزی در اواخر شب سه‌شنبه انجام شد."


def passage(text, event_id="e1"):
    return {"event_id": event_id, "text": text, "source_lang": "en", "chars": len(text)}


def actor(n, label, passages=None):
    return {"id": f"a{n:03d}", "name": f"Actor {n}", "prod_c": {"actor_type": label},
            "passages": passages or [passage(EN)]}


def claim(n, ctype, subject="other", passages=None):
    return {"id": f"c{n:03d}", "claim_text": f"Claim {n}.", "claim_language": "fa",
            "prod_c": {"claim_type": ctype, "claim_subject_type": subject},
            "passages": passages or [passage(EN)]}


def write_pool(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


# --- eligibility ------------------------------------------------------------------------

def test_first_english_passage_inside_80_to_1500_is_taken():
    long = EN * 20
    chosen, reason = eligible_passage([passage(FA, "e1"), passage(long, "e2"), passage(EN, "e3")])
    assert (chosen["event_id"], reason) == ("e3", None)


@pytest.mark.parametrize("texts, reason", [
    ([FA], "not_english"),
    (["Strike reported near the border."], "under_80"),
    ([EN * 20], "over_1500"),
    # The reason is the closest miss: an English passage that is only too long beats Persian.
    ([FA, EN * 20], "over_1500"),
])
def test_items_without_an_eligible_passage_carry_the_closest_reason(texts, reason):
    assert eligible_passage([passage(t, f"e{i}") for i, t in enumerate(texts)]) == (None, reason)


# --- the equal quota --------------------------------------------------------------------

def test_quota_is_the_largest_equal_share_that_fits():
    # C1 on the real export: 15 classes of 20 or more and one of 4.
    # k = 13: 4 + 15 x 13 = 199 <= 200; k = 14: 4 + 15 x 14 = 214 > 200.
    sizes = [906, 875, 471, 434, 175, 140, 130, 125, 91, 76, 65, 53, 35, 23, 20, 4]
    assert quota(sizes, target=200, cap=25) == 13


def test_quota_stops_at_the_cap():
    # C2 by claim_type: eight classes of 100 or more give 8 x 25 = 200 exactly.
    assert quota([11254, 3281, 2190, 1221, 759, 440, 437, 100], target=200, cap=25) == 25


def test_quota_when_every_class_is_small():
    assert quota([3, 2], target=200, cap=25) == 25  # nothing binds; all 5 items are taken


# --- the draw ---------------------------------------------------------------------------

def toy_actors():
    rows = [actor(n, "government") for n in range(40)]
    rows += [actor(100 + n, "police") for n in range(6)]
    rows += [actor(200 + n, "ethnic_militia") for n in range(2)]
    return rows


def test_strata_hold_the_quota_then_fill_to_target():
    sample, info = draw(toy_actors(), "actor_type", target=12, cap=5, seed=7)
    # k: min(40,k) + min(6,k) + min(2,k) <= 12 -> k = 5 gives 5 + 5 + 2 = 12.
    assert info["quota"] == 5
    assert info["stratified"] == {"ethnic_militia": 2, "government": 5, "police": 5}
    assert info["fill"] == 0 and len(sample) == 12


def test_random_fill_tops_up_when_the_quota_leaves_room():
    sample, info = draw(toy_actors(), "actor_type", target=20, cap=5, seed=7)
    assert info["stratified"] == {"ethnic_militia": 2, "government": 5, "police": 5}
    assert info["fill"] == 8 and len(sample) == 20
    assert len({r["id"] for r in sample}) == 20


def test_same_seed_same_items_other_seed_other_items():
    a, _ = draw(toy_actors(), "actor_type", target=20, cap=5, seed=20261002)
    b, _ = draw(list(reversed(toy_actors())), "actor_type", target=20, cap=5, seed=20261002)
    c, _ = draw(toy_actors(), "actor_type", target=20, cap=5, seed=1)
    assert [r["id"] for r in a] == [r["id"] for r in b]
    assert [r["id"] for r in a] != [r["id"] for r in c]


# --- the whole run ----------------------------------------------------------------------

@pytest.fixture
def export(tmp_path):
    actors = toy_actors() + [
        actor(300, "government", [passage(FA)]),
        actor(301, "police", [passage("Too short to be a passage at all.")]),
        actor(302, "military", [passage(EN * 20)]),
    ]
    claims = [claim(n, "factual_assertion") for n in range(30)]
    claims += [claim(100 + n, "denial", "casualty_count") for n in range(3)]
    claims += [claim(200, None), claim(201, "threat", passages=[passage(FA)])]
    write_pool(tmp_path / "c1_pool.jsonl", actors)
    write_pool(tmp_path / "c2_pool.jsonl", claims)
    (tmp_path / "export_summary.json").write_text(
        json.dumps({"provenance_rule": "- toy rule"}), encoding="utf-8"
    )
    return tmp_path


def test_run_twice_writes_identical_items_and_counts_drops(export):
    first = run(export, target=10, cap=4)
    files = {n: (export / n).read_bytes() for n in ("c1_items.jsonl", "c2_items.jsonl")}
    second = run(export, target=10, cap=4)
    assert files == {n: (export / n).read_bytes() for n in files}
    assert first == second
    assert first["c1"]["dropped"] == {"not_english": 1, "over_1500": 1, "under_80": 1}
    assert first["c2"]["dropped"] == {"no_label": 1, "not_english": 1}


def test_items_carry_the_chosen_passage_and_the_label(export):
    run(export, target=10, cap=4)
    c2 = [json.loads(line) for line in (export / "c2_items.jsonl").read_text("utf-8").splitlines()]
    assert len(c2) == 10
    denial = [r for r in c2 if r["prod_c"]["claim_type"] == "denial"]
    assert len(denial) == 3  # under the quota of 4, so all three are in
    assert all(r["passage"] == EN and r["event_id"] == "e1" for r in c2)
    assert {"id", "claim_text", "prod_c", "passage", "event_id", "chars", "drawn_by"} <= set(c2[0])


def test_sample_md_records_rule_drops_and_quota(export):
    run(export, target=10, cap=4)
    text = (export / "SAMPLE.md").read_text(encoding="utf-8")
    assert "- toy rule" in text
    assert "20261002" in text
    assert "not_english" in text and "quota" in text
