"""Tests for ghatwatch.load: schema checks, value states, expected grid, summary."""

import hashlib
import math

import pandas as pd
import pytest

from ghatwatch import load
from ghatwatch.load import DataValidationError

READINGS = load.DATA_DIR / load.READINGS_FILE
CRITERIA = load.DATA_DIR / load.CRITERIA_FILE


@pytest.fixture(scope="module")
def data() -> load.LoadedData:
    return load.load_all()


def _raw(path=READINGS) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def _write(df: pd.DataFrame, tmp_path, name=load.READINGS_FILE):
    path = tmp_path / name
    df.to_csv(path, index=False, encoding="utf-8")
    return path


# ------------------------------------------------------------ real data

def test_real_data_counts(data):
    s = data.summary
    assert s.files == {load.READINGS_FILE: 1524, load.CRITERIA_FILE: 19}
    assert s.distinct == {"site": 7, "year": 3, "festival": 2, "phase": 3, "parameter": 13}
    assert s.duplicate_keys == 0
    assert s.expected_cells == 7 * 3 * 2 * 3 * 13 == 1638
    assert s.no_table_cells == 114
    assert s.value_state_counts == {
        "numeric": 1289, "bdl": 174, "nd": 0, "not_sampled": 61, "no_table": 114, "unknown_flag": 0,
        "invalid_value": 0,
    }
    assert s.issues == []


def test_numeric_do_and_bod_match_problem_statement(data):
    """Parsing check only: 42/116 DO < 5 and 100/112 BOD > 3 (no CPCB logic here)."""
    num = data.grid[data.grid["value_state"] == "numeric"]
    do = num[num["parameter"] == "Dissolved oxygen"]["value"]
    bod = num[num["parameter"] == "BOD"]["value"]
    assert (len(do), (do < 5).sum()) == (116, 42)
    assert (len(bod), (bod > 3).sum()) == (112, 100)


def test_four_zero_do_readings_are_numeric_at_bairagarh(data):
    zeros = data.grid[(data.grid["parameter"] == "Dissolved oxygen") & (data.grid["value"] == 0)]
    assert len(zeros) == 4
    assert set(zeros["value_state"]) == {"numeric"}
    assert set(zeros["site"]) == {"Bairagarh (Sant Hirdaram) kund"}


def test_no_table_cells_are_the_known_absent_tables(data):
    g = data.grid
    no_table = g[g["value_state"] == "no_table"]
    durga25_missing_sites = no_table[(no_table["year"] == 2025) & (no_table["festival"] == "Durga")
                                     & no_table["site"].isin(["Bairagarh (Sant Hirdaram) kund", "Malikhedi kund"])]
    assert len(durga25_missing_sites) == 2 * 3 * 13
    rest = no_table.drop(durga25_missing_sites.index)
    assert set(rest["parameter"]) == {"Suspended solids"}
    assert set(zip(rest["year"], rest["festival"])) == {(2023, "Durga"), (2025, "Durga")}
    # Nothing is invented for absent cells.
    assert no_table["source_page"].isna().all()
    assert no_table["value"].isna().all()
    assert no_table["site_as_printed"].isna().all()


def test_no_table_never_assigned_to_a_source_row(data):
    assert (data.readings["value_state"] != "no_table").all()
    from_source = data.grid[data.grid["source_page"].notna()]
    assert len(from_source) == 1524
    assert (from_source["value_state"] != "no_table").all()


def test_missing_markers_are_not_sampled_and_never_zero(data):
    r = data.readings
    for printed in ("_", "*", "**"):
        rows = r[r["value_as_printed"] == printed]
        assert len(rows) > 0
        assert set(rows["value_state"]) == {"not_sampled"}
        assert rows["value"].isna().all()


def test_bdl_is_not_zero(data):
    bdl = data.readings[data.readings["value_state"] == "bdl"]
    assert len(bdl) == 174
    assert bdl["value"].isna().all()
    assert set(bdl["value_as_printed"]) == {"BDL"}
    assert set(bdl["parameter"]) <= {"Chromium", "Lead", "Zinc", "Copper"}


def test_printed_text_preserved(data):
    raw = _raw()
    for col in ("value_as_printed", "parameter_as_printed", "site_as_printed", "flag", "unit_assumed"):
        assert data.readings[col].tolist() == raw[col].tolist()
    assert "µS/cm" in set(data.readings["unit_assumed"])


def test_source_files_not_modified():
    paths = [READINGS, CRITERIA, load.DATA_DIR / load.SAMPLE_FILE]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    load.load_all()
    load.load_all(readings_file=load.SAMPLE_FILE, years=(2025,))
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths] == before


def test_sample_file_matches_2025_rows(data):
    sample = load.load_all(readings_file=load.SAMPLE_FILE, years=(2025,))
    assert len(sample.readings) == 453
    full_2025 = data.readings[data.readings["year"] == 2025].reset_index(drop=True)
    pd.testing.assert_frame_equal(sample.readings, full_2025)
    assert sample.summary.expected_cells == 7 * 2 * 3 * 13


def test_sample_file_rejected_against_full_grid():
    with pytest.raises(DataValidationError, match="no rows at all for 2023, 2024"):
        load.load_all(readings_file=load.SAMPLE_FILE)


def test_summary_text_mentions_key_counts(data):
    text = data.summary.to_text()
    assert "1638" in text and "no_table" in text and "114" in text


# ------------------------------------------------------------ classify_measurement

@pytest.mark.parametrize(
    "value, flag, printed, state",
    [
        (0.0, "", "0", "numeric"),
        (2.5, "", "2.5", "numeric"),
        (math.nan, "BDL", "BDL", "bdl"),
        (math.nan, "ND", "ND", "nd"),
        (math.nan, "not sampled", "", "not_sampled"),
        (math.nan, "not sampled", "_", "not_sampled"),
        (math.nan, "not sampled", "-", "not_sampled"),
        (math.nan, "*", "*", "not_sampled"),
        (math.nan, "**", "**", "not_sampled"),
    ],
)
def test_classify_consistent_rows(value, flag, printed, state):
    assert load.classify_measurement(value, flag, printed) == (state, None)


@pytest.mark.parametrize(
    "value, flag, printed, state",
    [
        (math.nan, "NA", "NA", "unknown_flag"),          # flag not in the dictionary
        (math.nan, "bdl", "bdl", "unknown_flag"),        # no silent case-folding
        (0.0, "BDL", "BDL", "bdl"),                      # value and flag both set
        (math.nan, "", "", "not_sampled"),               # blank with no flag
        (math.nan, "", "n.d.", "unknown_flag"),          # text with no flag
        (5.0, "", "4.5", "unknown_flag"),                # value disagrees with print
    ],
)
def test_classify_contradictions_are_reported_and_never_numeric(value, flag, printed, state):
    got, problem = load.classify_measurement(value, flag, printed)
    assert got == state
    assert got != "numeric"
    assert problem


def test_contradictions_appear_in_summary(tmp_path):
    df = _raw()
    df.loc[0, "flag"] = "NA"
    df.loc[0, "value"] = ""
    path = _write(df, tmp_path)
    (tmp_path / load.CRITERIA_FILE).write_bytes(CRITERIA.read_bytes())
    result = load.load_all(tmp_path)
    assert result.summary.value_state_counts["unknown_flag"] == 1
    assert len(result.summary.issues) == 1
    assert result.summary.issues[0].row == 0
    assert path.exists()


# ------------------------------------------------------------ errors

def test_missing_file_raises(tmp_path):
    with pytest.raises(DataValidationError, match="file not found"):
        load.load_readings(tmp_path / "nope.csv")


def test_header_only_file_raises(tmp_path):
    path = _write(_raw().iloc[0:0], tmp_path)
    with pytest.raises(DataValidationError, match="no data rows"):
        load.load_readings(path)


def test_missing_column_raises(tmp_path):
    path = _write(_raw().drop(columns="source_page"), tmp_path)
    with pytest.raises(DataValidationError, match="source_page") as exc:
        load.load_readings(path)
    assert exc.value.source == load.READINGS_FILE


@pytest.mark.parametrize(
    "column, bad",
    [
        ("festival", "Diwali"),
        ("phase", "post"),
        ("parameter", "Dissolved Oxygen"),
        ("site", "Upper Lake ghat"),
        ("site_match_confidence", "low"),
        ("year", "2022"),
        ("year", "twenty"),
        ("value", "4.5 mg/l"),
        ("source_page", "p28"),
        ("site", ""),
    ],
)
def test_unexpected_values_raise_naming_column(tmp_path, column, bad):
    df = _raw()
    df.loc[5, column] = bad
    path = _write(df, tmp_path)
    with pytest.raises(DataValidationError) as exc:
        load.load_readings(path)
    assert exc.value.field_name == column
    assert exc.value.source == load.READINGS_FILE


def test_duplicate_key_rejected(tmp_path):
    df = _raw()
    df = pd.concat([df, df.iloc[[10]]], ignore_index=True)
    df.loc[len(df) - 1, "value"] = "99"
    df.loc[len(df) - 1, "value_as_printed"] = "99"
    path = _write(df, tmp_path)
    with pytest.raises(DataValidationError, match="Refusing to pick one"):
        load.load_readings(path)


def test_whole_site_missing_rejected(tmp_path):
    df = _raw()
    df = df[df["site"] != "Shahpura lake ghat"]
    path = _write(df, tmp_path)
    readings, _ = load.classify_value_states(load.load_readings(path))
    with pytest.raises(DataValidationError, match="Shahpura lake ghat"):
        load.build_expected_grid(readings)


@pytest.mark.parametrize(
    "column, bad",
    [("limit_type", "between"), ("class", "F"), ("limit", "five"), ("limit", "6.5")],
)
def test_bad_criteria_raise(tmp_path, column, bad):
    df = _raw(CRITERIA)
    df.loc[5, column] = bad  # row 5 is Class B pH, a range
    path = _write(df, tmp_path, load.CRITERIA_FILE)
    with pytest.raises(DataValidationError) as exc:
        load.load_criteria(path)
    assert exc.value.field_name == column


def test_criteria_missing_column_raises(tmp_path):
    path = _write(_raw(CRITERIA).drop(columns="limit_type"), tmp_path, load.CRITERIA_FILE)
    with pytest.raises(DataValidationError, match="limit_type"):
        load.load_criteria(path)
