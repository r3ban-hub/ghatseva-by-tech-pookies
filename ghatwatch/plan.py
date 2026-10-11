"""Turn ranking flags into a dated action plan, using editable rules.

Rules live in config/action_rules.csv (one row per action). The planner only
reads flag codes, tiers and evidence from ranking.py; it never re-applies a
threshold. Dates are relative to the immersion day D (20 Oct 2026 by default)
and the whole plan runs D-9 to D+7 (11-27 Oct).

Rules file columns:
    trigger_flag   a ranking flag code, several joined by "|" (any of them
                   triggers the rule once), or ALL_GHATS
    action_en, action_hi
    task_group     one of TASK_GROUPS
    when           "D", "D+7", "D-3 to D+7" ...
    source         where the action comes from
    verified       yes | no. "yes" needs a real citation in `source`
    action_hi_reviewed (optional) yes | no. Hindi checked by a fluent reader

Nothing here records completion or acceptance: every action is a
recommendation for the officer.

Usage:
    python -m ghatwatch.plan             # print the plan for all data
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from ghatwatch import load
from ghatwatch import ranking as rk

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
RULES_FILE = CONFIG_DIR / "action_rules.csv"

EVENT_DATE = date(2026, 10, 20)  # Durga visarjan, D
PLAN_START_OFFSET, PLAN_END_OFFSET = -9, 7  # PRD §7.3: 11 Oct to 27 Oct

ALL_GHATS = "ALL_GHATS"
TASK_GROUPS = ("Cleaning & debris", "Aeration", "Barricading & nets", "Water sampling", "Site identity check")
RULE_COLUMNS = ("trigger_flag", "action_en", "action_hi", "task_group", "when", "source", "verified")
UNVERIFIED_WARNING = "Recommendation — verify with MPPCB / CPCB guidelines."
PROVISIONAL_HINDI = "Provisional translation — to be reviewed by a fluent Hindi reader."

_WINDOW = re.compile(r"^D([+-]\d+)?(\s+to\s+D([+-]\d+)?)?$")


class PlanError(ValueError):
    """The rules cannot produce a plan that meets the PRD's guarantees."""


@dataclass(frozen=True)
class ActionRule:
    rule_id: str  # "R<row number>", by position in the CSV
    triggers: tuple[str, ...]
    action_en: str
    action_hi: str
    hi_reviewed: bool
    task_group: str
    when: str
    start_offset: int
    end_offset: int
    source: str
    verified: bool


@dataclass(frozen=True)
class PlannedAction:
    order: int  # position in the whole plan (1-based)
    ghat_rank: int  # priority: rank from ranking.py, 1 = highest risk
    tier: int
    high_risk: bool
    site: str
    water_body: str | None
    triggers: tuple[str, ...]  # flags on this ghat that matched, or ("ALL_GHATS",)
    rule_ids: tuple[str, ...]
    action_en: str
    action_hi: str
    hi_reviewed: bool
    task_group: str
    when: str  # relative window as configured
    start: date
    end: date
    window: str  # "17–27 Oct"
    source: str
    verified: bool
    warning: str | None  # UNVERIFIED_WARNING unless verified
    evidence: tuple[rk.Evidence, ...]  # readings behind the triggering flags


@dataclass(frozen=True)
class OverviewActivity:
    text_en: str
    sites: tuple[str, ...] | None  # None: applies to the operation as a whole


@dataclass(frozen=True)
class OverviewWindow:
    start: date
    end: date
    window: str
    activities: tuple[OverviewActivity, ...]


@dataclass(frozen=True)
class Plan:
    event_date: date
    start: date
    end: date
    actions: tuple[PlannedAction, ...]
    overview: tuple[OverviewWindow, ...]
    note: str = "Planning recommendation only. It does not show that tasks are scheduled, accepted or resourced."

    def for_site(self, site: str) -> tuple[PlannedAction, ...]:
        return tuple(a for a in self.actions if a.site == site)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "order": a.order, "rank": a.ghat_rank, "site": a.site, "task_group": a.task_group,
            "window": a.window, "start": a.start, "end": a.end, "triggers": ", ".join(a.triggers),
            "action_en": a.action_en, "action_hi": a.action_hi, "source": a.source,
            "verified": "yes" if a.verified else "no", "warning": a.warning or "",
            "pages": "; ".join(sorted({e.page_ref for e in a.evidence})),
        } for a in self.actions])


# ------------------------------------------------------------ dates

def as_event_date(value: date | str) -> date:
    """Accept a date or an ISO string 'YYYY-MM-DD'; anything else is an error."""
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"event date {value!r} is not a valid date (use YYYY-MM-DD)") from exc
    if isinstance(value, date):
        return date(value.year, value.month, value.day)  # drops any time part
    raise ValueError(f"event date must be a date or 'YYYY-MM-DD', got {type(value).__name__}")


def parse_window(when: str) -> tuple[int, int]:
    """'D-3 to D+7' -> (-3, 7); 'D' -> (0, 0); 'D+7' -> (7, 7)."""
    m = _WINDOW.match(when.strip())
    if not m:
        raise ValueError(f"window {when!r} not understood; use 'D', 'D+7', 'D-3' or 'D-3 to D+7'")
    start = int(m.group(1) or 0)
    # The "to D..." group decides whether there is an end; any whitespace may surround "to".
    end = int(m.group(3) or 0) if m.group(2) is not None else start
    if end < start:
        raise ValueError(f"window {when!r} ends before it starts")
    return start, end


def window_dates(when: str, event_date: date | str = EVENT_DATE) -> tuple[date, date]:
    d = as_event_date(event_date)
    start, end = parse_window(when)
    return d + timedelta(days=start), d + timedelta(days=end)


def window_label(start: date, end: date) -> str:
    """'11–13 Oct', '27 Oct', '30 Oct–2 Nov'."""
    if start == end:
        return f"{start.day} {start:%b}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}–{end.day} {end:%b}"
    return f"{start.day} {start:%b}–{end.day} {end:%b}"


def plan_period(event_date: date | str = EVENT_DATE) -> tuple[date, date]:
    d = as_event_date(event_date)
    return d + timedelta(days=PLAN_START_OFFSET), d + timedelta(days=PLAN_END_OFFSET)


# ------------------------------------------------------------ rules

def load_action_rules(path: Path | str = RULES_FILE) -> tuple[ActionRule, ...]:
    """Read and validate the rules CSV. Raises load.DataValidationError naming row and column."""
    path = Path(path)
    source = path.name
    df = load.read_csv_strict(path)
    load.validate_columns(df, RULE_COLUMNS, source)
    known_triggers = set(rk.FLAG_ORDER) | {ALL_GHATS}

    def bad(i: int, column: str, problem: str) -> load.DataValidationError:
        return load.DataValidationError(source, column, f"row {i + 1}: {problem}")

    rules = []
    for i, row in df.iterrows():
        row = {k: v.strip() for k, v in row.items()}
        triggers = tuple(t.strip() for t in row["trigger_flag"].split("|"))
        unknown = [t for t in triggers if t not in known_triggers]
        if unknown or not row["trigger_flag"]:
            raise bad(i, "trigger_flag", f"{row['trigger_flag']!r} is not a ranking flag or {ALL_GHATS}; "
                                         f"known: {', '.join(sorted(known_triggers))}")
        if ALL_GHATS in triggers and len(triggers) > 1:
            raise bad(i, "trigger_flag", f"{ALL_GHATS} cannot be combined with other flags")
        for column in ("action_en", "action_hi", "source"):
            if not row[column]:
                raise bad(i, column, "is blank")
        if row["task_group"] not in TASK_GROUPS:
            raise bad(i, "task_group", f"{row['task_group']!r} not one of: {', '.join(TASK_GROUPS)}")
        if row["verified"] not in ("yes", "no"):
            raise bad(i, "verified", f"{row['verified']!r} must be yes or no")
        if row["verified"] == "yes" and row["source"].lower().startswith("team recommendation"):
            raise bad(i, "verified", "marked yes but source is a team recommendation; cite the guideline first")
        reviewed = row.get("action_hi_reviewed", "no") or "no"
        if reviewed not in ("yes", "no"):
            raise bad(i, "action_hi_reviewed", f"{reviewed!r} must be yes or no")
        try:
            start, end = parse_window(row["when"])
        except ValueError as exc:
            raise bad(i, "when", str(exc)) from exc
        if start < PLAN_START_OFFSET or end > PLAN_END_OFFSET:
            raise bad(i, "when", f"{row['when']!r} falls outside the plan period "
                                 f"D{PLAN_START_OFFSET:+d} to D{PLAN_END_OFFSET:+d}")
        rules.append(ActionRule(
            rule_id=f"R{i + 1}", triggers=triggers, action_en=row["action_en"], action_hi=row["action_hi"],
            hi_reviewed=reviewed == "yes", task_group=row["task_group"], when=row["when"],
            start_offset=start, end_offset=end, source=row["source"], verified=row["verified"] == "yes",
        ))
    return tuple(rules)


# ------------------------------------------------------------ planning

def _ghat_actions(g: rk.GhatRank, rules: tuple[ActionRule, ...], event_date: date) -> list[PlannedAction]:
    flags = {f.code: f for f in g.flags}
    merged: dict[tuple, PlannedAction] = {}
    for rule in rules:
        if rule.triggers == (ALL_GHATS,):
            matched: tuple[str, ...] = (ALL_GHATS,)
        else:
            matched = tuple(t for t in rule.triggers if t in flags)
            if not matched:
                continue
        evidence = tuple(dict.fromkeys(e for t in matched if t in flags for e in flags[t].evidence))
        start = event_date + timedelta(days=rule.start_offset)
        end = event_date + timedelta(days=rule.end_offset)
        action = PlannedAction(
            order=0, ghat_rank=g.rank, tier=g.tier, high_risk=g.high_risk, site=g.site, water_body=g.water_body,
            triggers=matched, rule_ids=(rule.rule_id,), action_en=rule.action_en, action_hi=rule.action_hi,
            hi_reviewed=rule.hi_reviewed, task_group=rule.task_group, when=rule.when, start=start, end=end,
            window=window_label(start, end), source=rule.source, verified=rule.verified,
            warning=None if rule.verified else UNVERIFIED_WARNING, evidence=evidence,
        )
        # Two rows describing the very same task (text, group, dates) become one.
        key = (rule.action_en, rule.task_group, start, end)
        if key in merged:
            prev = merged[key]
            if prev.action_hi != action.action_hi:
                raise PlanError(
                    f"Rules {', '.join(prev.rule_ids)} and {rule.rule_id} describe the same task "
                    f"({rule.task_group}, {rule.when}) with different Hindi text. Make the Hindi identical "
                    f"or the English distinct in {RULES_FILE.name}; neither text is dropped silently."
                )
            verified = prev.verified and action.verified
            action = replace(
                prev,
                triggers=tuple(dict.fromkeys(prev.triggers + matched)),
                rule_ids=prev.rule_ids + action.rule_ids,
                evidence=tuple(dict.fromkeys(prev.evidence + evidence)),
                source="; ".join(dict.fromkeys([prev.source, action.source])),
                verified=verified, warning=None if verified else UNVERIFIED_WARNING,
                hi_reviewed=prev.hi_reviewed and action.hi_reviewed,
            )
        merged[key] = action
    return sorted(merged.values(), key=lambda a: (a.start, a.end, a.rule_ids))


def _check_guarantees(actions: list[PlannedAction], ranking: rk.Ranking, event_date: date) -> None:
    """PRD §7.4: DATA_GAP -> sampling before D; SITE_IDENTITY -> field check."""
    for g in ranking.ghats:
        mine = [a for a in actions if a.site == g.site]
        if "DATA_GAP" in g.flag_codes and not any(
            a.task_group == "Water sampling" and a.end < event_date for a in mine
        ):
            raise PlanError(f"{g.site} has DATA_GAP but the rules give it no Water sampling task ending before "
                            f"{event_date:%d %b}. Check {RULES_FILE.name}.")
        if "SITE_IDENTITY" in g.flag_codes and not any(a.task_group == "Site identity check" for a in mine):
            raise PlanError(f"{g.site} has SITE_IDENTITY but the rules give it no Site identity check task. "
                            f"Check {RULES_FILE.name}.")


# Overview per PRD §7.3. Offsets from D; the site lists come from the ranking.
Selector = Callable[[rk.GhatRank], bool] | None
_has = lambda *codes: (lambda g: any(c in g.flag_codes for c in codes))  # noqa: E731
OVERVIEW: tuple[tuple[int, int, tuple[tuple[str, Selector], ...]], ...] = (
    (-9, -7, (
        ("Officer approves the priority list", None),
        ("Field check of site identity", _has("SITE_IDENTITY")),
        ("Request priority pre-immersion sampling", _has("DATA_GAP")),
    )),
    (-6, -3, (
        ("Pre-immersion sampling", _has("DATA_GAP", "PH_OUT")),
        ("Install barricades, nets or booms", lambda g: True),
        ("Set up flower and offering collection points", _has("BOD_OFTEN_HIGH")),
        ("Arrange aerators for Tier 1 ghats", lambda g: g.tier == 1),
    )),
    (-2, -1, (
        ("Aerators running", _has("DO_SEVERE", "DO_ZERO")),
        ("Brief and deploy crews", None),
        ("Re-check DO at Tier 1 ghats", lambda g: g.tier == 1),
    )),
    (0, 0, (
        ("Immersion day: during-immersion sampling", lambda g: True),
        ("Aeration on", _has("DO_SEVERE", "DO_ZERO", "DO_OFTEN_LOW")),
        ("Continuous floating-debris removal", lambda g: True),
    )),
    (1, 2, (
        ("Post-visarjan clean-up: idol remnants, frames, cloth and floral waste removed for disposal", lambda g: True),
        ("Aeration continues", _has("DO_SEVERE", "DO_ZERO", "DO_OFTEN_LOW")),
    )),
    (3, 6, (
        ("Follow-up DO checks at high-risk ghats", lambda g: g.high_risk),
        ("Residual clean-up", lambda g: True),
    )),
    (7, 7, (
        ("One-week-after sampling: DO, BOD, pH and total coliform", lambda g: True),
        ("Assess each ghat against the Class B checklist; officer report", None),
    )),
)


def build_overview(ranking: rk.Ranking, event_date: date | str = EVENT_DATE) -> tuple[OverviewWindow, ...]:
    d = as_event_date(event_date)
    ghats = sorted(ranking.ghats, key=lambda g: g.rank)
    windows = []
    for start_off, end_off, activities in OVERVIEW:
        start, end = d + timedelta(days=start_off), d + timedelta(days=end_off)
        items = []
        for text, select in activities:
            sites = None if select is None else tuple(g.site for g in ghats if select(g))
            if sites == ():
                continue  # no ghat needs it in this scope
            items.append(OverviewActivity(text, sites))
        windows.append(OverviewWindow(start, end, window_label(start, end), tuple(items)))
    return tuple(windows)


def plan_actions(
    ranking: rk.Ranking,
    rules: tuple[ActionRule, ...] | Path | str = RULES_FILE,
    event_date: date | str = EVENT_DATE,
) -> Plan:
    """Build the dated plan: per-ghat actions in rank order, plus the overview."""
    d = as_event_date(event_date)
    if not isinstance(rules, tuple):
        rules = load_action_rules(rules)
    actions: list[PlannedAction] = []
    for g in sorted(ranking.ghats, key=lambda g: g.rank):
        actions.extend(_ghat_actions(g, rules, d))
    _check_guarantees(actions, ranking, d)
    actions = [replace(a, order=i) for i, a in enumerate(actions, start=1)]
    start, end = plan_period(d)
    return Plan(event_date=d, start=start, end=end, actions=tuple(actions), overview=build_overview(ranking, d))


if __name__ == "__main__":
    plan = plan_actions(rk.rank_ghats(load.load_all()))
    print(f"Plan {window_label(plan.start, plan.end)} {plan.end.year}, immersion {plan.event_date:%d %b}. {plan.note}\n")
    for w in plan.overview:
        print(w.window)
        for a in w.activities:
            print(f"  - {a.text_en}" + (f": {', '.join(a.sites)}" if a.sites is not None else ""))
    print()
    for a in plan.actions:
        print(f"{a.order:>2}. [{a.ghat_rank}] {a.site} | {a.window} | {a.task_group} | {', '.join(a.triggers)}"
              f"{' | ' + a.warning if a.warning else ''}")
