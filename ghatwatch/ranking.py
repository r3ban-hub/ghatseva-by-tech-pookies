"""Rank the Bhopal ghats by risk and explain each rank with evidence-backed flags.

Every pass/fail decision comes from criteria.compare_frame(), so limits are the
CSV's, boundaries are inclusive, and contradictory rows are already excluded.
A reading is "usable numeric" only when its Class B result is pass or fail.

Tiers (PRD §6.4), DO first:
    1  DO fail rate > 50%
    2  any usable DO reading below the Class B minimum
    3  no DO failure, but a BOD or pH failure
    4  no failure in any reading taken (never called "clean" or "safe")
Missing readings never count as passes, so a gap cannot lower a tier; it adds
a DATA_GAP flag instead.

Unavailable metrics (no usable readings, so no rate or median) are None. In
tie-breaks a None always sorts AFTER every real value, so a missing metric
never outranks a measured one.

Page references are the `source_page` values in the CSV, quoted with the
report year. They have NOT been checked against the PDFs (PRD §3.3.6).

Usage:
    python -m ghatwatch.ranking          # print the all-data ranking
"""

from __future__ import annotations

import numbers
from dataclasses import dataclass, field
from statistics import median
from typing import Iterable

import pandas as pd

from ghatwatch import criteria as cr
from ghatwatch import load

DO, BOD, PH = "Dissolved oxygen", "BOD", "pH"
RANKED_PARAMETERS = (DO, BOD, PH)

# PRD §6.3: "often" means strictly more than half of usable readings.
OFTEN_SHARE = 0.5

FLAG_ORDER = ("DO_SEVERE", "DO_ZERO", "DO_OFTEN_LOW", "BOD_OFTEN_HIGH", "PH_OUT", "DATA_GAP", "SITE_IDENTITY")
HIGH_RISK_FLAGS = ("DO_SEVERE", "DO_OFTEN_LOW")

# Limit directions the flag codes, flag sentences, tiers and action rules assume.
# rank_grid refuses a criteria table that contradicts them (values are not checked).
REQUIRED_DIRECTIONS = {
    ("B", DO): ("min", "tiers 1-2 and DO_OFTEN_LOW treat readings below the limit as failures"),
    ("D", DO): ("min", "DO_SEVERE treats readings below the Class D limit as severe"),
    ("B", BOD): ("max", "BOD_OFTEN_HIGH and its clean-up actions treat readings above the limit as failures"),
    ("B", PH): ("range", "PH_OUT treats readings outside the range as failures"),
}
GAP_STATES = ("not_sampled", "no_table")

TIER_LABELS = {
    1: "Tier 1: dissolved oxygen below the bathing standard in most readings",
    2: "Tier 2: dissolved oxygen below the bathing standard in some readings",
    3: "Tier 3: dissolved oxygen met the standard; BOD or pH did not",
    4: "Tier 4: no exceedance in the readings taken; untested parameters and gaps are not covered",
}


@dataclass(frozen=True)
class Evidence:
    """One grid cell behind a flag. source_page is None when the report has no table."""

    year: int
    festival: str
    phase: str
    parameter: str
    value: float | None  # only for usable numeric readings
    value_as_printed: str | None
    value_state: str
    source_page: int | None
    site_as_printed: str | None

    @property
    def page_ref(self) -> str:
        return f"{self.year} p.{self.source_page}" if self.source_page is not None else f"{self.year} no page (no table in report)"


@dataclass(frozen=True)
class Flag:
    code: str
    site: str
    counts: dict  # the numbers filled into the text, e.g. {"n": 6, "N": 13, "min": 0.0}
    text_en: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class GhatMetrics:
    do_usable: int
    do_fail: int
    do_fail_rate: float | None
    do_severe: int
    do_severe_rate: float | None
    do_zero: int
    do_min: float | None
    bod_usable: int
    bod_fail: int
    bod_fail_rate: float | None
    bod_median: float | None
    bod_max: float | None
    ph_usable: int
    ph_out: int
    coverage_numeric: int
    coverage_expected: int
    coverage: float | None


@dataclass(frozen=True)
class GhatRank:
    rank: int
    site: str
    water_body: str | None
    tier: int
    tier_label: str
    high_risk: bool
    metrics: GhatMetrics
    flags: tuple[Flag, ...]

    @property
    def flag_codes(self) -> tuple[str, ...]:
        return tuple(f.code for f in self.flags)


@dataclass(frozen=True)
class Ranking:
    festivals: tuple[str, ...]
    years: tuple[int, ...]
    phases: tuple[str, ...]
    ghats: tuple[GhatRank, ...] = field(default_factory=tuple)

    def to_frame(self) -> pd.DataFrame:
        """One row per ghat, metrics flattened, for display or CSV export."""
        rows = []
        for g in self.ghats:
            m = g.metrics
            rows.append({
                "rank": g.rank, "site": g.site, "tier": g.tier, "high_risk": g.high_risk,
                "do_fail": m.do_fail, "do_usable": m.do_usable, "do_fail_rate": m.do_fail_rate,
                "do_severe": m.do_severe, "do_zero": m.do_zero, "do_min": m.do_min,
                "bod_fail": m.bod_fail, "bod_usable": m.bod_usable, "bod_fail_rate": m.bod_fail_rate,
                "bod_median": m.bod_median, "ph_out": m.ph_out, "ph_usable": m.ph_usable,
                "coverage": m.coverage, "flags": ", ".join(g.flag_codes),
            })
        return pd.DataFrame(rows)


# ------------------------------------------------------------ scope

def _as_tuple(value, allowed: tuple, name: str) -> tuple:
    if value is None:
        return allowed
    # numbers.Integral covers int and NumPy integer scalars (e.g. numpy.int64 from pandas).
    values = (value,) if isinstance(value, (str, numbers.Integral)) else tuple(value)
    bad = [v for v in values if v not in allowed]
    if bad or not values:
        raise ValueError(f"{name} filter {values!r} invalid; choose from {allowed}")
    return tuple(v for v in allowed if v in values)  # canonical order


def _ordered(df: pd.DataFrame) -> pd.DataFrame:
    """Stable chronological order: year, festival, phase, parameter as in load.*."""
    key = {
        "festival": {v: i for i, v in enumerate(load.FESTIVALS)},
        "phase": {v: i for i, v in enumerate(load.PHASES)},
        "parameter": {v: i for i, v in enumerate(load.PARAMETERS)},
    }
    return df.sort_values(
        ["year", "festival", "phase", "parameter"],
        key=lambda s: s.map(key[s.name]) if s.name in key else s,
        kind="mergesort",
    )


def _evidence(rows: pd.DataFrame) -> tuple[Evidence, ...]:
    out = []
    for _, r in _ordered(rows).iterrows():
        usable = r["result_b"] in (cr.PASS, cr.FAIL)
        out.append(Evidence(
            year=int(r["year"]), festival=r["festival"], phase=r["phase"], parameter=r["parameter"],
            value=float(r["value"]) if usable else None,
            value_as_printed=None if pd.isna(r["value_as_printed"]) else r["value_as_printed"],
            value_state=r["value_state"],
            source_page=None if pd.isna(r["source_page"]) else int(r["source_page"]),
            site_as_printed=None if pd.isna(r["site_as_printed"]) else r["site_as_printed"],
        ))
    return tuple(out)


def _pages(evidence: Iterable[Evidence]) -> str:
    """'2023 p.26, p.60; 2025 p.28'. Pages are grouped by report year."""
    by_year: dict[int, list[str]] = {}
    for e in evidence:
        page = f"p.{e.source_page}" if e.source_page is not None else "no page"
        if page not in by_year.setdefault(e.year, []):
            by_year[e.year].append(page)
    return "; ".join(f"{y} {', '.join(p)}" for y, p in sorted(by_year.items()))


def _fmt(x: float) -> str:
    return f"{x:g}"


def _rate(n: int, d: int) -> float | None:
    return n / d if d else None


# ------------------------------------------------------------ per ghat

def _metrics(cells: pd.DataFrame) -> GhatMetrics:
    usable = cells[cells["result_b"].isin([cr.PASS, cr.FAIL])]
    do = usable[usable["parameter"] == DO]
    bod = usable[usable["parameter"] == BOD]
    ph = usable[usable["parameter"] == PH]
    do_fail = int((do["result_b"] == cr.FAIL).sum())
    do_severe = int((do["result_d"] == cr.FAIL).sum())
    bod_fail = int((bod["result_b"] == cr.FAIL).sum())
    bod_values = bod["value"].astype(float).tolist()
    return GhatMetrics(
        do_usable=len(do), do_fail=do_fail, do_fail_rate=_rate(do_fail, len(do)),
        do_severe=do_severe, do_severe_rate=_rate(do_severe, len(do)),
        do_zero=int((do["value"] == 0).sum()),
        do_min=float(do["value"].min()) if len(do) else None,
        bod_usable=len(bod), bod_fail=bod_fail, bod_fail_rate=_rate(bod_fail, len(bod)),
        bod_median=float(median(bod_values)) if bod_values else None,
        bod_max=max(bod_values) if bod_values else None,
        ph_usable=len(ph), ph_out=int((ph["result_b"] == cr.FAIL).sum()),
        coverage_numeric=len(usable), coverage_expected=len(cells),
        coverage=_rate(len(usable), len(cells)),
    )


def _tier(m: GhatMetrics) -> int:
    if m.do_fail_rate is not None and m.do_fail_rate > OFTEN_SHARE:
        return 1
    if m.do_fail > 0:
        return 2
    if m.bod_fail > 0 or m.ph_out > 0:
        return 3
    return 4


def _gap_text(gaps: pd.DataFrame) -> str:
    """'BOD in 2023 Durga (pre, during, after); Dissolved oxygen, BOD, pH in 2025 Durga (...)'."""
    parts = []
    for (year, festival), season in _ordered(gaps).groupby(["year", "festival"], sort=False):
        by_phase = {ph: tuple(p for p in RANKED_PARAMETERS if p in set(rows["parameter"]))
                    for ph, rows in season.groupby("phase", sort=False)}
        # Merge phases that are missing the same parameters.
        merged: dict[tuple, list[str]] = {}
        for ph in load.PHASES:
            if ph in by_phase:
                merged.setdefault(by_phase[ph], []).append(ph)
        for params, phases in merged.items():
            parts.append(f"{', '.join(params)} in {year} {festival} ({', '.join(phases)})")
    return "; ".join(parts)


def _flags(site: str, cells: pd.DataFrame, site_rows: pd.DataFrame, m: GhatMetrics, table: cr.CriteriaTable) -> list[Flag]:
    """Build flags. `cells` = this ghat's DO/BOD/pH cells in scope; `site_rows` = all its source rows."""
    flags: list[Flag] = []
    do_b, do_d, bod_b = table[("B", DO)], table[("D", DO)], table[("B", BOD)]
    ph_b = table[("B", PH)]
    usable = cells[cells["result_b"].isin([cr.PASS, cr.FAIL])]
    do = usable[usable["parameter"] == DO]

    severe = do[do["result_d"] == cr.FAIL]
    if len(severe):
        ev = _evidence(severe)
        counts = {"n": len(severe), "N": m.do_usable, "min": m.do_min, "pages": _pages(ev)}
        flags.append(Flag("DO_SEVERE", site, counts,
                          f"Dissolved oxygen fell below {do_d.limit_as_printed} {do_d.unit} in {counts['n']} of "
                          f"{counts['N']} readings (lowest {_fmt(m.do_min)}). Pages: {counts['pages']}.", ev))

    zeros = do[do["value"] == 0]
    if len(zeros):
        ev = _evidence(zeros)
        listing = "; ".join(f"{e.year} {e.festival} {e.phase}, p.{e.source_page}" for e in ev)
        flags.append(Flag("DO_ZERO", site, {"n": len(zeros), "list": listing},
                          f"Dissolved oxygen read 0 {do_b.unit} {len(zeros)} times ({listing}).", ev))

    if m.do_fail_rate is not None and m.do_fail_rate > OFTEN_SHARE:
        ev = _evidence(do[do["result_b"] == cr.FAIL])
        flags.append(Flag("DO_OFTEN_LOW", site, {"n": m.do_fail, "N": m.do_usable},
                          f"Dissolved oxygen was below the bathing standard of {do_b.limit_as_printed} {do_b.unit} "
                          f"in {m.do_fail} of {m.do_usable} readings.", ev))

    if m.bod_fail_rate is not None and m.bod_fail_rate > OFTEN_SHARE:
        bod = usable[usable["parameter"] == BOD]
        ev = _evidence(bod[bod["result_b"] == cr.FAIL])
        flags.append(Flag("BOD_OFTEN_HIGH", site, {"n": m.bod_fail, "N": m.bod_usable, "max": m.bod_max},
                          f"BOD was above the bathing limit of {bod_b.limit_as_printed} {bod_b.unit} in "
                          f"{m.bod_fail} of {m.bod_usable} readings (highest {_fmt(m.bod_max)}).", ev))

    ph = usable[usable["parameter"] == PH]
    ph_out = ph[ph["result_b"] == cr.FAIL]
    if len(ph_out):
        ev = _evidence(ph_out)
        values = ", ".join(_fmt(e.value) for e in ev)
        flags.append(Flag("PH_OUT", site, {"n": len(ph_out), "N": m.ph_usable, "values": values},
                          f"pH was outside {ph_b.limit_as_printed.replace('-', '–')} in {len(ph_out)} of "
                          f"{m.ph_usable} readings ({values}).", ev))

    # Any expected cell with no usable number. The PRD names not_sampled and
    # no_table; BDL/ND/unknown-flag/contradictory DO-BOD-pH cells are also gaps.
    gaps = cells[~cells["result_b"].isin([cr.PASS, cr.FAIL])]
    if len(gaps):
        ev = _evidence(gaps)
        state_counts = {s: int(n) for s, n in gaps["value_state"].value_counts().sort_index().items()}
        what = _gap_text(gaps)
        flags.append(Flag("DATA_GAP", site, {"cells": len(gaps), "by_state": state_counts, "what": what},
                          f"No reading for {what}. Missing data is not counted as passing.", ev))

    confidences = sorted(set(site_rows["site_match_confidence"].dropna()))
    if any(c != "high" for c in confidences):
        printed = sorted(set(site_rows["site_as_printed"].dropna()))
        by_festival = {f: sorted(set(site_rows.loc[site_rows["festival"] == f, "site_as_printed"].dropna()))
                       for f in load.FESTIVALS}
        flags.append(Flag("SITE_IDENTITY", site,
                          {"site_match_confidence": confidences, "names_as_printed": printed, "by_festival": by_festival},
                          "Report tables may describe two different places under this name.", ()))
    return flags


# ------------------------------------------------------------ ranking

def _sort_key(site: str, tier: int, m: GhatMetrics) -> tuple:
    """Lower sorts first. Each descending metric is (is_missing, -value): None goes last."""
    def desc(x: float | None) -> tuple:
        return (1, 0.0) if x is None else (0, -x)
    return (tier, *desc(m.do_fail_rate), *desc(m.do_severe_rate), *desc(m.bod_fail_rate), *desc(m.bod_median), site)


def rank_grid(
    grid: pd.DataFrame,
    table: cr.CriteriaTable,
    contradictory: frozenset[tuple] = frozenset(),
    festivals: str | Iterable[str] | None = None,
    years: int | Iterable[int] | None = None,
    phases: str | Iterable[str] | None = None,
) -> Ranking:
    """Rank every site in `grid` (a load.build_expected_grid() frame) within the filter scope.

    `contradictory` is criteria.contradictory_keys(); those cells are never used as numbers.
    Filters default to everything; a single value or an iterable is accepted.
    Raises criteria.CriteriaDirectionError if the table's limit directions
    contradict REQUIRED_DIRECTIONS.
    """
    cr.require_directions(table, REQUIRED_DIRECTIONS)
    festivals = _as_tuple(festivals, load.FESTIVALS, "festival")
    years = _as_tuple(years, tuple(sorted(int(y) for y in grid["year"].unique())), "year")
    phases = _as_tuple(phases, load.PHASES, "phase")

    in_scope = grid["festival"].isin(festivals) & grid["year"].isin(years) & grid["phase"].isin(phases)
    cells = grid[in_scope & grid["parameter"].isin(RANKED_PARAMETERS)]
    cells = cr.compare_frame(cells, table, "B", contradictory).rename(columns={"result": "result_b"})
    cells["result_d"] = cr.compare_frame(cells, table, "D", contradictory)["result"]

    unranked = []
    for site in sorted(grid["site"].unique()):
        site_cells = cells[cells["site"] == site]
        site_rows = grid[(grid["site"] == site) & (grid["value_state"] != "no_table")]
        m = _metrics(site_cells)
        tier = _tier(m)
        flags = sorted(_flags(site, site_cells, site_rows, m, table), key=lambda f: FLAG_ORDER.index(f.code))
        water = sorted(set(site_rows["water_body"].dropna()))
        unranked.append((_sort_key(site, tier, m), site, water, tier, m, tuple(flags)))

    ghats = []
    for rank, (_, site, water, tier, m, flags) in enumerate(sorted(unranked, key=lambda u: u[0]), start=1):
        ghats.append(GhatRank(
            rank=rank, site=site, water_body="; ".join(water) or None, tier=tier, tier_label=TIER_LABELS[tier],
            high_risk=any(f.code in HIGH_RISK_FLAGS for f in flags), metrics=m, flags=flags,
        ))
    return Ranking(festivals=festivals, years=years, phases=phases, ghats=tuple(ghats))


def rank_ghats(
    data: load.LoadedData,
    table: cr.CriteriaTable | None = None,
    festivals: str | Iterable[str] | None = None,
    years: int | Iterable[int] | None = None,
    phases: str | Iterable[str] | None = None,
) -> Ranking:
    """Rank the ghats in loaded data, excluding rows the loader reported as contradictory."""
    table = table if table is not None else cr.load_criteria_table()
    keys = cr.contradictory_keys(data.readings, data.summary.issues)
    return rank_grid(data.grid, table, keys, festivals, years, phases)


if __name__ == "__main__":
    ranking = rank_ghats(load.load_all())
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(ranking.to_frame().to_string(index=False))
    for g in ranking.ghats:
        print(f"\n{g.rank}. {g.site} | {g.tier_label} | high risk: {g.high_risk}")
        for f in g.flags:
            print(f"   {f.code}: {f.text_en}")
