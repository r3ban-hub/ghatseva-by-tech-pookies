"""Load and validate the Track 2 data files, classify every reading, and build
the expected measurement grid.

This module only answers "what does the data say, and what is missing?".
It does not compare readings with CPCB limits (see criteria.py, later).

Rules followed here come from data/DATA_DICTIONARY.md:
- A blank `value` with a flag explains *why* there is no number.
- BDL is "below detection limit": not zero, not missing.
- `not sampled`, `*` and `**` are missing. Missing is never clean.
- A cell in the expected grid with no row in the file is `no_table`.

Usage:
    python -m ghatwatch.load            # print the validation summary
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
READINGS_FILE = "bhopal_ghats_2023_2025.csv"
SAMPLE_FILE = "sample_bhopal_2025.csv"
CRITERIA_FILE = "cpcb_water_quality_criteria.csv"

READINGS_COLUMNS = (
    "year", "festival", "site", "water_body", "phase", "parameter", "value",
    "unit_assumed", "flag", "value_as_printed", "parameter_as_printed",
    "site_as_printed", "site_match_confidence", "source_page",
)
CRITERIA_COLUMNS = ("class", "designated_best_use", "parameter", "limit_type", "limit", "unit")

# Composite key: one reading per (year, festival, site, phase, parameter).
KEY_COLUMNS = ("year", "festival", "site", "phase", "parameter")

# Expected values, from DATA_DICTIONARY.md. Order here is display order.
YEARS = (2023, 2024, 2025)
FESTIVALS = ("Ganesh", "Durga")
PHASES = ("pre", "during", "after")
SITES = (
    "Bairagarh (Sant Hirdaram) kund",
    "Khatlapura ghat",
    "Prempura ghat",
    "Rani Kamlapati ghat / Kamla Park kund",
    "Hathaikheda dam / kund",
    "Malikhedi kund",
    "Shahpura lake ghat",
)
PARAMETERS = (
    "pH", "Dissolved oxygen", "BOD", "COD", "Total solids", "Dissolved solids",
    "Suspended solids", "Turbidity", "Conductivity",
    "Chromium", "Lead", "Zinc", "Copper",
)
SITE_MATCH_CONFIDENCES = ("high", "medium")
CRITERIA_CLASSES = ("A", "B", "C", "D", "E")
LIMIT_TYPES = ("min", "max", "range")

# Flag -> value_state. Any other non-empty flag becomes `unknown_flag`.
FLAG_STATES = {
    "BDL": "bdl",
    "ND": "nd",
    "not sampled": "not_sampled",
    "*": "not_sampled",
    "**": "not_sampled",
}
# How the dictionary says a "not sampled" cell can be printed.
NOT_SAMPLED_PRINTS = ("", "_", "-")
# Printed text consistent with each flag (DATA_DICTIONARY "Codes you will see").
FLAG_PRINTS = {
    "BDL": ("BDL",),
    "ND": ("ND",),
    "not sampled": NOT_SAMPLED_PRINTS,
    "*": ("*",),
    "**": ("**",),
}

VALUE_STATES = ("numeric", "bdl", "nd", "not_sampled", "no_table", "unknown_flag", "invalid_value")


class DataValidationError(ValueError):
    """A source file is missing, unreadable or does not match the data dictionary."""

    def __init__(self, source: str, field_name: str | None, problem: str):
        self.source = source
        self.field_name = field_name
        self.problem = problem
        where = f"{source}, column '{field_name}'" if field_name else source
        super().__init__(f"{where}: {problem}")


@dataclass
class DataIssue:
    """A row-level data-quality problem that does not stop loading."""

    source: str
    row: int | None  # 0-based data row in the source file (header excluded)
    field: str
    problem: str


@dataclass
class ValidationSummary:
    files: dict[str, int]  # filename -> data row count
    columns_checked: dict[str, tuple[str, ...]]  # filename -> required columns, all present
    distinct: dict[str, int]  # key column -> number of distinct values
    duplicate_keys: int
    expected_cells: int
    value_state_counts: dict[str, int]  # over the expected grid
    no_table_cells: int
    issues: list[DataIssue] = field(default_factory=list)

    def to_text(self) -> str:
        lines = ["Data validation summary"]
        for name, rows in self.files.items():
            lines.append(f"  {name}: {rows} rows, {len(self.columns_checked[name])} required columns present")
        lines.append("  Distinct: " + ", ".join(f"{k} {v}" for k, v in self.distinct.items()))
        lines.append(f"  Duplicate keys: {self.duplicate_keys}")
        lines.append(f"  Expected grid cells: {self.expected_cells}")
        lines.append("  Value states: " + ", ".join(f"{k} {v}" for k, v in self.value_state_counts.items()))
        lines.append(f"  Cells with no row in the report (no_table): {self.no_table_cells}")
        lines.append(f"  Unresolved data-quality issues: {len(self.issues)}")
        lines.extend(f"    - {i.source} row {i.row}, {i.field}: {i.problem}" for i in self.issues)
        return "\n".join(lines)


@dataclass
class LoadedData:
    readings: pd.DataFrame  # source rows + value_state
    grid: pd.DataFrame  # every expected cell, including no_table
    criteria: pd.DataFrame
    summary: ValidationSummary


# ---------------------------------------------------------------- reading files

def read_csv_strict(path: Path | str) -> pd.DataFrame:
    """Read a CSV with every cell as text, so nothing is coerced or guessed.

    Empty cells stay "" (not NaN), and "NA"/"ND"-like strings are not turned
    into missing values by pandas.
    """
    path = Path(path)
    if not path.is_file():
        raise DataValidationError(path.name, None, f"file not found at {path}")
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DataValidationError(path.name, None, f"could not be read as UTF-8 CSV ({exc})") from exc
    if df.empty:
        raise DataValidationError(path.name, None, "has a header but no data rows")
    return df


def validate_columns(df: pd.DataFrame, required: tuple[str, ...], source: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataValidationError(source, missing[0], f"required column(s) missing: {', '.join(missing)}")


def validate_allowed_values(df: pd.DataFrame, column: str, allowed: tuple, source: str) -> None:
    bad = df.loc[~df[column].isin(allowed), column]
    if not bad.empty:
        examples = ", ".join(repr(v) for v in bad.unique()[:5])
        raise DataValidationError(
            source, column,
            f"{len(bad)} row(s) hold unexpected value(s) {examples}; "
            f"expected one of {', '.join(map(str, allowed))} (first bad row {bad.index[0]})",
        )


def _parse_numbers(df: pd.DataFrame, column: str, source: str, *, integer: bool) -> pd.Series:
    """Parse a text column to numbers. Blank stays missing; any other text is an error."""
    text = df[column]
    parsed = pd.to_numeric(text.where(text != ""), errors="coerce")
    bad = text[(text != "") & parsed.isna()]
    if integer:
        bad = pd.concat([bad, text[parsed.notna() & (parsed % 1 != 0)]])
    if not bad.empty:
        raise DataValidationError(
            source, column,
            f"{len(bad)} row(s) are not {'whole numbers' if integer else 'numbers'}, "
            f"e.g. {bad.iloc[0]!r} (row {bad.index[0]})",
        )
    return parsed.astype("Int64") if integer else parsed.astype(float)


def find_duplicate_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Return every row whose composite key appears more than once."""
    return df[df.duplicated(list(KEY_COLUMNS), keep=False)]


def load_readings(path: Path | str = DATA_DIR / READINGS_FILE) -> pd.DataFrame:
    """Load an immersion-readings CSV (Bhopal file or the 2025 sample) and validate it.

    Returns the source columns with `year`, `value` and `source_page` parsed to
    numbers (blank -> missing, never 0). All printed-text columns are untouched.
    Raises DataValidationError on any schema problem or duplicate key.
    """
    path = Path(path)
    source = path.name
    df = read_csv_strict(path)
    validate_columns(df, READINGS_COLUMNS, source)

    for column in ("festival", "site", "phase", "parameter", "site_as_printed", "water_body"):
        empty = df[df[column] == ""]
        if not empty.empty:
            raise DataValidationError(source, column, f"{len(empty)} row(s) are blank (first bad row {empty.index[0]})")
    validate_allowed_values(df, "festival", FESTIVALS, source)
    validate_allowed_values(df, "phase", PHASES, source)
    validate_allowed_values(df, "parameter", PARAMETERS, source)
    validate_allowed_values(df, "site", SITES, source)
    validate_allowed_values(df, "site_match_confidence", SITE_MATCH_CONFIDENCES, source)

    df["year"] = _parse_numbers(df, "year", source, integer=True)
    if df["year"].isna().any():
        raise DataValidationError(source, "year", "blank year")
    validate_allowed_values(df, "year", YEARS, source)
    df["value"] = _parse_numbers(df, "value", source, integer=False)
    df["source_page"] = _parse_numbers(df, "source_page", source, integer=True)

    dups = find_duplicate_keys(df)
    if not dups.empty:
        first = dups.iloc[0]
        raise DataValidationError(
            source, None,
            f"{len(dups)} rows share a (year, festival, site, phase, parameter) key, e.g. "
            f"{first['year']} {first['festival']} {first['site']} {first['phase']} {first['parameter']} "
            f"(rows {', '.join(map(str, dups.index[:4]))}). Refusing to pick one.",
        )
    return df


def load_criteria(path: Path | str = DATA_DIR / CRITERIA_FILE) -> pd.DataFrame:
    """Load the CPCB criteria CSV and check every limit is parseable.

    Limits are left as printed ("5", "6.5-8.5"); interpreting them is criteria.py's job.
    """
    path = Path(path)
    source = path.name
    df = read_csv_strict(path)
    validate_columns(df, CRITERIA_COLUMNS, source)
    validate_allowed_values(df, "class", CRITERIA_CLASSES, source)
    validate_allowed_values(df, "limit_type", LIMIT_TYPES, source)

    for i, row in df.iterrows():
        if row["parameter"] == "":
            raise DataValidationError(source, "parameter", f"blank parameter (row {i})")
        parts = row["limit"].split("-") if row["limit_type"] == "range" else [row["limit"]]
        if len(parts) != (2 if row["limit_type"] == "range" else 1) or not all(_is_number(p) for p in parts):
            raise DataValidationError(
                source, "limit",
                f"row {i} ({row['class']} {row['parameter']}): {row['limit']!r} is not a valid "
                f"{row['limit_type']} limit",
            )

    dups = df[df.duplicated(["class", "parameter"], keep=False)]
    if not dups.empty:
        raise DataValidationError(source, "parameter", f"class/parameter repeated: {dups.iloc[0]['class']} {dups.iloc[0]['parameter']}")
    return df


def _is_number(text: str) -> bool:
    try:
        return math.isfinite(float(text))
    except ValueError:
        return False


# ------------------------------------------------------------ value states

def classify_measurement(value: float, flag: str, value_as_printed: str) -> tuple[str, str | None]:
    """Return (value_state, problem) for one source row.

    `problem` is None for a consistent row, otherwise a sentence describing the
    contradiction. Contradictory rows are never classified as `numeric`, so they
    can never count as a pass downstream.

    A negative number is `invalid_value`: none of the 13 parameters (pH
    included) can be below zero. No other plausibility limit is applied.
    """
    has_value = not pd.isna(value)

    if flag == "":
        if not has_value:
            if value_as_printed.strip() in NOT_SAMPLED_PRINTS:
                return "not_sampled", (
                    f"no value and no flag; printed as {value_as_printed!r}, "
                    "treated as not sampled per DATA_DICTIONARY"
                )
            return "unknown_flag", f"no value and no flag; printed as {value_as_printed!r}"
        if not _is_number(value_as_printed) or float(value_as_printed) != value:
            return "unknown_flag", f"value {value} does not match printed {value_as_printed!r}"
        if value < 0:
            return "invalid_value", f"negative value {value:g} is not a possible reading; not used until resolved"
        return "numeric", None

    state = FLAG_STATES.get(flag, "unknown_flag")
    if has_value:
        return state, f"has both value {value} and flag {flag!r}; value not used"
    if state == "unknown_flag":
        return state, f"flag {flag!r} is not defined in DATA_DICTIONARY"
    if value_as_printed.strip() not in FLAG_PRINTS[flag]:
        expected = " or ".join(repr(p) for p in FLAG_PRINTS[flag])
        return state, f"flag {flag!r} but printed {value_as_printed!r} (expected {expected}); printed text not used"
    return state, None


def classify_value_states(readings: pd.DataFrame, source: str = READINGS_FILE) -> tuple[pd.DataFrame, list[DataIssue]]:
    """Return a copy of `readings` with a `value_state` column, plus any row issues."""
    states: list[str] = []
    issues: list[DataIssue] = []
    for i, value, flag, printed in zip(readings.index, readings["value"], readings["flag"], readings["value_as_printed"]):
        state, problem = classify_measurement(value, flag, printed)
        states.append(state)
        if problem:
            issues.append(DataIssue(source, int(i), "value/flag", problem))
    out = readings.copy()
    out["value_state"] = states
    return out, issues


# ------------------------------------------------------------ expected grid

def build_expected_grid(readings: pd.DataFrame, years: tuple[int, ...] = YEARS, source: str = READINGS_FILE) -> pd.DataFrame:
    """Every (year, festival, site, phase, parameter) cell, matched to its source row.

    `readings` must already carry `value_state`. Cells with no source row get
    value_state `no_table` and blank source fields; nothing is invented for them.
    Raises if the data cannot support the expected grid (a whole year, festival,
    site, phase or parameter has no rows, or a row falls outside the grid).
    """
    expected = {"year": years, "festival": FESTIVALS, "site": SITES, "phase": PHASES, "parameter": PARAMETERS}
    for column, values in expected.items():
        absent = [v for v in values if v not in set(readings[column])]
        if absent:
            raise DataValidationError(
                source, column,
                f"no rows at all for {', '.join(map(str, absent))}; wrong file or wrong `years`?",
            )

    grid = pd.DataFrame(
        list(itertools.product(years, FESTIVALS, SITES, PHASES, PARAMETERS)),
        columns=["year", "festival", "site", "phase", "parameter"],
    )
    grid["year"] = grid["year"].astype("Int64")
    merged = grid.merge(readings, on=list(KEY_COLUMNS), how="outer", indicator=True, validate="one_to_one")

    outside = merged[merged["_merge"] == "right_only"]
    if not outside.empty:
        raise DataValidationError(source, "year", f"{len(outside)} row(s) fall outside the expected grid (years {years})")

    no_table = merged["_merge"] == "left_only"
    merged.loc[no_table, "value_state"] = "no_table"
    return merged.drop(columns="_merge").reset_index(drop=True)


# ------------------------------------------------------------ summary

def summarize(
    readings: pd.DataFrame,
    grid: pd.DataFrame,
    criteria: pd.DataFrame,
    issues: list[DataIssue],
    readings_name: str = READINGS_FILE,
    criteria_name: str = CRITERIA_FILE,
) -> ValidationSummary:
    counts = grid["value_state"].value_counts()
    return ValidationSummary(
        files={readings_name: len(readings), criteria_name: len(criteria)},
        columns_checked={readings_name: READINGS_COLUMNS, criteria_name: CRITERIA_COLUMNS},
        distinct={c: readings[c].nunique() for c in ("site", "year", "festival", "phase", "parameter")},
        duplicate_keys=len(find_duplicate_keys(readings)),
        expected_cells=len(grid),
        value_state_counts={s: int(counts.get(s, 0)) for s in VALUE_STATES},
        no_table_cells=int(counts.get("no_table", 0)),
        issues=list(issues),
    )


def load_all(
    data_dir: Path | str = DATA_DIR,
    readings_file: str = READINGS_FILE,
    criteria_file: str = CRITERIA_FILE,
    years: tuple[int, ...] = YEARS,
) -> LoadedData:
    """Load both files, classify readings, build the grid and summarise. Raises on invalid input."""
    data_dir = Path(data_dir)
    raw = load_readings(data_dir / readings_file)
    criteria = load_criteria(data_dir / criteria_file)
    readings, issues = classify_value_states(raw, readings_file)
    grid = build_expected_grid(readings, years, readings_file)
    summary = summarize(readings, grid, criteria, issues, readings_file, criteria_file)
    return LoadedData(readings=readings, grid=grid, criteria=criteria, summary=summary)


if __name__ == "__main__":
    print(load_all().summary.to_text())
