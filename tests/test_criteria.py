"""Tests for ghatwatch.criteria: limits from CSV, boundaries, missing data, Class B checklist."""

import ast
import inspect
import math

import pandas as pd
import pytest

from ghatwatch import criteria as cr
from ghatwatch import load


@pytest.fixture(scope="module")
def table() -> cr.CriteriaTable:
    return cr.load_criteria_table()


@pytest.fixture(scope="module")
def data() -> load.LoadedData:
    return load.load_all()


UNITS = {"Dissolved oxygen": "mg/l", "BOD": "mg/l", "pH": ""}


def _cmp(table, cls, parameter, value, state="numeric", **kw):
    return cr.compare_reading(table, cls, parameter, value, state, UNITS.get(parameter, "mg/l"), **kw)


# ------------------------------------------------------------ boundaries

@pytest.mark.parametrize(
    "cls, parameter, value, expected",
    [
        ("B", "Dissolved oxygen", 4.99, cr.FAIL),
        ("B", "Dissolved oxygen", 5.00, cr.PASS),
        ("B", "Dissolved oxygen", 5.01, cr.PASS),
        ("D", "Dissolved oxygen", 3.99, cr.FAIL),
        ("D", "Dissolved oxygen", 4.00, cr.PASS),
        ("B", "BOD", 2.99, cr.PASS),
        ("B", "BOD", 3.00, cr.PASS),
        ("B", "BOD", 3.01, cr.FAIL),
        ("B", "pH", 6.49, cr.FAIL),
        ("B", "pH", 6.50, cr.PASS),
        ("B", "pH", 8.50, cr.PASS),
        ("B", "pH", 8.51, cr.FAIL),
        ("D", "pH", 6.49, cr.FAIL),
        ("D", "pH", 8.50, cr.PASS),
        ("B", "Dissolved oxygen", 0.0, cr.FAIL),  # zero is a real reading
    ],
)
def test_boundaries(table, cls, parameter, value, expected):
    c = _cmp(table, cls, parameter, value)
    assert c.status == expected
    assert c.value == value
    assert c.cls == cls


def test_class_b_and_d_loaded_from_csv(table):
    b = {c.parameter: (c.limit_type, c.low, c.high, c.unit) for c in cr.criteria_for_class(table, "B")}
    assert b == {
        "Total coliform": ("max", None, 500.0, "MPN/100 ml"),
        "pH": ("range", 6.5, 8.5, ""),
        "Dissolved oxygen": ("min", 5.0, None, "mg/l"),
        "BOD": ("max", None, 3.0, "mg/l"),
    }
    d = {c.parameter: (c.limit_type, c.low, c.high) for c in cr.criteria_for_class(table, "D")}
    assert d == {
        "pH": ("range", 6.5, 8.5),
        "Dissolved oxygen": ("min", 4.0, None),
        "Free ammonia (as N)": ("max", None, 1.2),
    }
    assert table[("B", "BOD")].parameter_in_criteria == "BOD (5 days 20C)"


def test_thresholds_follow_the_csv_not_constants(tmp_path):
    df = pd.read_csv(load.DATA_DIR / load.CRITERIA_FILE, dtype=str, keep_default_na=False)
    df.loc[(df["class"] == "B") & (df["parameter"] == "Dissolved oxygen"), "limit"] = "6"
    df.loc[(df["class"] == "B") & (df["parameter"] == "pH"), "limit"] = "7-8"
    path = tmp_path / load.CRITERIA_FILE
    df.to_csv(path, index=False)
    edited = cr.load_criteria_table(path)
    assert _cmp(edited, "B", "Dissolved oxygen", 5.5).status == cr.FAIL
    assert _cmp(edited, "B", "Dissolved oxygen", 6.0).status == cr.PASS
    assert _cmp(edited, "B", "pH", 6.9).status == cr.FAIL
    assert _cmp(edited, "B", "pH", 8.0).status == cr.PASS


def test_module_has_no_hidden_threshold_numbers():
    """criteria.py code holds no numeric literals beyond 0 and 1 (indexing, counts)."""
    tree = ast.parse(inspect.getsource(cr))
    numbers = {n.value for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
    assert numbers <= {0, 1}


def test_unsupported_class_rejected(table):
    with pytest.raises(ValueError, match="not supported"):
        _cmp(table, "A", "Dissolved oxygen", 7.0)


# ------------------------------------------------------------ missing and unresolved

@pytest.mark.parametrize("state", ["bdl", "nd", "not_sampled", "no_table", "unknown_flag", "something_new"])
@pytest.mark.parametrize("cls", ["B", "D"])
def test_non_numeric_states_never_pass(table, state, cls):
    # A plausible passing number is supplied on purpose: it must be ignored.
    c = _cmp(table, cls, "Dissolved oxygen", 7.0, state)
    assert c.status == cr.UNASSESSABLE
    assert c.value is None
    assert c.reason


@pytest.mark.parametrize("state", ["bdl", "nd"])
def test_bdl_and_nd_never_become_zero(table, state):
    # With BOD max 3, a zero would pass; BDL/ND must not.
    c = _cmp(table, "B", "BOD", math.nan, state)
    assert c.status == cr.UNASSESSABLE
    assert c.value is None


def test_numeric_state_with_no_value_is_unassessable(table):
    assert _cmp(table, "B", "BOD", math.nan).status == cr.UNASSESSABLE
    assert _cmp(table, "B", "BOD", None).status == cr.UNASSESSABLE


def test_contradictory_row_cannot_pass(table):
    c = _cmp(table, "B", "Dissolved oxygen", 7.0, contradictory=True)
    assert c.status == cr.UNASSESSABLE
    assert "conflicting" in c.reason


def test_unit_mismatch_is_unassessable(table):
    c = cr.compare_reading(table, "B", "Dissolved oxygen", 7.0, "numeric", "ppm")
    assert c.status == cr.UNASSESSABLE


@pytest.mark.parametrize("parameter", ["Lead", "COD", "Conductivity", "Turbidity"])
def test_no_criterion(table, parameter):
    c = _cmp(table, "B", parameter, 1.0)
    assert c.status == cr.NO_CRITERION
    assert c.limit_text is None


def test_bod_has_no_class_d_criterion(table):
    assert _cmp(table, "D", "BOD", 50.0).status == cr.NO_CRITERION


def test_contradictions_from_loader_flow_into_grid(tmp_path, table):
    """A loader-reported conflict (value + BDL flag) never passes, even in the grid."""
    raw = pd.read_csv(load.DATA_DIR / load.READINGS_FILE, dtype=str, keep_default_na=False, encoding="utf-8")
    do_row = raw.index[(raw["parameter"] == "Dissolved oxygen") & (raw["value"] == "7.4")][0]
    raw.loc[do_row, "flag"] = "BDL"  # value 7.4 kept: contradictory
    raw.to_csv(tmp_path / load.READINGS_FILE, index=False, encoding="utf-8")
    (tmp_path / load.CRITERIA_FILE).write_bytes((load.DATA_DIR / load.CRITERIA_FILE).read_bytes())

    data = load.load_all(tmp_path)
    assert [i.row for i in data.summary.issues] == [do_row]
    keys = cr.contradictory_keys(data.readings, data.summary.issues)
    out = cr.compare_frame(data.grid, table, "B", keys)
    r = raw.loc[do_row]
    cell = out[(out["year"] == int(r["year"])) & (out["festival"] == r["festival"]) & (out["site"] == r["site"])
               & (out["phase"] == r["phase"]) & (out["parameter"] == r["parameter"])]
    assert len(cell) == 1
    assert cell["result"].iloc[0] == cr.UNASSESSABLE
    assert "conflicting" in cell["result_reason"].iloc[0]


# ------------------------------------------------------------ real data

def test_real_grid_counts(data, table):
    keys = cr.contradictory_keys(data.readings, data.summary.issues)
    b = cr.compare_frame(data.grid, table, "B", keys)
    d = cr.compare_frame(data.grid, table, "D", keys)

    def counts(df, parameter):
        return df[df["parameter"] == parameter]["result"].value_counts().to_dict()

    assert counts(b, "Dissolved oxygen") == {cr.PASS: 74, cr.FAIL: 42, cr.UNASSESSABLE: 10}
    assert counts(b, "BOD") == {cr.FAIL: 100, cr.PASS: 12, cr.UNASSESSABLE: 14}
    assert counts(b, "pH")[cr.FAIL] == 6
    assert counts(b, "pH")[cr.PASS] == 109
    assert counts(d, "Dissolved oxygen")[cr.FAIL] == 17
    # Metals (incl. all BDL rows) and other parameters have no Class B limit.
    assert set(b[b["value_state"] == "bdl"]["result"]) == {cr.NO_CRITERION}
    # Every no_table / not_sampled cell is unassessable or has no criterion; never pass/fail.
    missing = b[b["value_state"].isin(["no_table", "not_sampled"])]
    assert set(missing["result"]) <= {cr.UNASSESSABLE, cr.NO_CRITERION}
    # The source frame is not modified.
    assert "result" not in data.grid.columns


# ------------------------------------------------------------ Class B checklist

def _sample(**readings) -> pd.DataFrame:
    """Rows for one ghat/event. Value is a number, or a value_state string."""
    names = {"do": "Dissolved oxygen", "bod": "BOD", "ph": "pH"}
    rows = []
    for key, v in readings.items():
        p = names[key]
        numeric = not isinstance(v, str)
        rows.append({
            "year": 2025, "festival": "Durga", "site": "Prempura ghat", "phase": "after",
            "parameter": p, "value": v if numeric else math.nan,
            "value_state": "numeric" if numeric else v, "unit_assumed": UNITS[p],
        })
    return pd.DataFrame(rows)


def test_checklist_measured_pass_coliform_untested(table):
    cl = cr.class_b_checklist(_sample(do=5.0, bod=3.0, ph=7.2), table)
    assert cl.outcome == cr.MEETS_MEASURED_COLIFORM_UNTESTED
    assert cl.outcome != cr.MEETS_ALL
    assert [i.parameter for i in cl.items] == ["Dissolved oxygen", "BOD", "pH", "Total coliform"]
    coliform = cl.items[-1]
    assert coliform.status == cr.UNASSESSABLE and coliform.value_state == "not_tested"
    assert "not confirmed" in cl.explanation
    assert "clean" not in cl.explanation.lower()
    assert cl.site == "Prempura ghat"


def test_checklist_fail(table):
    cl = cr.class_b_checklist(_sample(do=2.5, bod=8.0, ph=7.2), table)
    assert cl.outcome == cr.FAILS
    assert "Dissolved oxygen" in cl.explanation and "BOD" in cl.explanation


def test_checklist_fail_wins_over_missing(table):
    cl = cr.class_b_checklist(_sample(do=2.5, bod="not_sampled", ph=7.2), table)
    assert cl.outcome == cr.FAILS
    assert "Not assessable: BOD, Total coliform" in cl.explanation


@pytest.mark.parametrize(
    "readings",
    [
        {"do": 6.0, "bod": "not_sampled", "ph": 7.0},
        {"do": "no_table", "bod": 2.0, "ph": 7.0},
        {"do": 6.0, "bod": 2.0},  # pH row absent entirely
        {},
    ],
)
def test_checklist_insufficient_data(table, readings):
    cl = cr.class_b_checklist(_sample(**readings), table)
    assert cl.outcome == cr.INSUFFICIENT_DATA


def test_checklist_contradictory_row_blocks_pass(table):
    sample = _sample(do=6.0, bod=2.0, ph=7.0)
    key = (2025, "Durga", "Prempura ghat", "after", "BOD")
    cl = cr.class_b_checklist(sample, table, frozenset({key}))
    assert cl.outcome == cr.INSUFFICIENT_DATA


def test_checklist_all_met_only_with_coliform(table):
    sample = pd.concat([_sample(do=6.0, bod=2.0, ph=7.0), pd.DataFrame([{
        "year": 2025, "festival": "Durga", "site": "Prempura ghat", "phase": "after",
        "parameter": "Total coliform", "value": 120.0, "value_state": "numeric", "unit_assumed": "MPN/100 ml",
    }])], ignore_index=True)
    assert cr.class_b_checklist(sample, table).outcome == cr.MEETS_ALL


def test_checklist_rejects_ambiguous_input(table):
    two = pd.concat([_sample(do=6.0), _sample(do=4.0)], ignore_index=True)
    with pytest.raises(ValueError, match="one reading per parameter"):
        cr.class_b_checklist(two, table)
    mixed = _sample(do=6.0, bod=2.0)
    mixed.loc[1, "site"] = "Khatlapura ghat"
    with pytest.raises(ValueError, match="one ghat"):
        cr.class_b_checklist(mixed, table)


def test_checklist_on_real_sample(data, table):
    """Bairagarh, 2023 Durga during: DO 0 -> fails."""
    g = data.grid
    event = g[(g["site"] == "Bairagarh (Sant Hirdaram) kund") & (g["year"] == 2023)
              & (g["festival"] == "Durga") & (g["phase"] == "during")
              & g["parameter"].isin(["Dissolved oxygen", "BOD", "pH"])]
    cl = cr.class_b_checklist(event, table)
    assert cl.outcome == cr.FAILS
    assert cl.items[0].value == 0.0 and cl.items[0].status == cr.FAIL


def test_missing_flag_is_not_a_contradiction(tmp_path, table):
    """Audit fix: a blank cell with no flag is missing data, not a value/flag conflict."""
    raw = pd.read_csv(load.DATA_DIR / load.READINGS_FILE, dtype=str, keep_default_na=False, encoding="utf-8")
    blank = raw.index[(raw["flag"] == "not sampled") & (raw["value_as_printed"] == "")
                      & (raw["parameter"] == "BOD")][0]
    conflict = raw.index[(raw["parameter"] == "Dissolved oxygen") & (raw["value_as_printed"] == "7.4")][0]
    raw.loc[blank, "flag"] = ""          # missing flag only
    raw.loc[conflict, "flag"] = "BDL"    # value and flag: a real conflict
    raw.to_csv(tmp_path / load.READINGS_FILE, index=False, encoding="utf-8")
    (tmp_path / load.CRITERIA_FILE).write_bytes((load.DATA_DIR / load.CRITERIA_FILE).read_bytes())
    data = load.load_all(tmp_path)
    assert sorted(i.row for i in data.summary.issues) == sorted([blank, conflict])

    keys = cr.contradictory_keys(data.readings, data.summary.issues)
    key = lambda i: (int(raw.loc[i, "year"]), *raw.loc[i, ["festival", "site", "phase", "parameter"]])  # noqa: E731
    assert key(conflict) in keys
    assert key(blank) not in keys
    out = cr.compare_frame(data.grid, table, "B", keys)
    blank_cell = out[(out["year"] == key(blank)[0]) & (out["festival"] == key(blank)[1]) & (out["site"] == key(blank)[2])
                     & (out["phase"] == key(blank)[3]) & (out["parameter"] == "BOD")].iloc[0]
    assert blank_cell["result"] == cr.UNASSESSABLE
    assert "Not sampled" in blank_cell["result_reason"]
