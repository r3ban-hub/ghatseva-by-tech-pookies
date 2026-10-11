"""Tests for ghatwatch.evidence: one row per cell, provenance, honest states, CSV."""

import pandas as pd
import pytest

from ghatwatch import criteria as cr
from ghatwatch import evidence as ev
from ghatwatch import load

RANI = "Rani Kamlapati ghat / Kamla Park kund"
UNASSESSED = {cr.UNASSESSABLE, cr.NO_CRITERION}


@pytest.fixture(scope="module")
def data():
    return load.load_all()


@pytest.fixture(scope="module")
def evidence(data):
    return ev.build_evidence(data)


def _copy_inputs(tmp_path, raw):
    raw.to_csv(tmp_path / load.READINGS_FILE, index=False, encoding="utf-8")
    (tmp_path / load.CRITERIA_FILE).write_bytes((load.DATA_DIR / load.CRITERIA_FILE).read_bytes())
    return load.load_all(tmp_path)


def _raw():
    return pd.read_csv(load.DATA_DIR / load.READINGS_FILE, dtype=str, keep_default_na=False, encoding="utf-8")


# ------------------------------------------------------------ shape and order

def test_one_row_per_grid_cell(evidence, data):
    assert len(evidence) == len(data.grid) == 1638
    assert tuple(evidence.columns) == ev.EVIDENCE_COLUMNS
    keys = evidence[list(load.KEY_COLUMNS)]
    assert not keys.duplicated().any()


def test_deterministic_order(evidence, data):
    rank = {c: {v: i for i, v in enumerate(vals)} for c, vals in
            {"festival": load.FESTIVALS, "site": load.SITES, "phase": load.PHASES, "parameter": load.PARAMETERS}.items()}
    keys = [(r.year, rank["festival"][r.festival], rank["site"][r.site], rank["phase"][r.phase],
             rank["parameter"][r.parameter]) for r in evidence.itertuples()]
    assert keys == sorted(keys)
    shuffled = load.LoadedData(data.readings, data.grid.sample(frac=1, random_state=3), data.criteria, data.summary)
    pd.testing.assert_frame_equal(ev.build_evidence(shuffled), evidence)


# ------------------------------------------------------------ provenance

def test_source_provenance(evidence):
    present = evidence[evidence["value_state"] != "no_table"]
    assert (present["source_page"] != "").all()
    checked = present["page_verified"].str.startswith("spot-checked")
    assert checked.sum() == 12  # exactly the readings in verification/pdf_spot_checks.csv
    assert (present.loc[~checked, "page_verified"] == ev.PAGE_NOT_VERIFIED).all()
    assert present.loc[checked, "page_verified"].str.contains("partial manual check").all()
    assert (present["site_as_printed"] != "").all()
    assert (evidence["data_file"] == load.READINGS_FILE).all()
    for year, (report, url) in ev.SOURCE_REPORTS.items():
        rows = evidence[evidence["year"] == year]
        assert (rows["source_report"] == report).all() and (rows["source_url"] == url).all()
        assert url.startswith("https://www.mppcb.mp.gov.in/")


def test_pages_and_print_match_source_rows(evidence, data):
    src = data.readings.set_index(list(load.KEY_COLUMNS))
    present = evidence[evidence["value_state"] != "no_table"]
    for r in present.itertuples():
        row = src.loc[(r.year, r.festival, r.site, r.phase, r.parameter)]
        assert r.source_page == row["source_page"]
        assert r.value_as_printed == row["value_as_printed"]
        assert r.site_as_printed == row["site_as_printed"]
        assert r.source_flag == row["flag"]


def test_no_table_rows_have_no_invented_fields(evidence):
    nt = evidence[evidence["value_state"] == "no_table"]
    assert len(nt) == 114
    for col in ("source_page", "page_verified", "value_as_printed", "value", "site_as_printed", "unit", "source_flag"):
        assert (nt[col] == "").all(), col


# ------------------------------------------------------------ states and results

def test_numeric_rows(evidence):
    num = evidence[evidence["value_state"] == "numeric"]
    assert len(num) == 1289
    assert (num["value"] != "").all()
    assert all(float(v) == float(p) for v, p in zip(num["value"], num["value_as_printed"]))
    zeros = num[(num["parameter"] == "Dissolved oxygen") & (num["value_as_printed"] == "0")]
    assert len(zeros) == 4 and (zeros["class_b_result"] == cr.FAIL).all() and (zeros["class_d_result"] == cr.FAIL).all()


def test_bdl_not_zero(evidence):
    bdl = evidence[evidence["value_state"] == "bdl"]
    assert len(bdl) == 174
    assert (bdl["value"] == "").all()
    assert (bdl["value_as_printed"] == "BDL").all() and (bdl["source_flag"] == "BDL").all()
    assert (bdl["class_b_result"] == cr.NO_CRITERION).all() and (bdl["class_b_limit"] == "").all()


def test_not_sampled_rows(evidence):
    ns = evidence[evidence["value_state"] == "not_sampled"]
    assert len(ns) == 61
    assert set(ns["value_as_printed"]) == {"", "_", "*", "**"}
    assert (ns["value"] == "").all()
    do = ns[ns["parameter"].isin(["Dissolved oxygen", "BOD", "pH"])]
    assert len(do) == 17 and (do["class_b_result"] == cr.UNASSESSABLE).all()


def test_missing_never_passes(evidence):
    not_usable = evidence[(evidence["value_state"] != "numeric") | (evidence["contradictory"] == "yes")]
    assert set(not_usable["class_b_result"]) <= UNASSESSED
    assert set(not_usable["class_d_result"]) <= UNASSESSED


def test_results_match_criteria_engine(evidence, data):
    table = cr.load_criteria_table()
    for cls, col in (("B", "class_b_result"), ("D", "class_d_result")):
        expected = cr.compare_frame(data.grid, table, cls)
        expected = {(int(r.year), r.festival, r.site, r.phase, r.parameter): r.result for r in expected.itertuples()}
        got = {(r.year, r.festival, r.site, r.phase, r.parameter): getattr(r, col) for r in evidence.itertuples()}
        assert got == expected
    b = evidence[evidence["class_b_result"].isin([cr.PASS, cr.FAIL])]
    assert dict(b.groupby(["parameter", "class_b_result"]).size()) == {
        ("BOD", "fail"): 100, ("BOD", "pass"): 12, ("Dissolved oxygen", "fail"): 42,
        ("Dissolved oxygen", "pass"): 74, ("pH", "fail"): 6, ("pH", "pass"): 109,
    }
    severe = evidence[(evidence["parameter"] == "Dissolved oxygen") & (evidence["class_d_result"] == cr.FAIL)]
    assert len(severe) == 17
    assert set(evidence.loc[evidence["parameter"] == "Dissolved oxygen", "class_d_limit"]) <= {"min 4 mg/l", ""}


def test_no_limit_invented(evidence):
    for p in ("COD", "Lead", "Conductivity", "Turbidity", "Suspended solids"):
        rows = evidence[evidence["parameter"] == p]
        assert (rows["class_b_limit"] == "").all() and (rows["class_b_result"] == cr.NO_CRITERION).all()


def test_unknown_flag_and_contradictory(tmp_path):
    raw = _raw()
    do = raw.index[(raw["parameter"] == "Dissolved oxygen") & (raw["value_as_printed"] == "7.4")]
    raw.loc[do[0], ["value", "flag", "value_as_printed"]] = ["", "NA", "NA"]       # unknown flag
    raw.loc[do[1], "flag"] = "BDL"                                                  # value + flag
    data = _copy_inputs(tmp_path, raw)
    out = ev.build_evidence(data)
    r0, r1 = raw.loc[do[0]], raw.loc[do[1]]

    def cell(r):
        return out[(out["year"] == int(r["year"])) & (out["festival"] == r["festival"]) & (out["site"] == r["site"])
                   & (out["phase"] == r["phase"]) & (out["parameter"] == r["parameter"])].iloc[0]

    unknown, conflict = cell(r0), cell(r1)
    assert unknown["value_state"] == "unknown_flag" and unknown["class_b_result"] == cr.UNASSESSABLE
    assert unknown["value_as_printed"] == "NA" and unknown["value"] == ""
    assert conflict["contradictory"] == "yes" and conflict["class_b_result"] == cr.UNASSESSABLE
    assert conflict["value"] == "" and conflict["value_as_printed"] == "7.4"
    assert "conflicting" in conflict["class_b_reason"]


# ------------------------------------------------------------ site identity

def test_site_identity_not_resolved(evidence):
    rani = evidence[evidence["site"] == RANI]
    assert len(rani) == 234
    assert (rani["site_identity_note"] == ev.SITE_IDENTITY_NOTE).all()  # including absent cells
    present = rani[rani["value_state"] != "no_table"]
    assert (present["site_match_confidence"] == "medium").all()
    printed = present.groupby("festival")["site_as_printed"].apply(set)
    assert any("kamla park" in n.lower() for n in printed["Ganesh"])
    assert any("lower lake" in n.lower() for n in printed["Durga"])
    assert (evidence.loc[evidence["site"] != RANI, "site_identity_note"] == "").all()


# ------------------------------------------------------------ CSV

def test_csv_round_trip(evidence, tmp_path):
    path = ev.write_evidence_csv(evidence, tmp_path / "evidence.csv")
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM for Excel
    assert b"\r\n" not in raw
    text = raw.decode("utf-8-sig")
    assert "µS/cm" in text and text.splitlines()[0] == ",".join(ev.EVIDENCE_COLUMNS)
    back = ev.read_evidence_csv(path)
    assert len(back) == 1638 and tuple(back.columns) == ev.EVIDENCE_COLUMNS
    as_text = evidence.astype(str).replace({"nan": ""})
    for col in ("year", "site", "site_as_printed", "value_as_printed", "value_state", "class_b_result",
                "source_page", "source_report", "site_identity_note"):
        assert back[col].tolist() == as_text[col].tolist(), col


def test_csv_bytes_deterministic(data):
    assert ev.evidence_csv_bytes(ev.build_evidence(data)) == ev.evidence_csv_bytes(ev.build_evidence(data))
