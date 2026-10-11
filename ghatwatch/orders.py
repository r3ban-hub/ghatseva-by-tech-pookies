"""Per-ghat work orders: the plan's actions routed to roles, one page per ghat.

Inputs are the existing Ranking (flags, evidence), Plan (dated actions) and
config/ghat_assignments.csv (task group -> ROLE per ghat). Nothing here
re-applies a threshold or recomputes a flag.

Privacy: the assignments file holds role titles only. Phone numbers, email
addresses and names written with an honorific (Shri, Smt, Dr, Mr ...) are
rejected. This is a heuristic: a bare name such as "R. Sharma" cannot be
detected and must be kept out by whoever edits the file. Unknown roles or
wards stay blank and print as "Assign: ________" / "________"; nothing is
filled in.

The tool never sends a work order and never collects a report. The officer
forwards orders through BMC's existing channels.

Usage:
    python -m ghatwatch.orders "Bairagarh (Sant Hirdaram) kund"   # print one order
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import load
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

ASSIGNMENTS_FILE = pl.CONFIG_DIR / "ghat_assignments.csv"
ASSIGNMENT_COLUMNS = ("site", "zone_ward", "task_group", "responsible_role", "report_to_role")
TEXT_FIELDS = ("zone_ward", "responsible_role", "report_to_role", "note")

ISSUED_BY = "Visarjan nodal officer, BMC"
ASSIGN_BLANK = "Assign: ________"
FILL_BLANK = "________"
FOOTER = ("Generated from MPPCB visarjan reports 2023–2025 by Visarjan Ghat Watch. "
          "Recommendations for officer verification. Not an official MPPCB assessment.")
REPORT_BACK = (
    "Tick sheet of tasks done",
    "Photos before and after",
    "Dates the aerators started and stopped (if aerators were used)",
    "Quantity of debris removed (if measured)",
)
NOTES = (
    "This tool does not send work orders or collect reports. Forward this order, and return the report, "
    "through BMC's existing channels (print, email or WhatsApp).",
    "Readings show past water quality against CPCB limits. They do not show causes or health effects.",
)

# Privacy patterns. Seven or more digits in a run (spaces, dashes, dots, brackets
# allowed) looks like a phone number; ward/zone numbers are shorter. Valid
# calendar dates (2026-10-11, 12.10.2026, 12/10/2026) are removed first so a
# revision date in a note is not mistaken for a phone number.
_DATE = re.compile(
    r"\b(?:19|20)\d{2}-(?:0?[1-9]|1[0-2])-(?:0?[1-9]|[12]\d|3[01])\b"
    r"|\b(?:0?[1-9]|[12]\d|3[01])[./-](?:0?[1-9]|1[0-2])[./-](?:19|20)\d{2}\b"
)
_PHONE = re.compile(r"\+?\d(?:[\s\-().]*\d){6,}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# An honorific followed by a name, with or without a space ("Dr. Sharma", "Dr.Sharma").
# HEURISTIC ONLY: a bare name such as "R. Sharma" or "Sharma" cannot be told apart
# from a role title and is NOT detected. Reviewers must still keep the file to roles.
_HONORIFIC = re.compile(r"\b(mr|mrs|ms|miss|shri|shree|sri|smt|kumari|dr)\b\.?\s*(?=[A-Za-z])", re.IGNORECASE)


@dataclass(frozen=True)
class Assignment:
    site: str
    task_group: str
    responsible_role: str | None
    report_to_role: str | None
    role_is_assumption: bool
    note: str | None


@dataclass(frozen=True)
class Assignments:
    by_key: dict[tuple[str, str], Assignment]  # (site, task_group)
    zone_ward: dict[str, str | None]  # site -> zone/ward, None if not entered


@dataclass(frozen=True)
class TargetItem:
    parameter: str
    target: str  # "≥ 5 mg/l", "6.5–8.5"
    tested_in_data: bool
    source: str


@dataclass(frozen=True)
class WorkOrderTask:
    number: int
    action: pl.PlannedAction  # dates, texts, triggers, verification, evidence
    responsible: str  # role, or ASSIGN_BLANK
    responsible_assigned: bool
    responsible_is_assumption: bool
    report_to: str | None
    assignment_note: str | None


@dataclass(frozen=True)
class WorkOrder:
    site: str  # canonical name used by the tool
    names_as_printed: dict[str, tuple[str, ...]]  # festival -> names in the MPPCB tables
    water_body: str | None
    zone_ward: str | None
    tier: int
    tier_label: str
    high_risk: bool
    ranking_scope: str  # e.g. "Ganesh, Durga 2023–2025, all phases"
    flags: tuple[rk.Flag, ...]
    issued_by: str
    issue_date: date
    event_date: date
    tasks: tuple[WorkOrderTask, ...]
    targets: tuple[TargetItem, ...]
    target_sample_date: date
    report_back: tuple[str, ...]
    report_to: tuple[str, ...]
    notes: tuple[str, ...]
    footer: str
    # (year, festival, site, phase, parameter) of readings matched in the partial manual PDF check
    spot_checked: frozenset[tuple] = field(default_factory=frozenset)

    @property
    def zone_ward_display(self) -> str:
        return self.zone_ward or FILL_BLANK


# ------------------------------------------------------------ assignments

def _privacy_problem(text: str) -> str | None:
    if _EMAIL.search(text):
        return "looks like an email address"
    if _PHONE.search(_DATE.sub(" ", text)):
        return "looks like a phone number"
    if _HONORIFIC.search(text):
        return "looks like a person's name (honorific found); use a role title"
    return None


def load_assignments(path: Path | str = ASSIGNMENTS_FILE) -> Assignments:
    """Read and validate the assignments CSV. Errors name the file, row and column.

    Blank roles and wards stay None. A (site, task group) pair with no row is
    simply unassigned.
    """
    path = Path(path)
    source = path.name
    df = load.read_csv_strict(path)
    load.validate_columns(df, ASSIGNMENT_COLUMNS, source)

    def bad(i: int, column: str, problem: str) -> load.DataValidationError:
        return load.DataValidationError(source, column, f"row {i + 1}: {problem}")

    by_key: dict[tuple[str, str], Assignment] = {}
    wards: dict[str, set[str]] = {s: set() for s in load.SITES}
    for i, row in df.iterrows():
        row = {k: v.strip() for k, v in row.items()}
        if row["site"] not in load.SITES:
            raise bad(i, "site", f"{row['site']!r} is not one of the 7 standard ghat names")
        if row["task_group"] not in pl.TASK_GROUPS:
            raise bad(i, "task_group", f"{row['task_group']!r} not one of: {', '.join(pl.TASK_GROUPS)}")
        for column in TEXT_FIELDS:
            problem = _privacy_problem(row.get(column, ""))
            if problem:
                raise bad(i, column, f"{problem}. Store role titles only, no personal data.")
        assumption = row.get("role_is_assumption", "no") or "no"
        if assumption not in ("yes", "no"):
            raise bad(i, "role_is_assumption", f"{assumption!r} must be yes or no")
        key = (row["site"], row["task_group"])
        if key in by_key:
            raise bad(i, "task_group", f"{row['site']} / {row['task_group']} is assigned more than once")
        by_key[key] = Assignment(
            site=row["site"], task_group=row["task_group"],
            responsible_role=row["responsible_role"] or None, report_to_role=row["report_to_role"] or None,
            role_is_assumption=assumption == "yes", note=row.get("note") or None,
        )
        if row["zone_ward"]:
            wards[row["site"]].add(row["zone_ward"])

    zone_ward = {}
    for site, values in wards.items():
        if len(values) > 1:
            raise load.DataValidationError(source, "zone_ward", f"{site} has conflicting values: {', '.join(sorted(values))}")
        zone_ward[site] = next(iter(values), None)
    return Assignments(by_key=by_key, zone_ward=zone_ward)


# ------------------------------------------------------------ building orders

def printed_site_names(readings: pd.DataFrame) -> dict[str, dict[str, tuple[str, ...]]]:
    """site -> festival -> every distinct site_as_printed, in source order."""
    out: dict[str, dict[str, tuple[str, ...]]] = {}
    for site in load.SITES:
        rows = readings[readings["site"] == site]
        out[site] = {f: tuple(dict.fromkeys(rows.loc[rows["festival"] == f, "site_as_printed"]))
                     for f in load.FESTIVALS if (rows["festival"] == f).any()}
    return out


def class_b_targets(table: cr.CriteriaTable) -> tuple[TargetItem, ...]:
    """The Class B checklist, read from the criteria CSV, in checklist order."""
    order = {p: i for i, p in enumerate(cr.CHECKLIST_ORDER)}
    items = []
    for c in sorted(cr.criteria_for_class(table, "B"), key=lambda c: order.get(c.parameter, len(order))):
        unit = f" {c.unit}" if c.unit else ""
        if c.limit_type == "min":
            target = f"≥ {c.limit_as_printed}{unit}"
        elif c.limit_type == "max":
            target = f"≤ {c.limit_as_printed}{unit}"
        else:
            target = f"{c.limit_as_printed.replace('-', '–')}{unit}"
        items.append(TargetItem(c.parameter, target, c.parameter in load.PARAMETERS,
                                f"{load.CRITERIA_FILE}, Class B"))
    return tuple(items)


def _scope_text(ranking: rk.Ranking) -> str:
    years = f"{ranking.years[0]}–{ranking.years[-1]}" if len(ranking.years) > 1 else str(ranking.years[0])
    phases = "all phases" if ranking.phases == load.PHASES else ", ".join(ranking.phases)
    return f"{', '.join(ranking.festivals)} {years}, {phases}"


def _check_order(order: WorkOrder, planned: tuple[pl.PlannedAction, ...]) -> None:
    """PRD §7.4 guarantees. Raises PlanError if the plan breaks them."""
    if tuple(t.action for t in order.tasks) != planned:
        raise pl.PlanError(f"{order.site}: work order does not list every planned action")
    codes = {f.code for f in order.flags}
    if "DATA_GAP" in codes and not any(
        t.action.task_group == "Water sampling" and t.action.end < order.event_date for t in order.tasks
    ):
        raise pl.PlanError(f"{order.site}: DATA_GAP but no sampling task before {order.event_date:%d %b}")
    if "SITE_IDENTITY" in codes and not any(t.action.task_group == "Site identity check" for t in order.tasks):
        raise pl.PlanError(f"{order.site}: SITE_IDENTITY but no field-check task")


def work_order(
    site: str,
    ranking: rk.Ranking,
    plan: pl.Plan,
    assignments: Assignments,
    table: cr.CriteriaTable | None = None,
    names_as_printed: dict[str, dict[str, tuple[str, ...]]] | None = None,
    issue_date: date | str | None = None,
    spot_checks: pd.DataFrame | None = None,
) -> WorkOrder:
    """Build the work order for one ghat.

    issue_date defaults to the plan's first day (11 Oct 2026 for the default
    event), so output is reproducible; pass the real date when issuing.
    names_as_printed comes from printed_site_names(); without it, names are
    taken from the flags' evidence.
    spot_checks: the PARTIAL manual PDF check record, already validated against
    the readings (work_orders does this). Without it no reading is marked as
    checked and every page reference is described as not yet checked.
    """
    ghat = next((g for g in ranking.ghats if g.site == site), None)
    if ghat is None:
        raise ValueError(f"{site!r} is not in the ranking")
    table = table if table is not None else cr.load_criteria_table()
    try:
        issued = pl.as_event_date(issue_date) if issue_date is not None else plan.start
    except ValueError as exc:
        raise ValueError(f"issue date {issue_date!r} is not a valid date (use YYYY-MM-DD)") from exc

    if names_as_printed is not None:
        printed = names_as_printed.get(site, {})
    else:
        ev = [e for f in ghat.flags for e in f.evidence if e.site_as_printed]
        printed = {fest: tuple(dict.fromkeys(e.site_as_printed for e in ev if e.festival == fest))
                   for fest in load.FESTIVALS if any(e.festival == fest for e in ev)}

    planned = plan.for_site(site)
    tasks = []
    for n, action in enumerate(planned, start=1):
        a = assignments.by_key.get((site, action.task_group))
        role = a.responsible_role if a else None
        tasks.append(WorkOrderTask(
            number=n, action=action, responsible=role or ASSIGN_BLANK, responsible_assigned=role is not None,
            responsible_is_assumption=bool(a and role and a.role_is_assumption),
            report_to=a.report_to_role if a else None, assignment_note=a.note if a else None,
        ))
    report_to = tuple(dict.fromkeys(t.report_to for t in tasks if t.report_to)) or (ISSUED_BY,)

    order = WorkOrder(
        site=site, names_as_printed=printed, water_body=ghat.water_body, zone_ward=assignments.zone_ward.get(site),
        tier=ghat.tier, tier_label=ghat.tier_label, high_risk=ghat.high_risk, ranking_scope=_scope_text(ranking),
        flags=ghat.flags, issued_by=ISSUED_BY, issue_date=issued, event_date=plan.event_date, tasks=tuple(tasks),
        targets=class_b_targets(table), target_sample_date=plan.end, report_back=REPORT_BACK,
        report_to=report_to, notes=(_page_note(spot_checks),) + NOTES, footer=FOOTER,
        spot_checked=frozenset(evm.spot_checked_keys(spot_checks)) if spot_checks is not None else frozenset(),
    )
    _check_order(order, planned)
    return order


def work_orders(
    ranking: rk.Ranking,
    plan: pl.Plan,
    assignments: Assignments | Path | str = ASSIGNMENTS_FILE,
    table: cr.CriteriaTable | None = None,
    readings: pd.DataFrame | None = None,
    issue_date: date | str | None = None,
    spot_checks: pd.DataFrame | None = None,
) -> tuple[WorkOrder, ...]:
    """One work order per ranked ghat, in rank order.

    With `readings`, the manual PDF spot-check record (default
    verification/pdf_spot_checks.csv) is validated against them and checked
    readings are marked. Without `readings` nothing is marked as checked.
    """
    if not isinstance(assignments, Assignments):
        assignments = load_assignments(assignments)
    table = table if table is not None else cr.load_criteria_table()
    names = printed_site_names(readings) if readings is not None else None
    if readings is not None:
        spot_checks = spot_checks if spot_checks is not None else evm.load_spot_checks()
        evm.validate_spot_checks(spot_checks, readings)
    else:
        spot_checks = None
    unknown = {a.site for a in plan.actions} - {g.site for g in ranking.ghats}
    if unknown:
        raise ValueError(f"plan has actions for sites not in the ranking: {', '.join(sorted(unknown))}")
    return tuple(work_order(g.site, ranking, plan, assignments, table, names, issue_date, spot_checks)
                 for g in sorted(ranking.ghats, key=lambda g: g.rank))


def _page_note(spot_checks: pd.DataFrame | None) -> str:
    base = "Page references are the source_page values in the supplied CSV. "
    if spot_checks is None or spot_checks.empty:
        return base + "They have not yet been checked against the report PDFs."
    pages = spot_checks[["year", "source_page"]].drop_duplicates()
    return (base + f"Readings marked ✓ matched the PDF page in a partial manual spot check ({len(spot_checks)} readings "
            f"on {len(pages)} pages in all); all other page references have not yet been checked against the report PDFs.")


# ------------------------------------------------------------ Markdown

def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _text_cites_all_pages(flag: rk.Flag) -> bool:
    """True when every page in the flag's evidence already appears in its sentence.

    Decided from the evidence records, not from wording: each cited page must
    occur as "p.<page>" after its report year ("2023 p.26, p.60" or
    "2023 Ganesh after, p.26").
    """
    cited = [e for e in flag.evidence if e.source_page is not None]
    if not cited:
        return False
    for e in cited:
        pattern = rf"{e.year}\b[^;]*?\bp\.{e.source_page}\b"
        if not re.search(pattern, flag.text_en):
            return False
    return True


def _date(d: date) -> str:
    return f"{d.day} {d:%b %Y}"


def to_markdown(order: WorkOrder) -> str:
    """Print-friendly bilingual work order (English labels, EN + HI action text)."""
    risk = "HIGH RISK" if order.high_risk else "not flagged high risk"
    lines = [
        f"# Work order — {order.site}",
        "",
        f"**Water body:** {order.water_body or FILL_BLANK} · **Zone / ward:** {order.zone_ward_display} · "
        f"**Tier {order.tier}, {risk}**",
        "",
        "**DRAFT for officer review — not an issued order.**",
        "",
        f"**Prepared for issue by:** {order.issued_by} (role) · **Draft date:** {_date(order.issue_date)} · "
        f"**Immersion day:** {_date(order.event_date)}",
        "",
        "**Name in the MPPCB reports:**",
    ]
    for festival, names in order.names_as_printed.items():
        lines.append(f"- {festival} tables: " + "; ".join(f"“{n}”" for n in names))
    if any(f.code == "SITE_IDENTITY" for f in order.flags):
        lines.append("- These names may describe two different places. Confirm the location at the field check; "
                     "this order does not choose between them.")

    lines += ["", f"## Why this ghat ({order.ranking_scope})", "", order.tier_label + ".", ""]
    for f in order.flags:
        pages = sorted({e.page_ref for e in f.evidence})
        already_cited = _text_cites_all_pages(f)
        lines.append(f"- **{f.code}:** {f.text_en}" + (f" Sources: {', '.join(pages)}." if pages and not already_cited else ""))
        checked = [e for e in f.evidence if (e.year, e.festival, order.site, e.phase, e.parameter) in order.spot_checked]
        if checked:
            lines.append("  ✓ Matched to the PDF in the partial manual check: " + "; ".join(
                f"{e.year} p.{e.source_page} ({e.festival} {e.phase}, {e.parameter} {e.value_as_printed})" for e in checked) + ".")

    lines += ["", "## Tasks", "",
              "| # | What | Where | When | Responsible | Report to | Done | Remarks |",
              "|---|---|---|---|---|---|---|---|"]
    for t in order.tasks:
        a = t.action
        hi = a.action_hi + ("" if a.hi_reviewed else f" *({pl.PROVISIONAL_HINDI})*")
        what = f"{a.action_en}<br>{hi}<br>*{a.task_group}; trigger: {', '.join(a.triggers)}*"
        if a.warning:
            what += f"<br>⚠ {a.warning}"
        who = t.responsible + (" *(assumed — confirm)*" if t.responsible_is_assumption else "")
        lines.append(f"| {t.number} | {_cell(what)} | Location note: {FILL_BLANK} | {a.window} {a.start.year} | "
                     f"{_cell(who)} | {_cell(t.report_to or ASSIGN_BLANK)} | ☐ | |")

    lines += ["", f"## Target to report against (sample on {_date(order.target_sample_date)})", ""]
    for item in order.targets:
        note = "" if item.tested_in_data else " — not tested in the supplied data; test needed to confirm Class B"
        lines.append(f"- ☐ {item.parameter} {item.target}{note}")
    lines.append(f"\nSource: {order.targets[0].source if order.targets else load.CRITERIA_FILE}.")

    lines += ["", f"## Report back to {', '.join(order.report_to)}", "", f"By: {FILL_BLANK}", ""]
    lines += [f"- ☐ {item}" for item in order.report_back]
    lines += [""] + [f"*{n}*  " for n in order.notes]
    lines += ["", "---", order.footer, ""]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    data = load.load_all()
    ranking = rk.rank_ghats(data)
    orders = work_orders(ranking, pl.plan_actions(ranking), readings=data.readings)
    wanted = sys.argv[1] if len(sys.argv) > 1 else orders[0].site
    sys.stdout.reconfigure(encoding="utf-8")
    print(to_markdown(next(o for o in orders if o.site == wanted)))
