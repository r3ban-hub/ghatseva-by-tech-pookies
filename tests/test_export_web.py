"""Tests for ghatwatch.export_web: the JSON the web UI reads must equal the backend's outputs."""

import csv
import json

import pytest

from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import export_web as ex
from ghatwatch import load
from ghatwatch import plan as pl
from ghatwatch import ranking as rk


@pytest.fixture(scope="module")
def export():
    return json.loads(json.dumps(ex.build_export()))  # normalise exactly as the file is written


@pytest.fixture(scope="module")
def backend():
    data = load.load_all()
    ranking = rk.rank_ghats(data)
    return {"data": data, "ranking": ranking, "plan": pl.plan_actions(ranking), "evidence": evm.build_evidence(data)}


def test_committed_export_is_current(export):
    """web/lib/data/generated/backend.json must match a fresh export. Fix: python -m ghatwatch.export_web"""
    committed = json.loads(ex.DEFAULT_OUT.read_text(encoding="utf-8"))
    assert committed == export


def test_export_is_deterministic(export, tmp_path):
    assert json.loads(json.dumps(ex.build_export())) == export
    a = ex.write_export(tmp_path / "a.json").read_bytes()
    b = ex.write_export(tmp_path / "b.json").read_bytes()
    assert a == b and b"\r\n" not in a


def test_headlines(export):
    h = export["headlines"]
    assert (h["doBelow5"], h["doBelow4"], h["bodAbove3"], h["phOut"]) == (
        {"n": 42, "N": 116}, {"n": 17, "N": 116}, {"n": 100, "N": 112}, {"n": 6, "N": 115})
    assert (h["durgaDoBelow5"], h["durgaBodAbove3"]) == ({"n": 25, "N": 57}, {"n": 50, "N": 53})
    assert h["highRisk"] == {"n": 5, "N": 7} and h["preBodAbove3"] == {"n": 32, "N": 37}
    assert h["doZero"]["count"] == 4 and h["doZero"]["sites"] == ["Bairagarh (Sant Hirdaram) kund"]
    assert [(r["year"], r["page"], r["verified"]) for r in h["doZero"]["refs"]] == [
        (2023, 26, True), (2023, 60, True), (2025, 28, True)]


def test_sites_equal_ranking(export, backend):
    sites = export["sites"]
    assert [s["csvSiteName"] for s in sites] == [g.site for g in backend["ranking"].ghats]
    for s, g in zip(sites, backend["ranking"].ghats):
        m = g.metrics
        assert (s["rank"], s["tier"], s["highRisk"], s["flags"]) == (g.rank, g.tier, g.high_risk, list(g.flag_codes))
        assert s["doBelow5"] == {"n": m.do_fail, "N": m.do_usable} and s["doBelow4"] == m.do_severe
        assert s["bodAbove3"] == {"n": m.bod_fail, "N": m.bod_usable}
        assert s["phOutOfRange"] == {"n": m.ph_out, "N": m.ph_usable}
        assert s["doZeroCount"] == m.do_zero and s["doMin"] == f"{m.do_min:g}"
        assert [n["flag"] for n in s["notes"]] == list(g.flag_codes)
        for note, flag in zip(s["notes"], g.flags):
            assert note["en"] == flag.text_en
            assert any("ऀ" <= ch <= "ॿ" for ch in note["hi"])


def test_page_refs_verified_only_when_every_cited_reading_was_checked(export, backend):
    checked = set(evm.spot_checked_keys(evm.load_spot_checks()))
    for s, g in zip(export["sites"], backend["ranking"].ghats):
        for note, flag in zip(s["notes"], g.flags):
            for ref in note["refs"]:
                cited = [e for e in flag.evidence if (e.year, e.source_page) == (ref["year"], ref["page"])]
                assert cited
                assert ref["verified"] == all((e.year, e.festival, g.site, e.phase, e.parameter) in checked for e in cited)
    verified = [r for s in export["sites"] for n in s["notes"] for r in n["refs"] if r["verified"]]
    assert verified  # the DO = 0 pages are fully covered by the spot check
    assert not any(r["verified"] for r in export["sites"][0]["notes"][-1]["refs"])  # DATA_GAP pages: not checked


def test_actions_equal_plan(export, backend):
    actions = export["actions"]
    plan = backend["plan"]
    assert len(actions) == len(plan.actions) == 36
    for a, p in zip(actions, plan.actions):
        assert (a["order"], a["site"], a["ruleIds"], a["triggers"]) == (p.order, p.site, list(p.rule_ids), list(p.triggers))
        assert (a["start"], a["end"], a["en"], a["hi"]) == (p.start.isoformat(), p.end.isoformat(), p.action_en, p.action_hi)
        assert a["warning"] == pl.UNVERIFIED_WARNING and a["verified"] is False
        assert a["taskGroup"] in {"cleaning", "aeration", "barricading", "sampling", "identity"}
    assert {a["id"] for a in actions if a["trigger"] == "ALL"} == {"rule-r7", "rule-r8"}


def test_cells_cover_the_grid_and_point_at_csv_lines(export, backend):
    cells = export["cells"]
    assert len(cells) == 1638
    states = {}
    for c in cells:
        states[c["state"]] = states.get(c["state"], 0) + 1
    assert states == {"numeric": 1289, "bdl": 174, "not_sampled": 61, "no_table": 114}
    with open(load.DATA_DIR / load.READINGS_FILE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for c in cells:
        if "reading" in c:
            src = rows[c["reading"]["csvLine"] - 2]
            assert (src["year"], src["festival"], src["site"], src["phase"], src["parameter"]) == (
                str(c["year"]), c["festival"], c["site"], c["phase"], c["parameter"])
            assert src["value_as_printed"] == c["reading"]["valueAsPrinted"]


def test_missing_reasons(export):
    no_table = [c for c in export["cells"] if c["state"] == "no_table"]
    whole = [c for c in no_table if c["missingReason"] == "season_table_absent"]
    partial = [c for c in no_table if c["missingReason"] == "parameter_absent"]
    assert len(whole) == 78 and {(c["site"], c["year"], c["festival"]) for c in whole} == {
        ("Bairagarh (Sant Hirdaram) kund", 2025, "Durga"), ("Malikhedi kund", 2025, "Durga")}
    assert len(partial) == 36 and {c["parameter"] for c in partial} == {"Suspended solids"}
    assert all("reading" not in c for c in no_table)


def test_spot_checks_marked_per_reading(export):
    marked = {(c["year"], c["festival"], c["site"], c["phase"], c["parameter"])
              for c in export["cells"] if c.get("reading", {}).get("spotChecked")}
    assert marked == set(evm.spot_checked_keys(evm.load_spot_checks()))
    assert export["meta"]["spotCheck"] == {"readings": 12, "pages": 8, "checkedOn": ["2026-10-11"]}


def test_dates_and_targets(export):
    meta = export["meta"]
    assert (meta["visarjanDate"], meta["planStart"], meta["d7Date"]) == ("2026-10-20", "2026-10-11", "2026-10-27")
    assert [w["datesEn"] for w in export["planWindows"]] == [
        "11–13 Oct", "14–17 Oct", "18–19 Oct", "20 Oct", "21–22 Oct", "23–26 Oct", "27 Oct"]
    assert [(t["parameter"], t["inCurrentData"]) for t in export["targets"]] == [
        ("Dissolved oxygen", True), ("BOD", True), ("pH", True), ("Total coliform", False)]
    assert export["meta"]["coliform"]["en"] == "500 MPN/100 ml or less"


def test_no_cost_or_rate_figures(export):
    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k
                yield from keys(v)
        elif isinstance(o, list):
            for v in o:
                yield from keys(v)
    banned = {"cost", "rate", "rates", "rupees", "inr", "personDays", "illustrative", "low", "high"}
    assert not banned & set(keys(export))
    text = json.dumps(export, ensure_ascii=False)
    assert "₹" not in text and "rupee" not in text.lower()


def test_every_site_has_a_ui_label(export):
    """The UI throws at build time for an unlabelled site; catch it here first."""
    static_ts = (ex.ROOT / "web" / "lib" / "data" / "static.ts").read_text(encoding="utf-8")
    for s in export["sites"]:
        assert f'"{s["csvSiteName"]}": {{ siteId:' in static_ts


def test_unknown_flag_has_no_silent_hindi():
    flag = rk.Flag("NEW_FLAG", "S", {}, "text", ())
    with pytest.raises(ValueError, match="no Hindi wording"):
        ex._note_hi(flag, cr.load_criteria_table())
