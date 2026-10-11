"""End-to-end audit: every output built from ONE load, checked against each other.

Run:  python -m pytest tests/test_pipeline.py -v
"""

import hashlib
import re
from datetime import date

import pytest

from ghatwatch import brief as br
from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import load
from ghatwatch import orders as od
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

D = date(2026, 10, 20)
D7 = date(2026, 10, 27)
GEN = "2026-10-11"

# SHA-256 of the files as supplied in the problem-statement repo
# (track-2-visarjan-ghat-watch/data/, cloned 11 Oct 2026).
SOURCE_SHA256 = {
    "bhopal_ghats_2023_2025.csv": "6068f686d2e78296ad7d165dd6762abf38fed3b908cdb94cd3b240d414329c6b",
    "sample_bhopal_2025.csv": "9056c7f1a2f4bf2c19c6712e3807666929b3b6ff004939f22ff2ca8b54ef92b0",
    "cpcb_water_quality_criteria.csv": "e46fb585c9d699c3689aad1060e529b25a9c548cea373938d48fc5a3dd975180",
    "DATA_DICTIONARY.md": "e9d8621b3936a3efc46d01d8f02ddd66e6c0e960a7372cc2c6d7fb2a0bdd7ffe",
}


def run_pipeline() -> dict:
    data = load.load_all()
    table = cr.load_criteria_table()
    ranking = rk.rank_ghats(data, table)
    plan = pl.plan_actions(ranking)
    orders = od.work_orders(ranking, plan, table=table, readings=data.readings)
    evidence = evm.build_evidence(data, table)
    return {
        "data": data, "table": table, "ranking": ranking, "plan": plan, "orders": orders, "evidence": evidence,
        "csv": evm.evidence_csv_bytes(evidence),
        "orders_md": [od.to_markdown(o) for o in orders],
        "briefs": br.build_briefs(ranking, plan, evidence, table, generated_on=GEN),
    }


@pytest.fixture(scope="module")
def p():
    return run_pipeline()


# 1-2 ------------------------------------------------------------ load and grid

def test_load_grid_and_unchanged_sources(p):
    assert p["data"].summary.expected_cells == len(p["data"].grid) == 1638
    assert p["data"].summary.no_table_cells == 114
    assert p["data"].summary.issues == []
    assert len(p["data"].criteria) == 19
    for name, sha in SOURCE_SHA256.items():
        assert hashlib.sha256((load.DATA_DIR / name).read_bytes()).hexdigest() == sha, name


# 3 ------------------------------------------------------------ comparisons

def test_class_b_and_d(p):
    ev = p["evidence"]
    counts = ev[ev["class_b_result"].isin([cr.PASS, cr.FAIL])].groupby(["parameter", "class_b_result"]).size().to_dict()
    assert counts == {("BOD", "fail"): 100, ("BOD", "pass"): 12, ("Dissolved oxygen", "fail"): 42,
                      ("Dissolved oxygen", "pass"): 74, ("pH", "fail"): 6, ("pH", "pass"): 109}
    severe = ev[(ev["parameter"] == "Dissolved oxygen") & (ev["class_d_result"] == cr.FAIL)]
    assert len(severe) == 17 == sum(g.metrics.do_severe for g in p["ranking"].ghats)


# 4-5 ------------------------------------------------------------ ranking, plan, orders

def test_ranking(p):
    r = p["ranking"]
    assert [(g.rank, g.site, g.tier, g.high_risk) for g in r.ghats] == [
        (1, "Bairagarh (Sant Hirdaram) kund", 1, True), (2, "Malikhedi kund", 1, True),
        (3, "Khatlapura ghat", 2, False), (4, "Rani Kamlapati ghat / Kamla Park kund", 2, True),
        (5, "Shahpura lake ghat", 2, True), (6, "Prempura ghat", 2, True), (7, "Hathaikheda dam / kund", 3, False),
    ]


def test_actions_reconcile_with_orders(p):
    plan, orders = p["plan"], p["orders"]
    assert len(plan.actions) == 36
    on_orders = [t.action for o in orders for t in o.tasks]
    assert len(on_orders) == 36 == len(set(a.order for a in on_orders))
    assert sorted(on_orders, key=lambda a: a.order) == list(plan.actions)
    for o in orders:
        assert all(t.action.site == o.site for t in o.tasks)
    assert {o.site: len(o.tasks) for o in orders} == {
        "Bairagarh (Sant Hirdaram) kund": 6, "Malikhedi kund": 6, "Khatlapura ghat": 5,
        "Rani Kamlapati ghat / Kamla Park kund": 5, "Shahpura lake ghat": 4, "Prempura ghat": 6,
        "Hathaikheda dam / kund": 4,
    }
    # Each order's markdown lists each of its tasks once.
    for o, md in zip(orders, p["orders_md"]):
        rows = [l for l in md.splitlines() if re.match(r"^\| \d+ \|", l)]
        assert len(rows) == len(o.tasks)


# 6-7 ------------------------------------------------------------ guarantees and dates

def test_guarantees(p):
    for g, o in zip(p["ranking"].ghats, p["orders"]):
        if "DATA_GAP" in g.flag_codes:
            assert any(t.action.task_group == "Water sampling" and t.action.end < D for t in o.tasks)
        if "SITE_IDENTITY" in g.flag_codes:
            assert any(t.action.task_group == "Site identity check" for t in o.tasks)
    assert sum("DATA_GAP" in g.flag_codes for g in p["ranking"].ghats) == 4
    assert sum("SITE_IDENTITY" in g.flag_codes for g in p["ranking"].ghats) == 1


def test_dates(p):
    plan = p["plan"]
    assert (plan.event_date, plan.start, plan.end) == (D, date(2026, 10, 11), D7)
    windows = {(a.when, a.start, a.end) for a in plan.actions}
    expected = {
        ("D-9 to D-5", date(2026, 10, 11), date(2026, 10, 15)), ("D-7 to D-2", date(2026, 10, 13), date(2026, 10, 18)),
        ("D-5 to D", date(2026, 10, 15), D), ("D-3 to D+7", date(2026, 10, 17), D7),
        ("D-2 to D+2", date(2026, 10, 18), date(2026, 10, 22)), ("D to D+7", D, D7), ("D+7", D7, D7),
    }
    assert windows == expected
    assert all(o.target_sample_date == D7 and o.event_date == D for o in p["orders"])


# 8 ------------------------------------------------------------ never a pass

def test_missing_never_passes(p):
    ev = p["evidence"]
    bad = ev[(ev["value_state"] != "numeric") | (ev["contradictory"] == "yes")]
    assert set(bad["value_state"]) == {"bdl", "not_sampled", "no_table"}  # nd / unknown_flag absent in real data
    assert set(bad["class_b_result"]) <= {cr.UNASSESSABLE, cr.NO_CRITERION}
    assert set(bad["class_d_result"]) <= {cr.UNASSESSABLE, cr.NO_CRITERION}
    for state in ("bdl", "nd", "not_sampled", "no_table", "unknown_flag"):
        c = cr.compare_reading(p["table"], "B", "Dissolved oxygen", 9.0, state, "mg/l")
        assert c.status == cr.UNASSESSABLE
    assert cr.compare_reading(p["table"], "B", "Dissolved oxygen", 9.0, "numeric", "mg/l", contradictory=True).status \
        == cr.UNASSESSABLE


# 9 ------------------------------------------------------------ brief agrees with outputs

def test_brief_matches_outputs(p):
    en = p["briefs"]["en"]
    for g in p["ranking"].ghats:
        m = g.metrics
        line = next(l for l in en.splitlines() if l.startswith(f"{g.rank}. **{g.site}**"))
        assert f"Tier {g.tier}" in line and (", high risk" in line) == g.high_risk
        assert f"BOD >3 in {m.bod_fail}/{m.bod_usable}" in line
        if m.do_fail:
            assert f"DO <5 mg/l in {m.do_fail}/{m.do_usable}, lowest {m.do_min:g}" in line
        if m.ph_out:
            assert f"in {m.ph_out}/{m.ph_usable}" in line
    for a in p["plan"].actions:
        if a.start < D:
            assert pl.window_label(a.start, a.end) in en.split("## 3.")[1].split("## 4.")[0]
    assert "Durga visarjan, 20 Oct 2026" in en and "27 Oct 2026 sample" in en


# 10 ------------------------------------------------------------ evidence provenance

def test_evidence_provenance(p):
    ev, src = p["evidence"], p["data"].readings.set_index(list(load.KEY_COLUMNS))
    present = ev[ev["value_state"] != "no_table"]
    assert len(present) == 1524
    checked = present["page_verified"].str.startswith("spot-checked")
    assert checked.sum() == 12  # exactly the readings in verification/pdf_spot_checks.csv
    assert (present.loc[~checked, "page_verified"] == evm.PAGE_NOT_VERIFIED).all()
    assert present.loc[checked, "page_verified"].str.contains("partial manual check").all()
    joined = present.join(src[["source_page", "value_as_printed", "site_as_printed", "flag"]],
                          on=list(load.KEY_COLUMNS), rsuffix="_src")
    assert (joined["source_page"] == joined["source_page_src"]).all()
    assert (joined["value_as_printed"] == joined["value_as_printed_src"]).all()
    assert (joined["site_as_printed"] == joined["site_as_printed_src"]).all()
    assert (joined["source_flag"] == joined["flag"]).all()
    # Ranking/plan evidence references point at real source rows.
    for a in p["plan"].actions:
        for e in a.evidence:
            if e.source_page is not None:
                assert src.loc[(e.year, e.festival, a.site, e.phase, e.parameter), "source_page"] == e.source_page
    for md in p["orders_md"]:
        assert "not yet been checked against the report PDFs" in md
    assert "all other page references are not yet checked" in p["briefs"]["en"]


# 11-12 ------------------------------------------------------------ disclosures and warnings

def test_coliform_disclosed(p):
    targets = od.class_b_targets(p["table"])
    assert [(t.parameter, t.tested_in_data) for t in targets][-1] == ("Total coliform", False)
    for md in p["orders_md"]:
        assert "Total coliform ≤ 500 MPN/100 ml — not tested in the supplied data" in md
    assert "No total coliform readings" in p["briefs"]["en"]
    assert "टोटल कोलीफॉर्म की कोई रीडिंग नहीं" in p["briefs"]["hi"]


def test_warnings_and_sampling_assumption(p):
    assert all(not a.verified and a.warning == pl.UNVERIFIED_WARNING for a in p["plan"].actions)
    for o, md in zip(p["orders"], p["orders_md"]):
        assert md.count("⚠ " + pl.UNVERIFIED_WARNING) == len(o.tasks)
        sampling = [t for t in o.tasks if t.action.task_group == "Water sampling"]
        assert sampling and all(t.responsible == "MPPCB regional office, Bhopal" and t.responsible_is_assumption
                                for t in sampling)
        assert "MPPCB regional office, Bhopal *(assumed — confirm)*" in md
    for text in p["briefs"].values():
        assert pl.UNVERIFIED_WARNING in text


# 13 ------------------------------------------------------------ unassigned stays blank

def test_unassigned_blank(p):
    for o, md in zip(p["orders"], p["orders_md"]):
        assert o.zone_ward is None and "**Zone / ward:** ________" in md
        for t in o.tasks:
            if t.action.task_group != "Water sampling":
                assert t.responsible == od.ASSIGN_BLANK and not t.responsible_assigned


# 14-15 ------------------------------------------------------------ resources and Hindi status

def test_no_costs_and_hindi_provisional(p):
    for text in p["briefs"].values():
        assert not re.search(r"₹|\bRs\b|rupee|person-day|रुपये", text, re.I)
    assert "Not estimated" in p["briefs"]["en"] and "अनुमान नहीं लगाया गया" in p["briefs"]["hi"]
    assert br.HINDI_REVIEW_NOTICE in p["briefs"]["hi"]
    assert all(not t.action.hi_reviewed for o in p["orders"] for t in o.tasks)
    assert all(pl.PROVISIONAL_HINDI in md for md in p["orders_md"])


# 16 ------------------------------------------------------------ determinism

def test_deterministic(p):
    again = run_pipeline()
    assert again["csv"] == p["csv"]
    assert again["orders_md"] == p["orders_md"]
    assert again["briefs"] == p["briefs"]
    assert again["plan"] == p["plan"] and again["ranking"] == p["ranking"]
