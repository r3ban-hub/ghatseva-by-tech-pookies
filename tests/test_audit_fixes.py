"""Regression tests for the independent audit findings (D1-D6, R3-R8) and the PDF spot-check record."""

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from ghatwatch import brief as br
from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import load
from ghatwatch import orders as od
from ghatwatch import plan as pl
from ghatwatch import ranking as rk



@pytest.fixture(scope="module")
def data():
    return load.load_all()


@pytest.fixture(scope="module")
def ranking(data):
    return rk.rank_ghats(data)


def _raw():
    return pd.read_csv(load.DATA_DIR / load.READINGS_FILE, dtype=str, keep_default_na=False, encoding="utf-8")


def _reload(df, tmp_path):
    df.to_csv(tmp_path / load.READINGS_FILE, index=False, encoding="utf-8")
    (tmp_path / load.CRITERIA_FILE).write_bytes((load.DATA_DIR / load.CRITERIA_FILE).read_bytes())
    return load.load_all(tmp_path)


def _key(df, i):
    r = df.loc[i]
    return (int(r["year"]), r["festival"], r["site"], r["phase"], r["parameter"])


# ------------------------------------------------------------ D1: window whitespace

@pytest.mark.parametrize("when", ["D-3 to D+7", "D-3\tto D+7", "D-3  to   D+7", "D-3 to\tD+7", "  D-3 to D+7  "])
def test_window_whitespace(when):
    assert pl.parse_window(when) == (-3, 7)


@pytest.mark.parametrize("when", ["D-3 to D", "D-3\tto\tD"])
def test_window_to_d(when):
    assert pl.parse_window(when) == (-3, 0)


@pytest.mark.parametrize("bad", ["D-3to D+7", "D-3 too D+7", "D-3 to", "D-3 - D+7", "D-3 to D+7 to D+9"])
def test_window_invalid_still_fails(bad):
    with pytest.raises(ValueError, match="window"):
        pl.parse_window(bad)


def test_window_tab_through_rules_csv(tmp_path):
    df = pd.read_csv(pl.RULES_FILE, dtype=str, keep_default_na=False, encoding="utf-8")
    df.loc[0, "when"] = "D-3\tto D+7"
    df.to_csv(tmp_path / "rules.csv", index=False, encoding="utf-8")
    rule = pl.load_action_rules(tmp_path / "rules.csv")[0]
    assert (rule.start_offset, rule.end_offset) == (-3, 7)


# ------------------------------------------------------------ D2: flag vs printed text

@pytest.mark.parametrize(
    "flag, printed, state",
    [("BDL", "BDL", "bdl"), ("ND", "ND", "nd"), ("not sampled", "", "not_sampled"), ("not sampled", "_", "not_sampled"),
     ("not sampled", "-", "not_sampled"), ("*", "*", "not_sampled"), ("**", "**", "not_sampled")],
)
def test_flag_with_matching_print_is_clean(flag, printed, state):
    assert load.classify_measurement(math.nan, flag, printed) == (state, None)


@pytest.mark.parametrize(
    "flag, printed, state",
    [("BDL", "0.5", "bdl"), ("BDL", "ND", "bdl"), ("ND", "BDL", "nd"), ("not sampled", "7.4", "not_sampled"),
     ("not sampled", "*", "not_sampled"), ("*", "**", "not_sampled"), ("**", "", "not_sampled"), ("*", "3.2", "not_sampled")],
)
def test_flag_with_inconsistent_print_is_reported(flag, printed, state):
    got, problem = load.classify_measurement(math.nan, flag, printed)
    assert got == state and got != "numeric"
    assert problem and "printed" in problem


def test_inconsistent_print_never_passes(tmp_path):
    df = _raw()
    i = df.index[(df["flag"] == "not sampled") & (df["parameter"] == "Dissolved oxygen")][0]
    df.loc[i, "value_as_printed"] = "7.4"
    data = _reload(df, tmp_path)
    assert [x.row for x in data.summary.issues] == [i]
    ev = evm.build_evidence(data)
    cell = ev.set_index(list(load.KEY_COLUMNS)).loc[_key(df, i)]
    assert cell["value_state"] == "not_sampled" and cell["class_b_result"] == cr.UNASSESSABLE
    assert cell["contradictory"] == "yes" and cell["value"] == ""


def test_real_data_has_no_flag_print_conflicts(data):
    assert data.summary.issues == []


# ------------------------------------------------------------ D3: merge with differing Hindi

def test_differing_hindi_is_not_dropped(ranking):
    rules = pl.load_action_rules()
    dup = replace(rules[2], rule_id="R99", triggers=("PH_OUT",), action_hi="ZZ अलग पाठ")
    with pytest.raises(pl.PlanError, match="different Hindi text"):
        pl.plan_actions(ranking, rules + (dup,))


def test_identical_hindi_still_merges(ranking):
    rules = pl.load_action_rules()
    dup = replace(rules[2], rule_id="R99", triggers=("PH_OUT",))
    tasks = [a for a in pl.plan_actions(ranking, rules + (dup,)).for_site("Hathaikheda dam / kund")
             if a.task_group == "Cleaning & debris"]
    assert len(tasks) == 1 and tasks[0].rule_ids == ("R3", "R99") and tasks[0].action_hi == rules[2].action_hi


# ------------------------------------------------------------ D4/D5: privacy heuristics

@pytest.mark.parametrize("text", ["Assigned 2026-10-11", "Zone 7 (rev. 12.10.2026)", "Revised 12/10/2026",
                                  "Ward 12, Zone 7", "Zone engineer (water works)"])
def test_dates_and_roles_not_flagged(text):
    assert od._privacy_problem(text) is None


@pytest.mark.parametrize("text", ["0000000000", "+00 00000 00000", "000-0000000", "Call 00-00-000000",
                                  "Revised 2026-10-11, call 0000000000"])
def test_phone_numbers_still_rejected(text):
    assert od._privacy_problem(text) == "looks like a phone number"


@pytest.mark.parametrize("text", ["Dr.Sharma", "Smt.Verma", "Dr. Sharma", "Shri R. Sharma", "mrs gupta"])
def test_honorific_forms_rejected(text):
    assert "person's name" in od._privacy_problem(text)


@pytest.mark.parametrize("text", ["Drainage engineer", "Zone sanitation in-charge", "Mrida ward office"])
def test_honorific_check_ignores_ordinary_words(text):
    assert od._privacy_problem(text) is None


def test_bare_names_are_a_documented_limitation():
    # Not detectable by the heuristic; the module docstring says so.
    assert od._privacy_problem("R. Sharma") is None
    assert "cannot be" in od.__doc__ and "R. Sharma" in od.__doc__


# ------------------------------------------------------------ D6: NumPy integer filters

def test_numpy_integer_year_filter(data, ranking):
    a = rk.rank_ghats(data, years=np.int64(2025))
    b = rk.rank_ghats(data, years=2025)
    assert a == b and a.years == (2025,)
    assert rk.rank_ghats(data, years=[np.int64(2024), np.int32(2025)]).years == (2024, 2025)
    assert rk.rank_ghats(data, festivals="Durga").festivals == ("Durga",)
    with pytest.raises(ValueError):
        rk.rank_ghats(data, years=np.int64(2022))


# ------------------------------------------------------------ R3: wording from limit_type

def _criterion(limit_type, limit, unit="mg/l"):
    low, high = (None, float(limit)) if limit_type == "max" else ((float(limit), None) if limit_type == "min" else (1.0, 2.0))
    return cr.Criterion("B", "X", "X", "", limit_type, low, high, limit, unit)


@pytest.mark.parametrize(
    "limit_type, limit, lang, kind, expected",
    [("min", "5", "en", "fail", "<5 mg/l"), ("min", "5", "en", "ok", "≥5 mg/l"), ("max", "3", "en", "fail", ">3 mg/l"),
     ("max", "3", "en", "ok", "≤3 mg/l"), ("range", "6.5-8.5", "en", "fail", "outside 6.5–8.5 mg/l"),
     ("max", "3", "en", "fail_words", "above 3 mg/l"), ("min", "3", "en", "fail_words", "below 3 mg/l"),
     ("min", "5", "hi", "fail", "5 mg/l से कम"), ("max", "3", "hi", "fail", "3 mg/l से अधिक"),
     ("min", "5", "hi", "ok", "5 mg/l या अधिक"), ("range", "6.5-8.5", "hi", "fail", "6.5–8.5 mg/l से बाहर")],
)
def test_compare_phrase_follows_limit_type(limit_type, limit, lang, kind, expected):
    assert br.compare_phrase(_criterion(limit_type, limit), lang, kind) == expected


def _criteria_with(tmp_path, cls, parameter, column, value):
    df = pd.read_csv(load.DATA_DIR / load.CRITERIA_FILE, dtype=str, keep_default_na=False)
    df.loc[(df["class"] == cls) & (df["parameter"] == parameter), column] = value
    path = tmp_path / load.CRITERIA_FILE
    df.to_csv(path, index=False)
    return cr.load_criteria_table(path)


def test_brief_wording_follows_csv_limit(tmp_path):
    """The brief's limit text comes from the CSV (BOD max 4 -> 'BOD >4'), not a constant."""
    table = _criteria_with(tmp_path, "B", "BOD (5 days 20C)", "limit", "4")
    data = load.load_all()
    ranking = rk.rank_ghats(data, table)
    text = br.build_brief(ranking, pl.plan_actions(ranking), evm.build_evidence(data, table), table, generated_on="2026-10-11")
    assert "BOD >4 in" in text and "BOD >3" not in text
    assert "BOD was above 4 mg/l in most readings" in text


def test_brief_cannot_be_built_on_reversed_bod(tmp_path):
    """A reversed BOD direction no longer reaches the brief: ranking refuses it first (Prompt 10 guard)."""
    table = _criteria_with(tmp_path, "B", "BOD (5 days 20C)", "limit_type", "min")
    with pytest.raises(cr.CriteriaDirectionError, match="Class B BOD must be a 'max' criterion"):
        rk.rank_ghats(load.load_all(), table)


# ------------------------------------------------------------ R4/R6: CSV export

@pytest.mark.parametrize(
    "value, expected",
    [("=1+2", "'=1+2"), ("+91", "'+91"), ("@SUM(A1)", "'@SUM(A1)"), ("-1+2", "'-1+2"), ("\tx", "'\tx"),
     ("-3", "-3"), ("-0.5", "-0.5"), ("-", "-"), ("", ""), ("BDL", "BDL"), (6.5, 6.5), (26, 26)],
)
def test_escape_formula(value, expected):
    assert evm.escape_formula(value) == expected


def test_export_escapes_only_in_file(data, tmp_path):
    ev = evm.build_evidence(data)
    poisoned = ev.copy()
    poisoned.loc[0, "site_as_printed"] = "=HYPERLINK(\"x\")"
    back = evm.read_evidence_csv(evm.write_evidence_csv(poisoned, tmp_path / "e.csv"))
    assert back.loc[0, "site_as_printed"] == "'=HYPERLINK(\"x\")"
    assert poisoned.loc[0, "site_as_printed"] == "=HYPERLINK(\"x\")"  # in-memory original kept
    # Real data has nothing to escape: export equals a plain to_csv.
    plain = ev[list(evm.EVIDENCE_COLUMNS)].to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
    assert evm.evidence_csv_bytes(ev) == plain


def test_no_table_rows_carry_source_note(data):
    ev = evm.build_evidence(data)
    nt = ev[ev["value_state"] == "no_table"]
    assert len(nt) == 114 and (nt["source_note"] == evm.NO_TABLE_NOTE).all()
    assert "not a citation" in evm.NO_TABLE_NOTE
    assert (ev.loc[ev["value_state"] != "no_table", "source_note"] == "").all()


# ------------------------------------------------------------ R7: impossible negative readings

def test_negative_reading_is_invalid_not_passing(tmp_path):
    df = _raw()
    i = df.index[(df["parameter"] == "BOD") & (df["value_as_printed"] == "2.4")][0]
    df.loc[i, ["value", "value_as_printed"]] = ["-3", "-3"]
    data = _reload(df, tmp_path)
    assert data.readings.loc[i, "value_state"] == "invalid_value"
    assert data.summary.value_state_counts["invalid_value"] == 1
    assert "negative" in data.summary.issues[0].problem
    # Even WITHOUT passing contradiction keys, -3 cannot pass "BOD max 3".
    out = cr.compare_frame(data.grid, cr.load_criteria_table(), "B")
    cell = out.set_index(list(load.KEY_COLUMNS)).loc[_key(df, i)]
    assert cell["result"] == cr.UNASSESSABLE and "not a possible reading" in cell["result_reason"]
    ev = evm.build_evidence(data).set_index(list(load.KEY_COLUMNS)).loc[_key(df, i)]
    assert ev["value"] == "" and ev["value_as_printed"] == "-3"  # printed text preserved, number not used
    g = next(g for g in rk.rank_ghats(data).ghats if g.site == df.loc[i, "site"])
    assert "DATA_GAP" in g.flag_codes


def test_zero_is_still_valid():
    assert load.classify_measurement(0.0, "", "0") == ("numeric", None)


# ------------------------------------------------------------ R8/R5: work-order citations and wording

def test_sources_added_only_when_text_lacks_pages(ranking):
    plan = pl.plan_actions(ranking)
    md = od.to_markdown(od.work_order("Bairagarh (Sant Hirdaram) kund", ranking, plan, od.load_assignments()))
    severe = next(l for l in md.splitlines() if l.startswith("- **DO_SEVERE:**"))
    bod = next(l for l in md.splitlines() if l.startswith("- **BOD_OFTEN_HIGH:**"))
    assert "Sources:" not in severe and "Sources:" in bod


def test_cites_all_pages_is_structured():
    ev = (rk.Evidence(2023, "Durga", "pre", "Dissolved oxygen", 0.0, "0", "numeric", 60, "x"),)
    flag = lambda text: rk.Flag("DO_SEVERE", "S", {}, text, ev)  # noqa: E731
    assert od._text_cites_all_pages(flag("Pages: 2023 p.60."))
    assert not od._text_cites_all_pages(flag("Pages: 2024 p.60."))   # wrong year
    assert not od._text_cites_all_pages(flag("Pages: 2023 p.6."))    # wrong page
    assert not od._text_cites_all_pages(flag("see p. 60 of the report"))  # " p." alone no longer counts


def test_data_gap_wording(ranking):
    plan = pl.plan_actions(ranking)
    orders = od.work_orders(ranking, plan)
    text = "\n".join(od.to_markdown(o) for o in orders)
    assert "Missing data is not counted as passing." in text
    assert "not treated as clean" not in text


# ------------------------------------------------------------ PDF spot-check record

def test_pdf_spot_checks_match_data(data):
    checks = pd.read_csv(evm.SPOT_CHECKS_FILE, dtype=str, keep_default_na=False)
    assert len(checks) == 12 and checks[["year", "source_page"]].drop_duplicates().shape[0] == 8
    assert (checks["scope"] == "PARTIAL manual spot check").all()
    src = data.readings.set_index(list(load.KEY_COLUMNS))
    for c in checks.itertuples():
        row = src.loc[(int(c.year), c.festival, c.site, c.phase, c.parameter)]
        assert row["value_as_printed"] == c.value_as_printed
        assert row["source_page"] == int(c.source_page)
        assert evm.SOURCE_REPORTS[int(c.year)][0] == c.report_file
