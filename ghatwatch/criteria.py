"""Compare readings with CPCB water-quality criteria (Classes B and D).

Thresholds come only from data/cpcb_water_quality_criteria.csv. This module
holds no limit values of its own.

Class B (outdoor bathing, organised) is the bathing standard used by the tool.
Class D (wildlife and fisheries) is a separate ecological line and never stands
in for Class B.

Every comparison returns one of these statuses:
    pass          numeric reading meets the criterion (boundaries inclusive)
    fail          numeric reading does not meet the criterion
    unassessable  no usable number: BDL, ND, not sampled, no table, unresolved
                  flag, contradictory row, unit mismatch, or parameter not tested
    no_criterion  the requested class sets no limit for this parameter

Only `pass` means the criterion was met. `unassessable` is never a pass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ghatwatch import load

PASS = "pass"
FAIL = "fail"
UNASSESSABLE = "unassessable"
NO_CRITERION = "no_criterion"
STATUSES = (PASS, FAIL, UNASSESSABLE, NO_CRITERION)

SUPPORTED_CLASSES = ("B", "D")

# Criteria-file parameter name -> name used in the readings file.
# Names only; no limits here. [ASSUMPTION, PRD §3.3.7] data `BOD` is BOD (5 days 20C).
PARAMETER_ALIASES = {"BOD (5 days 20C)": "BOD"}

# Why a non-numeric value_state cannot be compared.
STATE_REASONS = {
    "bdl": "Below detection limit: very low, but the exact value is unknown, so it is not compared.",
    "nd": "Not detected: the exact value is unknown, so it is not compared.",
    "not_sampled": "Not sampled. Missing data is never treated as meeting the limit.",
    "no_table": "No table for this reading in the report. Missing data is never treated as meeting the limit.",
    "unknown_flag": "The report's mark for this reading has no documented meaning, so it is not compared.",
    "invalid_value": "The printed value is not a possible reading (e.g. negative), so it is not compared until resolved.",
}

# Class B checklist display order (PRD §7.1). Membership comes from the CSV.
CHECKLIST_ORDER = ("Dissolved oxygen", "BOD", "pH", "Total coliform")
COLIFORM = "Total coliform"

# Checklist outcomes. None of these is an operational clean-up status.
MEETS_ALL = "meets_all_class_b"
MEETS_MEASURED_COLIFORM_UNTESTED = "meets_measured_class_b_coliform_untested"
FAILS = "fails_class_b"
INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class Criterion:
    cls: str
    parameter: str  # name as used in the readings file
    parameter_in_criteria: str  # name as printed in the criteria CSV
    designated_best_use: str
    limit_type: str  # min | max | range
    low: float | None  # min, or lower end of range
    high: float | None  # max, or upper end of range
    limit_as_printed: str
    unit: str

    @property
    def limit_text(self) -> str:
        """Readable limit, e.g. 'min 5 mg/l' or 'range 6.5-8.5'."""
        return f"{self.limit_type} {self.limit_as_printed}{' ' + self.unit if self.unit else ''}"

    def check(self, value: float) -> str:
        """Return PASS or FAIL for a real number. Boundaries are inclusive."""
        if self.limit_type == "min":
            return PASS if value >= self.low else FAIL
        if self.limit_type == "max":
            return PASS if value <= self.high else FAIL
        return PASS if self.low <= value <= self.high else FAIL


@dataclass(frozen=True)
class Comparison:
    parameter: str
    value: float | None  # None unless value_state is numeric and the row is usable
    value_state: str
    unit: str
    cls: str
    limit_text: str | None  # None when no_criterion
    status: str
    reason: str


@dataclass(frozen=True)
class ClassBChecklist:
    site: str | None
    items: tuple[Comparison, ...]  # one per Class B criterion, in CHECKLIST_ORDER
    outcome: str
    explanation: str


CriteriaTable = dict[tuple[str, str], Criterion]  # (class, data parameter name) -> Criterion


# ------------------------------------------------------------ loading

def load_criteria_table(path: Path | str = load.DATA_DIR / load.CRITERIA_FILE) -> CriteriaTable:
    """Read and validate the criteria CSV, keyed by (class, readings-file parameter name)."""
    df = load.load_criteria(path)  # raises DataValidationError on bad input
    table: CriteriaTable = {}
    for row in df.to_dict("records"):
        limit, limit_type = row["limit"], row["limit_type"]
        if limit_type == "range":
            low, high = (float(p) for p in limit.split("-"))
        elif limit_type == "min":
            low, high = float(limit), None
        else:
            low, high = None, float(limit)
        parameter = PARAMETER_ALIASES.get(row["parameter"], row["parameter"])
        table[(row["class"], parameter)] = Criterion(
            cls=row["class"], parameter=parameter, parameter_in_criteria=row["parameter"],
            designated_best_use=row["designated_best_use"], limit_type=limit_type,
            low=low, high=high, limit_as_printed=limit, unit=row["unit"],
        )
    return table


class CriteriaDirectionError(ValueError):
    """The criteria file's limit direction conflicts with what a consumer assumes."""


def require_directions(table: CriteriaTable, required: dict[tuple[str, str], tuple[str, str]]) -> None:
    """Check each (class, parameter) has the expected limit_type (min | max | range).

    `required` maps (class, parameter) -> (expected limit_type, why it is needed).
    Only directions are checked; limit values stay whatever the CSV says.
    """
    for (cls, parameter), (expected, why) in required.items():
        criterion = table.get((cls, parameter))
        if criterion is None:
            raise CriteriaDirectionError(
                f"Class {cls} {parameter}: no criterion in {load.CRITERIA_FILE}, but one of type "
                f"'{expected}' is required ({why})."
            )
        if criterion.limit_type != expected:
            raise CriteriaDirectionError(
                f"Class {cls} {parameter} must be a '{expected}' criterion ({why}); "
                f"{load.CRITERIA_FILE} has '{criterion.limit_type}' ({criterion.limit_text})."
            )


def criteria_for_class(table: CriteriaTable, cls: str) -> list[Criterion]:
    _check_class(cls)
    return [c for (k, _), c in table.items() if k == cls]


def _check_class(cls: str) -> None:
    if cls not in SUPPORTED_CLASSES:
        raise ValueError(f"Class {cls!r} is not supported; use one of {', '.join(SUPPORTED_CLASSES)}")


# ------------------------------------------------------------ contradictions

def contradictory_keys(readings: pd.DataFrame, issues: list[load.DataIssue]) -> frozenset[tuple]:
    """Composite keys of source rows the loader reported as contradictory.

    `DataIssue.row` indexes `readings` (the source-file row); the grid has its
    own index, so the key is what links an issue to a grid cell.

    A blank cell with no flag is an issue (the flag is missing) but not a
    contradiction: the loader classifies it not_sampled per DATA_DICTIONARY,
    so it is excluded here. It still never passes, being non-numeric.
    """
    rows = [i.row for i in issues if i.row is not None]
    issue_rows = readings.loc[rows]
    missing_flag_only = (
        (issue_rows["flag"] == "") & issue_rows["value"].isna()
        & issue_rows["value_as_printed"].str.strip().isin(load.NOT_SAMPLED_PRINTS)
    )
    keys = issue_rows.loc[~missing_flag_only, list(load.KEY_COLUMNS)]
    return frozenset((int(y), *rest) for y, *rest in keys.itertuples(index=False, name=None))


# ------------------------------------------------------------ comparing

def compare_reading(
    table: CriteriaTable,
    cls: str,
    parameter: str,
    value: float | None,
    value_state: str,
    unit: str | None = None,
    contradictory: bool = False,
) -> Comparison:
    """Compare one reading with one class. See module docstring for statuses."""
    _check_class(cls)
    criterion = table.get((cls, parameter))
    unit = "" if unit is None or (isinstance(unit, float) and math.isnan(unit)) else unit

    def result(status: str, reason: str, usable_value: float | None = None) -> Comparison:
        return Comparison(
            parameter=parameter, value=usable_value, value_state=value_state,
            unit=unit or (criterion.unit if criterion else ""), cls=cls,
            limit_text=criterion.limit_text if criterion else None, status=status, reason=reason,
        )

    if criterion is None:
        return result(NO_CRITERION, f"CPCB Class {cls} sets no limit for {parameter}.")
    if contradictory:
        return result(UNASSESSABLE, "The source row has conflicting entries (see data-quality issues), so it is not compared.")
    if value_state != "numeric":
        reason = STATE_REASONS.get(value_state, f"Unrecognised value state {value_state!r}; not compared.")
        return result(UNASSESSABLE, reason)
    if value is None or pd.isna(value):
        return result(UNASSESSABLE, "Marked numeric but has no value; not compared.")
    if unit != criterion.unit:
        return result(UNASSESSABLE, f"Unit {unit or '(none)'!r} does not match the criterion unit {criterion.unit or '(none)'!r}.")

    status = criterion.check(float(value))
    verb = "meets" if status == PASS else "does not meet"
    return result(status, f"{parameter} {value:g} {verb} Class {cls} {criterion.limit_text}.", float(value))


def compare_frame(
    df: pd.DataFrame,
    table: CriteriaTable,
    cls: str,
    contradictory: frozenset[tuple] = frozenset(),
) -> pd.DataFrame:
    """Return a copy of a readings or grid frame with comparison columns added.

    Added columns: criterion_class, limit_text, result, result_reason.
    `contradictory` is the output of contradictory_keys().
    """
    out = df.copy()
    rows = [
        compare_reading(
            table, cls, r["parameter"], r["value"], r["value_state"], r["unit_assumed"],
            contradictory=(int(r["year"]), r["festival"], r["site"], r["phase"], r["parameter"]) in contradictory,
        )
        for _, r in df.iterrows()
    ]
    out["criterion_class"] = cls
    out["limit_text"] = [c.limit_text for c in rows]
    out["result"] = [c.status for c in rows]
    out["result_reason"] = [c.reason for c in rows]
    return out


# ------------------------------------------------------------ Class B checklist

def class_b_checklist(
    measurements: pd.DataFrame,
    table: CriteriaTable,
    contradictory: frozenset[tuple] = frozenset(),
) -> ClassBChecklist:
    """Class B checklist for ONE ghat and ONE sampling event (e.g. the D+7 sample).

    `measurements` has loader columns (parameter, value, value_state,
    unit_assumed, and the key columns). At most one row per parameter: pick
    the sample first, this function does not average or choose between rows.
    A Class B parameter with no row at all is reported as not tested.
    """
    site = None
    by_parameter: dict[str, pd.Series] = {}
    if not measurements.empty:
        if "site" in measurements:
            if measurements["site"].nunique() > 1:
                raise ValueError(f"Checklist needs one ghat; got {measurements['site'].nunique()} sites")
            site = measurements["site"].iloc[0]
        repeated = measurements["parameter"][measurements["parameter"].duplicated()].unique()
        if len(repeated):
            raise ValueError(f"Checklist needs one reading per parameter; repeated: {', '.join(repeated)}")
        by_parameter = {r["parameter"]: r for _, r in measurements.iterrows()}

    order = {p: i for i, p in enumerate(CHECKLIST_ORDER)}
    criteria = sorted(criteria_for_class(table, "B"), key=lambda c: order.get(c.parameter, len(order)))

    items = []
    for c in criteria:
        r = by_parameter.get(c.parameter)
        if r is None:
            items.append(Comparison(
                parameter=c.parameter, value=None, value_state="not_tested", unit=c.unit, cls="B",
                limit_text=c.limit_text, status=UNASSESSABLE,
                reason=f"{c.parameter} is not tested in the supplied data.",
            ))
            continue
        key = (int(r["year"]), r["festival"], r["site"], r["phase"], r["parameter"]) if "year" in r else None
        items.append(compare_reading(
            table, "B", c.parameter, r["value"], r["value_state"], r.get("unit_assumed"),
            contradictory=key in contradictory,
        ))

    outcome, explanation = _checklist_outcome(items)
    return ClassBChecklist(site=site, items=tuple(items), outcome=outcome, explanation=explanation)


def _checklist_outcome(items: list[Comparison]) -> tuple[str, str]:
    failed = [i.parameter for i in items if i.status == FAIL]
    missing = [i.parameter for i in items if i.status == UNASSESSABLE]
    if failed:
        text = f"Does not meet Class B: {', '.join(failed)} outside the limit."
        if missing:
            text += f" Not assessable: {', '.join(missing)}."
        return FAILS, text
    if not missing:
        return MEETS_ALL, "All Class B criteria met, including total coliform."
    if missing == [COLIFORM]:
        measured = ", ".join(i.parameter for i in items if i.status == PASS)
        return MEETS_MEASURED_COLIFORM_UNTESTED, (
            f"Measured Class B criteria met ({measured}). Total coliform not tested, "
            "so Class B is not confirmed."
        )
    return INSUFFICIENT_DATA, f"Cannot assess Class B: no usable reading for {', '.join(missing)}."
