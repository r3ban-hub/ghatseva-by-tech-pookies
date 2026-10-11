"""Export backend outputs as one JSON file for the web UI (web/lib/data/generated/backend.json).

Every figure, flag, note, reading, grid cell, action and date the UI shows comes
from here, built from the same modules as the CLI and tests. The UI only adds
presentation text (labels, Hindi site names, PRD rule descriptions).

Output is deterministic: no clock time, sorted where order is not meaningful.

Usage:
    python -m ghatwatch.export_web                 # writes web/lib/data/generated/backend.json
    python -m ghatwatch.export_web out.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from ghatwatch import brief as br
from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import load
from ghatwatch import orders as od
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "web" / "lib" / "data" / "generated" / "backend.json"
TRACK_PACK_URL = "https://github.com/Laaaaksh/bhopal-impact-lab-2026/tree/main/tracks/02-visarjan-ghat-watch/data"

TASK_GROUP_IDS = {
    "Cleaning & debris": "cleaning", "Aeration": "aeration", "Barricading & nets": "barricading",
    "Water sampling": "sampling", "Site identity check": "identity",
}
FESTIVAL_HI = {"Ganesh": "गणेश", "Durga": "दुर्गा"}
PHASE_EN = {"pre": "before immersion", "during": "during immersion", "after": "one week after"}
PHASE_HI = {"pre": "विसर्जन से पहले", "during": "विसर्जन के दौरान", "after": "एक सप्ताह बाद"}
WARNING_HI = "सिफ़ारिश — MPPCB / CPCB दिशानिर्देशों से पुष्टि करें"

# Plain-words limit wording ("5 mg/l or more"), by limit_type.
TARGET_WORDS = {
    "en": {"min": "{v} or more", "max": "{v} or less", "range": "{a} to {b}"},
    "hi": {"min": "{v} या अधिक", "max": "{v} या कम", "range": "{a} से {b}"},
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frac(n: int, d: int) -> dict:
    return {"n": int(n), "N": int(d)}


def _target(c: cr.Criterion, lang: str) -> str:
    unit = f" {c.unit}" if c.unit else ""
    if c.limit_type == "range":
        a, b = c.limit_as_printed.split("-")
        return TARGET_WORDS[lang]["range"].format(a=a, b=b)
    return TARGET_WORDS[lang][c.limit_type].format(v=f"{c.limit_as_printed}{unit}")


def _ref(year: int, page: int, verified: bool) -> dict:
    return {"year": int(year), "page": int(page), "verified": bool(verified)}


def _refs(evidence: tuple[rk.Evidence, ...], site: str, checked: set[tuple]) -> list[dict]:
    """One ref per (year, page). verified only if EVERY reading cited on that page was spot-checked."""
    pages: dict[tuple[int, int], list[bool]] = {}
    for e in evidence:
        if e.source_page is not None:
            pages.setdefault((e.year, e.source_page), []).append(
                (e.year, e.festival, site, e.phase, e.parameter) in checked)
    return [_ref(y, p, all(flags)) for (y, p), flags in sorted(pages.items())]


def _note_hi(f: rk.Flag, table: cr.CriteriaTable) -> str:
    """Hindi wording for a ranking flag, filled from the flag's own counts and evidence."""
    c = f.counts
    do_b, do_d, bod_b, ph_b = (table[("B", rk.DO)], table[("D", rk.DO)], table[("B", rk.BOD)], table[("B", rk.PH)])
    if f.code == "DO_SEVERE":
        pages = c["pages"].replace("p.", "पृ. ")
        return (f"घुलित ऑक्सीजन {c['N']} में से {c['n']} रीडिंग में {do_d.limit_as_printed} {do_d.unit} से कम रही "
                f"(सबसे कम {c['min']:g})। पृष्ठ: {pages}।")
    if f.code == "DO_ZERO":
        items = "; ".join(f"{e.year} {FESTIVAL_HI[e.festival]}, {PHASE_HI[e.phase]}, पृ. {e.source_page}" for e in f.evidence)
        return f"घुलित ऑक्सीजन {c['n']} बार 0 {do_b.unit} दर्ज हुई ({items})।"
    if f.code == "DO_OFTEN_LOW":
        return (f"घुलित ऑक्सीजन {c['N']} में से {c['n']} रीडिंग में स्नान मानक {do_b.limit_as_printed} {do_b.unit} "
                f"से कम रही।")
    if f.code == "BOD_OFTEN_HIGH":
        return (f"BOD {c['N']} में से {c['n']} रीडिंग में स्नान सीमा {bod_b.limit_as_printed} {bod_b.unit} से अधिक रहा "
                f"(सबसे अधिक {c['max']:g})।")
    if f.code == "PH_OUT":
        return f"pH {c['N']} में से {c['n']} रीडिंग में {ph_b.limit_as_printed.replace('-', '–')} से बाहर रहा ({c['values']})।"
    if f.code == "DATA_GAP":
        # Same grouping as ranking._gap_text: per season, phases that miss the same parameters.
        parts = []
        festival_order = {fe: i for i, fe in enumerate(load.FESTIVALS)}
        seasons = sorted({(e.year, e.festival) for e in f.evidence}, key=lambda s: (s[0], festival_order[s[1]]))
        for year, fest in seasons:
            by_phase = {}
            for ph in load.PHASES:
                params = tuple(p for p in rk.RANKED_PARAMETERS
                               if any(e.year == year and e.festival == fest and e.phase == ph and e.parameter == p
                                      for e in f.evidence))
                if params:
                    by_phase[ph] = params
            merged: dict[tuple, list[str]] = {}
            for ph, params in by_phase.items():
                merged.setdefault(params, []).append(PHASE_HI[ph])
            for params, phases in merged.items():
                names = ", ".join("DO" if p == rk.DO else p for p in params)
                parts.append(f"{names}: {year} {FESTIVAL_HI[fest]} ({', '.join(phases)})")
        return f"इन रीडिंग का रिकॉर्ड नहीं: {'; '.join(parts)}। कमी को पास नहीं माना गया।"
    if f.code == "SITE_IDENTITY":
        return "रिपोर्ट की तालिकाओं में इस नाम से दो अलग जगहें हो सकती हैं।"
    raise ValueError(f"no Hindi wording for flag {f.code}")


def _absent_detail(ev: pd.DataFrame) -> dict:
    """Describe the absent tables from the evidence (whole seasons, then single parameters)."""
    nt = ev[ev["value_state"] == "no_table"]
    whole, partial = [], {}
    for (site, year, fest), cells in nt.groupby(["site", "year", "festival"], sort=False):
        if len(cells) == len(load.PHASES) * len(load.PARAMETERS):
            whole.append((site, int(year), fest))
        else:
            for p in cells["parameter"].unique():
                partial.setdefault((p, int(year), fest), set()).add(site)
    en_parts = [f"no {fest} {year} table for {site}" for site, year, fest in whole]
    hi_parts = [f"{site} की {FESTIVAL_HI[fest]} {year} तालिका नहीं" for site, year, fest in whole]
    for (p, year, fest), sites in sorted(partial.items(), key=lambda kv: (kv[0][1], kv[0][2])):
        en_parts.append(f"no {p.lower()} rows in {fest} {year} ({len(sites)} ghats)")
        hi_parts.append(f"{FESTIVAL_HI[fest]} {year} में {p} की पंक्तियाँ नहीं ({len(sites)} घाट)")
    return {
        "en": f"{len(nt)} expected cells have no table in the reports: {'; '.join(en_parts)}. These cells are missing, not passing.",
        "hi": f"{len(nt)} अपेक्षित सेल की रिपोर्ट में तालिका नहीं: {'; '.join(hi_parts)}। ये खाली हैं, पास नहीं।",
    }


def build_export(generated_on: date | str | None = None) -> dict:
    data = load.load_all()
    table = cr.load_criteria_table()
    ranking = rk.rank_ghats(data, table)
    plan = pl.plan_actions(ranking)
    orders = od.work_orders(ranking, plan, table=table, readings=data.readings)  # validates guarantees
    evidence = evm.build_evidence(data, table)
    spot = evm.load_spot_checks()
    checked = set(evm.spot_checked_keys(spot))
    generated = pl.as_event_date(generated_on) if generated_on is not None else plan.start

    usable = evidence[evidence["class_b_result"].isin([cr.PASS, cr.FAIL])]

    def fails(param: str, rows: pd.DataFrame = usable, column: str = "class_b_result") -> dict:
        r = rows[rows["parameter"] == param]
        return _frac((r[column] == cr.FAIL).sum(), len(r))

    durga = usable[usable["festival"] == "Durga"]
    pre = usable[usable["phase"] == "pre"]
    zero_flags = [(g.site, f) for g in ranking.ghats for f in g.flags if f.code == "DO_ZERO"]

    headlines = {
        "doBelow5": fails(rk.DO), "doBelow4": fails(rk.DO, column="class_d_result"),
        "doZero": {"count": sum(g.metrics.do_zero for g in ranking.ghats),
                   "sites": [site for site, _ in zero_flags],
                   "refs": [r for site, f in zero_flags for r in _refs(f.evidence, site, checked)]},
        "bodAbove3": fails(rk.BOD), "phOut": fails(rk.PH),
        "durgaDoBelow5": fails(rk.DO, durga), "durgaBodAbove3": fails(rk.BOD, durga),
        "highRisk": _frac(sum(g.high_risk for g in ranking.ghats), len(ranking.ghats)),
        "preBodAbove3": fails(rk.BOD, pre),
    }

    sites = []
    for g in ranking.ghats:
        m = g.metrics
        site_rows = data.readings[data.readings["site"] == g.site]
        sites.append({
            "csvSiteName": g.site, "rank": g.rank, "tier": g.tier, "highRisk": g.high_risk,
            "waterBody": g.water_body,
            "identityConfidence": "medium" if "SITE_IDENTITY" in g.flag_codes else "high",
            "confidenceValues": sorted(set(site_rows["site_match_confidence"])),
            "doBelow5": _frac(m.do_fail, m.do_usable), "doBelow4": m.do_severe,
            "doMin": "—" if m.do_min is None else f"{m.do_min:g}", "doZeroCount": m.do_zero,
            "bodAbove3": _frac(m.bod_fail, m.bod_usable), "phOutOfRange": _frac(m.ph_out, m.ph_usable),
            "expectedPerParameter": m.coverage_expected // len(rk.RANKED_PARAMETERS),
            "coverage": _frac(m.coverage_numeric, m.coverage_expected),
            "flags": list(g.flag_codes),
            "notes": [{"flag": f.code, "en": f.text_en, "hi": _note_hi(f, table),
                       "refs": _refs(f.evidence, g.site, checked)} for f in g.flags],
        })

    # Readings and the expected grid, straight from the evidence table.
    seasons_with_rows = {(s, int(y), f) for s, y, f in zip(data.readings["site"], data.readings["year"], data.readings["festival"])}
    # Line in the source CSV: readings keep the file's 0-based data-row index; +2 for 1-based and the header.
    csv_line = {(int(r.year), r.festival, r.site, r.phase, r.parameter): int(i) + 2
                for i, r in zip(data.readings.index, data.readings.itertuples(index=False))}
    cells = []
    for r in evidence.itertuples(index=False):
        has_row = r.value_state != "no_table"
        cell = {"year": int(r.year), "festival": r.festival, "site": r.site, "phase": r.phase,
                "parameter": r.parameter, "state": r.value_state}
        if has_row:
            cell["reading"] = {
                "csvLine": csv_line[(int(r.year), r.festival, r.site, r.phase, r.parameter)],
                "waterBody": r.water_body, "value": None if r.value == "" else float(r.value),
                "valueAsPrinted": r.value_as_printed, "unitAssumed": r.unit, "flag": r.source_flag,
                "parameterAsPrinted": r.parameter_as_printed, "siteAsPrinted": r.site_as_printed,
                "siteMatchConfidence": r.site_match_confidence,
                "page": None if r.source_page == "" else int(r.source_page),
                "spotChecked": str(r.page_verified).startswith("spot-checked"),
                "classB": r.class_b_result, "contradictory": r.contradictory == "yes",
            }
        else:
            cell["missingReason"] = ("parameter_absent" if (r.site, int(r.year), r.festival) in seasons_with_rows
                                     else "season_table_absent")
        cells.append(cell)

    actions = []
    for o in orders:
        for t in o.tasks:
            a = t.action
            actions.append({
                "order": a.order, "site": a.site, "id": "rule-" + "-".join(a.rule_ids).lower(),
                "ruleIds": list(a.rule_ids), "triggers": list(a.triggers),
                "trigger": "ALL" if pl.ALL_GHATS in a.triggers else a.triggers[0],
                "taskGroup": TASK_GROUP_IDS[a.task_group], "en": a.action_en, "hi": a.action_hi,
                "hiReviewed": a.hi_reviewed, "window": a.when.replace(" to ", " → "),
                "start": a.start.isoformat(), "end": a.end.isoformat(),
                "datesEn": pl.window_label(a.start, a.end), "datesHi": br._window(a.start, a.end, "hi"),
                "source": a.source, "verified": a.verified, "warning": a.warning,
                "responsible": t.responsible, "responsibleAssigned": t.responsible_assigned,
                "responsibleIsAssumption": t.responsible_is_assumption, "reportTo": t.report_to,
            })

    criteria_out = []
    for (cls, param), role in (((("B", rk.DO)), "standard"), (("B", rk.BOD), "standard"), (("B", rk.PH), "standard"),
                               (("D", rk.DO), "severity_line")):
        c = table[(cls, param)]
        criteria_out.append({"parameter": param, "cpcbClass": cls, "limitType": c.limit_type,
                             "limit": c.limit_as_printed, "unit": c.unit or None, "role": role,
                             "ruleEn": _target(c, "en"), "ruleHi": _target(c, "hi")})

    targets = [{"parameter": t.parameter, "en": _target(table[("B", t.parameter)], "en"),
                "hi": _target(table[("B", t.parameter)], "hi"), "inCurrentData": t.tested_in_data}
               for t in od.class_b_targets(table)]

    pre_bod = headlines["preBodAbove3"]
    return {
        "generator": {
            "module": "ghatwatch.export_web",
            "generatedOn": generated.isoformat(),
            "readingsFile": load.READINGS_FILE,
            "readingsSha256": _sha256(load.DATA_DIR / load.READINGS_FILE),
            "criteriaSha256": _sha256(load.DATA_DIR / load.CRITERIA_FILE),
            "trackPackUrl": TRACK_PACK_URL,
        },
        "meta": {
            "visarjanDate": plan.event_date.isoformat(), "planStart": plan.start.isoformat(),
            "planEnd": plan.end.isoformat(), "d7Date": plan.end.isoformat(), "ghatCount": len(ranking.ghats),
            "criteria": criteria_out,
            "coliform": {"en": _target(table[("B", "Total coliform")], "en"), "hi": _target(table[("B", "Total coliform")], "hi")},
            "coverage": {"expectedCells": data.summary.expected_cells, "rowsInFile": len(data.readings),
                         "absentCells": data.summary.no_table_cells, "absentDetail": _absent_detail(evidence)},
            "spotCheck": {"readings": len(spot), "pages": int(len(spot[["year", "source_page"]].drop_duplicates())),
                          "checkedOn": sorted(set(spot["checked_on"]))},
            "sourcePdfs": {str(y): f for y, (f, _) in evm.SOURCE_REPORTS.items()},
            "interimNote": {
                "en": (f"BOD was already above {table[('B', rk.BOD)].limit_as_printed} mg/l in {pre_bod['n']} of "
                       f"{pre_bod['N']} pre-immersion readings (2023–2025), so full Class B by "
                       f"{plan.end.day} Oct is unlikely at most ghats. The interim target does not replace Class B."),
                "hi": (f"2023–2025 में विसर्जन-पूर्व {pre_bod['N']} में से {pre_bod['n']} रीडिंग में BOD पहले ही "
                       f"{table[('B', rk.BOD)].limit_as_printed} mg/l से अधिक था, इसलिए अधिकांश घाटों पर "
                       f"{plan.end.day} अक्टूबर तक पूर्ण क्लास B की संभावना कम है। अंतरिम लक्ष्य क्लास B का स्थान नहीं लेता।"),
            },
            "warningEn": pl.UNVERIFIED_WARNING, "warningHi": WARNING_HI,
        },
        "headlines": headlines,
        "sites": sites,
        "cells": cells,
        "actions": actions,
        "targets": targets,
        "planWindows": [{"start": w.start.isoformat(), "end": w.end.isoformat(),
                         "datesEn": w.window, "datesHi": br._window(w.start, w.end, "hi")} for w in plan.overview],
    }


def write_export(path: Path | str = DEFAULT_OUT, generated_on: date | str | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(build_export(generated_on), ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


if __name__ == "__main__":
    out = write_export(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
