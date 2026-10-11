"""Evidence table: every expected cell with its reading, limit, result and source.

One row per cell of the expected grid (load.build_expected_grid), so absent
tables appear as rows too. Comparisons come from criteria.compare_frame():
Class B for the bathing standard and Class D for the severe DO line. Nothing
is recomputed here.

Source report per year follows DATA_DICTIONARY.md ("source_page: PDF page in
that year's report" and its Sources table). Page references are NOT fully
verified. `page_verified` says, per row:
- "spot-checked — ..." only for a reading listed in
  verification/pdf_spot_checks.csv (a PARTIAL manual check), whose page and
  printed value match the data;
- "no — ..." for every other row with a page;
- "" for absent-table rows (there is no page).

CSV export escapes text that a spreadsheet would run as a formula (leading
=, +, @, tab, CR, or "-" not followed by a plain number) by prefixing "'".
This happens only in the exported file; build_evidence() keeps the original.

Usage:
    python -m ghatwatch.evidence out.csv     # write the evidence CSV
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

from ghatwatch import criteria as cr
from ghatwatch import load

# Year -> (report file, URL), from DATA_DICTIONARY.md "Sources".
SOURCE_REPORTS = {
    2023: ("Idol_immer._Report_23_CPCB.pdf", "https://www.mppcb.mp.gov.in/proc/mon/Idol_immer._Report_23_CPCB.pdf"),
    2024: ("Ganesh_and_Durga_visarjan_report-2024.pdf",
           "https://www.mppcb.mp.gov.in/proc/mon/Ganesh_and_Durga_visarjan_report-2024.pdf"),
    2025: ("Ganesh_and_Durga_visarjan_report-2025.pdf",
           "https://www.mppcb.mp.gov.in/proc/mon/Ganesh_and_Durga_visarjan_report-2025.pdf"),
}
PAGE_NOT_VERIFIED = "no — source_page from the data file; not yet checked against the PDF"
PAGE_SPOT_CHECKED = ("spot-checked — this reading matched page {page} of the PDF in a partial manual check "
                     "on {checked_on}; the report as a whole is not verified")
SPOT_CHECKS_FILE = Path(__file__).resolve().parent.parent / "verification" / "pdf_spot_checks.csv"
SPOT_CHECK_COLUMNS = ("year", "festival", "site", "phase", "parameter", "value_as_printed", "source_page",
                      "report_file", "method", "checked_on", "scope")
SPOT_CHECK_SCOPE = "PARTIAL manual spot check"
NO_TABLE_NOTE = ("No table for this cell in the report. source_report names the report where it "
                 "would appear; it is not a citation for a reading.")
SITE_IDENTITY_NOTE = "site_match_confidence is not high: report tables may describe two different places under this name"

EVIDENCE_COLUMNS = (
    "year", "festival", "site", "site_as_printed", "site_match_confidence", "site_identity_note", "water_body",
    "phase", "parameter", "parameter_as_printed", "value_as_printed", "value", "value_state", "source_flag",
    "contradictory", "unit",
    "class_b_limit", "class_b_result", "class_b_reason",
    "class_d_limit", "class_d_result", "class_d_reason",
    "source_page", "page_verified", "source_report", "source_url", "source_note", "data_file",
)
_FORMULA_START = ("=", "+", "@", "\t", "\r")
_PLAIN_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _order_key(column: pd.Series) -> pd.Series:
    orders = {"festival": load.FESTIVALS, "site": load.SITES, "phase": load.PHASES, "parameter": load.PARAMETERS}
    if column.name in orders:
        return column.map({v: i for i, v in enumerate(orders[column.name])})
    return column


def load_spot_checks(path: Path | str = SPOT_CHECKS_FILE) -> pd.DataFrame:
    """Read the manual PDF spot-check record. Every row must be marked as a partial check."""
    path = Path(path)
    df = load.read_csv_strict(path)
    load.validate_columns(df, SPOT_CHECK_COLUMNS, path.name)
    load.validate_allowed_values(df, "scope", (SPOT_CHECK_SCOPE,), path.name)
    for column, allowed in (("festival", load.FESTIVALS), ("site", load.SITES), ("phase", load.PHASES),
                            ("parameter", load.PARAMETERS)):
        load.validate_allowed_values(df, column, allowed, path.name)
    df["year"] = df["year"].astype(int)
    df["source_page"] = df["source_page"].astype(int)
    if df.duplicated(list(load.KEY_COLUMNS)).any():
        raise load.DataValidationError(path.name, None, "a reading is listed more than once")
    return df


def validate_spot_checks(spot_checks: pd.DataFrame, readings: pd.DataFrame, source: str = "pdf_spot_checks.csv") -> None:
    """Each checked reading must exist in the data with the same page and printed value.

    A mismatch means the record and the data disagree; that is raised, never
    silently marked as checked.
    """
    src = readings.set_index(list(load.KEY_COLUMNS))
    for i, c in spot_checks.iterrows():
        key = (int(c["year"]), c["festival"], c["site"], c["phase"], c["parameter"])
        if key not in src.index:
            raise load.DataValidationError(source, None, f"row {i + 1}: {key} is not a reading in the data")
        row = src.loc[key]
        if int(row["source_page"]) != int(c["source_page"]) or row["value_as_printed"] != c["value_as_printed"]:
            raise load.DataValidationError(
                source, None,
                f"row {i + 1}: checked page {c['source_page']} / value {c['value_as_printed']!r} disagree with the "
                f"data (page {row['source_page']}, value {row['value_as_printed']!r})",
            )


def spot_checked_keys(spot_checks: pd.DataFrame) -> dict[tuple, str]:
    """(year, festival, site, phase, parameter) -> checked_on date, for checked readings."""
    return {(int(c["year"]), c["festival"], c["site"], c["phase"], c["parameter"]): c["checked_on"]
            for _, c in spot_checks.iterrows()}


def build_evidence(
    data: load.LoadedData,
    table: cr.CriteriaTable | None = None,
    readings_file: str = load.READINGS_FILE,
    spot_checks: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the evidence table (columns EVIDENCE_COLUMNS), one row per expected cell.

    - `value` is filled only when the Class B comparison could use the number
      (pass/fail, or no_criterion with a numeric state). BDL, ND, missing and
      contradictory cells keep value blank; value_as_printed shows the report.
    - Results are pass / fail / unassessable / no_criterion (see criteria.py).
    - Order: year, festival, site, phase, parameter (stable, as in load.*).
    - page_verified: see module docstring. spot_checks defaults to
      verification/pdf_spot_checks.csv and is validated against the readings.
    """
    table = table if table is not None else cr.load_criteria_table()
    spot_checks = spot_checks if spot_checks is not None else load_spot_checks()
    validate_spot_checks(spot_checks, data.readings)
    checked = spot_checked_keys(spot_checks)
    keys = cr.contradictory_keys(data.readings, data.summary.issues)
    b = cr.compare_frame(data.grid, table, "B", keys)
    d = cr.compare_frame(data.grid, table, "D", keys)

    def blank(series: pd.Series) -> pd.Series:
        return series.astype(object).where(series.notna(), "")

    key_tuples = list(zip(b["year"].astype(int), b["festival"], b["site"], b["phase"], b["parameter"]))
    contradictory = pd.Series([k in keys for k in key_tuples], index=b.index)
    usable = (b["value_state"] == "numeric") & ~contradictory

    out = pd.DataFrame({
        "year": b["year"].astype(int),
        "festival": b["festival"],
        "site": b["site"],
        "site_as_printed": blank(b["site_as_printed"]),
        "site_match_confidence": blank(b["site_match_confidence"]),
        "water_body": blank(b["water_body"]),
        "phase": b["phase"],
        "parameter": b["parameter"],
        "parameter_as_printed": blank(b["parameter_as_printed"]),
        "value_as_printed": blank(b["value_as_printed"]),
        "value": b["value"].astype(object).where(usable, ""),
        "value_state": b["value_state"],
        "source_flag": blank(b["flag"]),
        "contradictory": contradictory.map({True: "yes", False: "no"}),
        "unit": blank(b["unit_assumed"]),
        "class_b_limit": blank(b["limit_text"]),
        "class_b_result": b["result"],
        "class_b_reason": b["result_reason"],
        "class_d_limit": blank(d["limit_text"]),
        "class_d_result": d["result"],
        "class_d_reason": d["result_reason"],
        "source_page": b["source_page"].astype(object).where(b["source_page"].notna(), ""),
        "source_report": b["year"].astype(int).map(lambda y: SOURCE_REPORTS.get(y, ("", ""))[0]),
        "source_url": b["year"].astype(int).map(lambda y: SOURCE_REPORTS.get(y, ("", ""))[1]),
        "data_file": readings_file,
    })
    out["site_identity_note"] = [
        SITE_IDENTITY_NOTE if conf not in ("", "high") else "" for conf in out["site_match_confidence"]
    ]
    # Absent tables have no page and no printed text: say so instead of leaving it to guesswork.
    no_table = out["value_state"] == "no_table"
    out.loc[no_table, "value_as_printed"] = ""
    out["page_verified"] = [
        "" if nt else (PAGE_SPOT_CHECKED.format(page=page, checked_on=checked[key]) if key in checked else PAGE_NOT_VERIFIED)
        for nt, key, page in zip(no_table, key_tuples, out["source_page"])
    ]
    out["source_note"] = [(NO_TABLE_NOTE if nt else "") for nt in no_table]
    # Site identity is site-level: carry it to absent cells too.
    flagged_sites = set(out.loc[out["site_identity_note"] != "", "site"])
    out.loc[out["site"].isin(flagged_sites), "site_identity_note"] = SITE_IDENTITY_NOTE

    out = out.sort_values(["year", "festival", "site", "phase", "parameter"], key=_order_key, kind="mergesort")
    return out[list(EVIDENCE_COLUMNS)].reset_index(drop=True)


def escape_formula(value: object) -> object:
    """Prefix "'" to text a spreadsheet would run as a formula; numbers and other text unchanged."""
    if not isinstance(value, str) or value in ("", "-"):
        return value
    if value.startswith(_FORMULA_START) or (value.startswith("-") and not _PLAIN_NUMBER.fullmatch(value)):
        return "'" + value
    return value


def evidence_csv_bytes(evidence: pd.DataFrame) -> bytes:
    """UTF-8 CSV (with BOM so Excel shows µ and Hindi correctly), LF line endings.

    Formula-like text is escaped in the export only (see escape_formula); the
    in-memory evidence table is not changed.
    """
    buffer = io.StringIO()
    export = evidence[list(EVIDENCE_COLUMNS)].copy()
    for column in export.columns:
        export[column] = export[column].map(escape_formula)
    export.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue().encode("utf-8-sig")


def write_evidence_csv(evidence: pd.DataFrame, path: Path | str) -> Path:
    path = Path(path)
    path.write_bytes(evidence_csv_bytes(evidence))
    return path


def read_evidence_csv(path: Path | str) -> pd.DataFrame:
    """Read an exported evidence CSV back as text (blank cells stay "")."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "evidence.csv"
    ev = build_evidence(load.load_all())
    print(f"{write_evidence_csv(ev, target)}: {len(ev)} rows")
