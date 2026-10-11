"""Prompt 10 hardening: criteria-direction guard and per-reading page-verification status."""

import pandas as pd
import pytest

from ghatwatch import brief as br
from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import load
from ghatwatch import orders as od
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

BOD_CSV = "BOD (5 days 20C)"


def _table(tmp_path, cls, parameter, limit_type, limit):
    df = pd.read_csv(load.DATA_DIR / load.CRITERIA_FILE, dtype=str, keep_default_na=False)
    mask = (df["class"] == cls) & (df["parameter"] == parameter)
    assert mask.sum() == 1
    df.loc[mask, ["limit_type", "limit"]] = [limit_type, limit]
    path = tmp_path / load.CRITERIA_FILE
    df.to_csv(path, index=False)
    return cr.load_criteria_table(path)


# ------------------------------------------------------------ direction guard

def test_supplied_criteria_pass_the_guard():
    cr.require_directions(cr.load_criteria_table(), rk.REQUIRED_DIRECTIONS)
    assert rk.REQUIRED_DIRECTIONS.keys() == {("B", rk.DO), ("D", rk.DO), ("B", rk.BOD), ("B", rk.PH)}
    assert {k: v[0] for k, v in rk.REQUIRED_DIRECTIONS.items()} == {
        ("B", rk.DO): "min", ("D", rk.DO): "min", ("B", rk.BOD): "max", ("B", rk.PH): "range"}


@pytest.mark.parametrize(
    "cls, parameter, label, limit_type, limit, expected",
    [
        ("B", "Dissolved oxygen", "Dissolved oxygen", "max", "5", "min"),
        ("B", "Dissolved oxygen", "Dissolved oxygen", "range", "5-9", "min"),
        ("D", "Dissolved oxygen", "Dissolved oxygen", "max", "4", "min"),
        ("D", "Dissolved oxygen", "Dissolved oxygen", "range", "4-9", "min"),
        ("B", BOD_CSV, "BOD", "min", "3", "max"),
        ("B", BOD_CSV, "BOD", "range", "0-3", "max"),
        ("B", "pH", "pH", "min", "6.5", "range"),
        ("B", "pH", "pH", "max", "8.5", "range"),
    ],
)
def test_wrong_direction_is_refused(tmp_path, cls, parameter, label, limit_type, limit, expected):
    table = _table(tmp_path, cls, parameter, limit_type, limit)
    message = f"Class {cls} {label} must be a '{expected}' criterion"
    with pytest.raises(cr.CriteriaDirectionError, match=message) as exc:
        rk.rank_ghats(load.load_all(), table)
    assert f"has '{limit_type}'" in str(exc.value)
    assert load.CRITERIA_FILE in str(exc.value)


def test_missing_criterion_is_refused(tmp_path):
    df = pd.read_csv(load.DATA_DIR / load.CRITERIA_FILE, dtype=str, keep_default_na=False)
    df = df[~((df["class"] == "D") & (df["parameter"] == "Dissolved oxygen"))]
    path = tmp_path / load.CRITERIA_FILE
    df.to_csv(path, index=False)
    with pytest.raises(cr.CriteriaDirectionError, match="Class D Dissolved oxygen: no criterion .* type 'min'"):
        rk.rank_ghats(load.load_all(), cr.load_criteria_table(path))


def test_guard_also_protects_rank_grid_directly(tmp_path):
    table = _table(tmp_path, "B", BOD_CSV, "min", "3")
    with pytest.raises(cr.CriteriaDirectionError):
        rk.rank_grid(load.load_all().grid, table)


def test_value_changes_with_right_direction_are_allowed(tmp_path):
    """Only directions are guarded; limit values still come from the CSV."""
    table = _table(tmp_path, "B", "Dissolved oxygen", "min", "6")
    r = rk.rank_ghats(load.load_all(), table)
    assert len(r.ghats) == 7
    assert any("standard of 6 mg/l" in f.text_en for g in r.ghats for f in g.flags if f.code == "DO_OFTEN_LOW")


def test_require_directions_is_generic():
    table = cr.load_criteria_table()
    cr.require_directions(table, {("E", "Boron"): ("max", "test")})
    with pytest.raises(cr.CriteriaDirectionError, match="Class E Boron must be a 'min' criterion \\(why\\)"):
        cr.require_directions(table, {("E", "Boron"): ("min", "why")})


# ------------------------------------------------------------ page-verification status

@pytest.fixture(scope="module")
def data():
    return load.load_all()


def test_spot_check_record_is_partial_and_valid(data):
    checks = evm.load_spot_checks()
    assert len(checks) == 12 and len(checks[["year", "source_page"]].drop_duplicates()) == 8
    assert evm.SPOT_CHECK_SCOPE == "PARTIAL manual spot check"
    assert (checks["scope"] == evm.SPOT_CHECK_SCOPE).all()
    evm.validate_spot_checks(checks, data.readings)


def test_marking_is_per_reading_not_per_page(data):
    ev = evm.build_evidence(data)
    checked = ev[ev["page_verified"].str.startswith("spot-checked")]
    record = evm.spot_checked_keys(evm.load_spot_checks())
    assert {(r.year, r.festival, r.site, r.phase, r.parameter) for r in checked.itertuples()} == set(record)
    # Other readings printed on the same checked pages are NOT marked.
    same_pages = ev[ev.set_index(["year", "source_page"]).index.isin(list(zip(checked["year"], checked["source_page"])))]
    assert len(same_pages) > 200
    others = same_pages[~same_pages.index.isin(checked.index)]
    assert (others["page_verified"] == evm.PAGE_NOT_VERIFIED).all()
    assert "page 26" in checked.iloc[0]["page_verified"] and "2026-10-11" in checked.iloc[0]["page_verified"]
    assert (ev.loc[ev["value_state"] == "no_table", "page_verified"] == "").all()


@pytest.mark.parametrize(
    "column, value, message",
    [("source_page", "27", "disagree with the data"), ("value_as_printed", "0.1", "disagree with the data"),
     ("phase", "pre", "not a reading in the data|disagree"), ("scope", "full verification", "scope")],
)
def test_record_disagreeing_with_data_is_refused(tmp_path, data, column, value, message):
    df = pd.read_csv(evm.SPOT_CHECKS_FILE, dtype=str, keep_default_na=False)
    df.loc[0, column] = value
    path = tmp_path / "pdf_spot_checks.csv"
    df.to_csv(path, index=False)
    with pytest.raises(load.DataValidationError, match=message):
        evm.build_evidence(data, spot_checks=evm.load_spot_checks(path))


def test_without_record_nothing_is_marked(data):
    empty = evm.load_spot_checks().iloc[0:0]
    ev = evm.build_evidence(data, spot_checks=empty)
    present = ev[ev["value_state"] != "no_table"]
    assert (present["page_verified"] == evm.PAGE_NOT_VERIFIED).all()
    r = rk.rank_ghats(data)
    text = br.build_brief(r, pl.plan_actions(r), ev, generated_on="2026-10-11")
    assert "✓" not in text
    assert "Report pages come from the data file and have not been checked against the PDFs." in text


def test_work_orders_mark_only_checked_readings(data):
    r = rk.rank_ghats(data)
    p = pl.plan_actions(r)
    with_record = {o.site: o for o in od.work_orders(r, p, readings=data.readings)}
    bairagarh = od.to_markdown(with_record["Bairagarh (Sant Hirdaram) kund"])
    assert "✓ Matched to the PDF in the partial manual check: 2023 p.26 (Ganesh after, BOD 10)." in bairagarh
    assert "12 readings on 8 pages in all); all other page references have not yet been checked" in bairagarh
    # Hathaikheda: none of its readings was checked, so no ✓ line, but the general note stays.
    hathaikheda = od.to_markdown(with_record["Hathaikheda dam / kund"])
    assert "✓ Matched" not in hathaikheda and "partial manual spot check" in hathaikheda
    # Without readings the record cannot be validated: nothing is marked.
    plain = od.to_markdown(od.work_orders(r, p)[0])
    assert "✓" not in plain and "They have not yet been checked against the report PDFs." in plain


def test_no_output_claims_full_verification(data):
    r = rk.rank_ghats(data)
    p = pl.plan_actions(r)
    ev = evm.build_evidence(data)
    texts = [od.to_markdown(o) for o in od.work_orders(r, p, readings=data.readings)]
    texts += list(br.build_briefs(r, p, ev, generated_on="2026-10-11").values())
    texts.append(evm.evidence_csv_bytes(ev).decode("utf-8-sig"))
    joined = "\n".join(texts).lower()
    import re
    assert not re.search(r"(all|every)\s+(source\s+|report\s+)?pages?\s+(have been|were|are)\s+(checked|verified)", joined)
    assert "fully verified" not in joined
    assert "page_verified" in joined  # column present
