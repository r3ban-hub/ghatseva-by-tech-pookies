"""Officer brief in English and Hindi, filled from code-generated data (PRD §9).

Templates in templates/brief_{en,hi}.md hold fixed prose only. Every number,
rank, flag, date and reason is inserted here from the Ranking, Plan, criteria
table and evidence table. The few short phrases below are per-language
wording for those values, not data.

The Hindi wording has not been reviewed by a fluent reader; the brief says so
until `hindi_reviewed=True` is passed.

Usage:
    python -m ghatwatch.brief en|hi      # print a brief
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from string import Template

import pandas as pd

from ghatwatch import criteria as cr
from ghatwatch import load
from ghatwatch import orders as od
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
LANGUAGES = ("en", "hi")
HINDI_REVIEW_NOTICE = "**अस्थायी अनुवाद — धाराप्रवाह समीक्षा आवश्यक (Provisional translation — requires fluent review).**"
DAGGER = "†"

MONTHS_HI = ("जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर")

# Wording per language. Values are filled in by code.
WORDS = {
    "en": {
        "festival": {"Ganesh": "Ganesh", "Durga": "Durga"},
        "phase": {"pre": "pre-immersion", "during": "during", "after": "1 week after"},
        "all_phases": "all phases",
        "and": " and ",
        "head": "Tier {tier}{risk}",
        "high_risk": ", high risk",
        "end": ".",
        "do_none": "no usable DO reading",
        "do_fail": "DO {fail} in {n}/{N}, lowest {min} ({year} {festival} {phase}, p.{page}{mark})",
        "legend": "n/N = readings outside the limit / usable readings. ✓ = cited reading matched the PDF page in a partial manual check.",
        "legend_plain": "n/N = readings outside the limit / usable readings.",
        "page_check": ("Report pages come from the data file. A partial manual check matched {n} readings on {p} pages "
                       "with the PDFs; all other page references are not yet checked."),
        "page_check_none": "Report pages come from the data file and have not been checked against the PDFs.",
        "do_ok": "DO {ok} in all {N}",
        "bod": "BOD {fail} in {n}/{N}",
        "bod_none": "no usable BOD reading",
        "ph": "pH {fail} in {n}/{N}",
        "gap_note": "data gaps",
        "identity_note": "site identity uncertain",
        "bod_summary": "BOD was {fail} in most readings at {k} of {n} ghats",
        "bod_pre": ", including {n} of {N} pre-immersion readings",
        "all_ghats": "All {n} ghats",
        "all_ghats_short": "all {n} ghats",
        "group": {"Cleaning & debris": "offerings collection and clean-up", "Aeration": "aeration and DO checks",
                  "Barricading & nets": "barricades, nets or booms", "Water sampling": "sampling",
                  "Site identity check": "site identity field check"},
        "trigger": {"DATA_GAP": "priority sampling", "PH_OUT": "pH test", "DO_SEVERE": "aerators, daily DO checks",
                    "DO_ZERO": "aerators, daily DO checks", "DO_OFTEN_LOW": "aeration during and after immersion"},
        "d7_sampling": "one-week-after sampling",
        "none": "None in this scope.",
        "not_tested": " (not tested in the supplied data)",
        "parameter": {"Dissolved oxygen": "DO"},
        "coliform_note": "No {names} readings in the supplied data, so no ghat can be confirmed as meeting Class B.",
        "coliform_all": "All Class B parameters are in the supplied data.",
        "gaps": "Missing DO, BOD or pH readings, not counted as passing: {items}.",
        "gaps_none": "No DO, BOD or pH reading is missing in this scope.",
        "gap_item": "#{rank} ({n})",
        "identity": "#{rank}: report tables may describe two different places under this name; field check {window}.",
        "identity_nocheck": "#{rank}: report tables may describe two different places under this name.",
        "identity_none": "No site-identity concern in the data.",
        "resources_none": "Not estimated: no sourced rates are available yet.",
        "warning": DAGGER + " " + pl.UNVERIFIED_WARNING + " These are team recommendations, not official instructions.",
    },
    "hi": {
        "festival": {"Ganesh": "गणेश", "Durga": "दुर्गा"},
        "phase": {"pre": "विसर्जन से पहले", "during": "विसर्जन के दौरान", "after": "एक सप्ताह बाद"},
        "all_phases": "सभी चरण",
        "and": " और ",
        "head": "श्रेणी {tier}{risk}",
        "high_risk": ", उच्च जोखिम",
        "end": "।",
        "do_none": "DO की उपयोगी रीडिंग नहीं",
        "do_fail": "DO {fail}: {n}/{N}, सबसे कम {min} ({year} {festival}, {phase}, पृ. {page}{mark})",
        "legend": "n/N = सीमा से बाहर रीडिंग / उपयोगी रीडिंग। ✓ = उद्धृत रीडिंग आंशिक हाथ-जाँच में PDF पृष्ठ से मेल खाई।",
        "legend_plain": "n/N = सीमा से बाहर रीडिंग / उपयोगी रीडिंग।",
        "page_check": ("रिपोर्ट के पृष्ठ डेटा फ़ाइल से लिए गए हैं। आंशिक हाथ-जाँच में {p} पृष्ठों की {n} रीडिंग PDF से मेल खाईं; "
                       "बाकी पृष्ठ संदर्भ अभी जाँचे नहीं गए हैं।"),
        "page_check_none": "रिपोर्ट के पृष्ठ डेटा फ़ाइल से लिए गए हैं; PDF से इनकी जाँच अभी नहीं हुई है।",
        "do_ok": "सभी {N} में DO {ok}",
        "bod": "BOD {fail}: {n}/{N}",
        "bod_none": "BOD की उपयोगी रीडिंग नहीं",
        "ph": "pH {fail}: {n}/{N}",
        "gap_note": "डेटा में कमी",
        "identity_note": "स्थल की पहचान अनिश्चित",
        "bod_summary": "{n} में से {k} घाटों पर ज़्यादातर रीडिंग में BOD {fail} था",
        "bod_pre": ", विसर्जन से पहले की {N} में से {n} रीडिंग भी शामिल",
        "all_ghats": "सभी {n} घाट",
        "all_ghats_short": "सभी {n} घाट",
        "group": {"Cleaning & debris": "पूजा सामग्री संग्रह और सफ़ाई", "Aeration": "एरेशन और DO जाँच",
                  "Barricading & nets": "बैरिकेड, जाल या बूम", "Water sampling": "नमूने",
                  "Site identity check": "स्थल की पहचान की जाँच"},
        "trigger": {"DATA_GAP": "प्राथमिकता से नमूने", "PH_OUT": "pH जाँच", "DO_SEVERE": "एरेटर, रोज़ DO जाँच",
                    "DO_ZERO": "एरेटर, रोज़ DO जाँच", "DO_OFTEN_LOW": "विसर्जन के दौरान और बाद एरेशन"},
        "d7_sampling": "एक सप्ताह बाद के नमूने",
        "none": "इस दायरे में कोई नहीं।",
        "not_tested": " (दिए गए डेटा में जाँच नहीं हुई)",
        "parameter": {"Dissolved oxygen": "DO", "Total coliform": "टोटल कोलीफॉर्म"},
        "coliform_note": "दिए गए डेटा में {names} की कोई रीडिंग नहीं, इसलिए किसी घाट को श्रेणी B पर खरा नहीं कहा जा सकता।",
        "coliform_all": "श्रेणी B के सभी मानक दिए गए डेटा में हैं।",
        "gaps": "DO, BOD या pH की रीडिंग उपलब्ध नहीं, इन्हें पास नहीं माना गया: {items}।",
        "gaps_none": "इस दायरे में DO, BOD या pH की कोई रीडिंग कम नहीं है।",
        "gap_item": "#{rank} ({n})",
        "identity": "#{rank}: रिपोर्ट की तालिकाओं में इस नाम से दो अलग जगहें हो सकती हैं; मौके पर जाँच {window}।",
        "identity_nocheck": "#{rank}: रिपोर्ट की तालिकाओं में इस नाम से दो अलग जगहें हो सकती हैं।",
        "identity_none": "डेटा में स्थल की पहचान को लेकर कोई संदेह नहीं।",
        "resources_none": "अनुमान नहीं लगाया गया: अभी स्रोत-आधारित दरें उपलब्ध नहीं हैं।",
        "warning": (DAGGER + " सिफ़ारिश — MPPCB / CPCB दिशानिर्देशों से पुष्टि करें (" + pl.UNVERIFIED_WARNING + ") "
                    "ये टीम की सिफ़ारिशें हैं, आधिकारिक निर्देश नहीं।"),
    },
}


# Comparison wording per limit_type, so the text follows the criteria CSV.
# "fail": a reading outside the limit; "ok": within it; "fail_words": prose form.
COMPARE = {
    "en": {
        "fail": {"min": "<{v}", "max": ">{v}", "range": "outside {v}"},
        "ok": {"min": "≥{v}", "max": "≤{v}", "range": "within {v}"},
        "fail_words": {"min": "below {v}", "max": "above {v}", "range": "outside {v}"},
    },
    "hi": {
        "fail": {"min": "{v} से कम", "max": "{v} से अधिक", "range": "{v} से बाहर"},
        "ok": {"min": "{v} या अधिक", "max": "{v} या कम", "range": "{v} के भीतर"},
        "fail_words": {"min": "{v} से कम", "max": "{v} से अधिक", "range": "{v} से बाहर"},
    },
}


def compare_phrase(criterion: cr.Criterion, lang: str, kind: str, unit: bool = True) -> str:
    """Wording for a reading outside ("fail", "fail_words") or within ("ok") a criterion's limit."""
    v = criterion.limit_as_printed.replace("-", "–") + (f" {criterion.unit}" if unit and criterion.unit else "")
    return COMPARE[lang][kind][criterion.limit_type].format(v=v)


# ------------------------------------------------------------ formatting

def _fmt(x: float) -> str:
    return f"{x:g}"


def _date(d: date, lang: str, year: bool = True) -> str:
    month = d.strftime("%b") if lang == "en" else MONTHS_HI[d.month - 1]
    return f"{d.day} {month}" + (f" {d.year}" if year else "")


def _window(start: date, end: date, lang: str) -> str:
    if lang == "en":
        return pl.window_label(start, end)
    if start == end:
        return _date(start, lang, year=False)
    if start.month == end.month:
        return f"{start.day}–{end.day} {MONTHS_HI[end.month - 1]}"
    return f"{_date(start, lang, False)}–{_date(end, lang, False)}"


def _join(items: list[str], lang: str) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + WORDS[lang]["and"] + items[-1]


def _task_label(action: pl.PlannedAction, d7: date, lang: str) -> str:
    w = WORDS[lang]
    if action.triggers == (pl.ALL_GHATS,) and action.task_group == "Water sampling" and action.start == d7:
        return w["d7_sampling"]
    for t in action.triggers:
        if t in w["trigger"]:
            return w["trigger"][t]
    return w["group"].get(action.task_group, action.task_group)


def word_count(text: str) -> int:
    """All whitespace-separated tokens except bare Markdown symbols (numbers, dates and page refs count)."""
    return len(re.findall(r"[^\s#*|\-–—†]+", text))


def prose_word_count(text: str) -> int:
    """Tokens containing a letter (Latin or Devanagari); numbers, dates and n/N counts excluded."""
    return sum(1 for t in text.split() if re.search(r"[A-Za-zऀ-ॿ]", t))


# ------------------------------------------------------------ sections

def _scope_evidence(evidence: pd.DataFrame, ranking: rk.Ranking) -> pd.DataFrame:
    return evidence[evidence["festival"].isin(ranking.festivals) & evidence["year"].astype(int).isin(ranking.years)
                    & evidence["phase"].isin(ranking.phases)]


def _lowest_do(ev: pd.DataFrame, g: rk.GhatRank) -> pd.Series:
    """The lowest usable DO reading for a ghat, from the evidence table (first if tied)."""
    do = ev[(ev["site"] == g.site) & (ev["parameter"] == rk.DO) & ev["class_b_result"].isin([cr.PASS, cr.FAIL])]
    values = do["value"].astype(float)
    row = do.loc[values.idxmin()]
    if float(row["value"]) != g.metrics.do_min:
        raise ValueError(f"{g.site}: evidence minimum DO {row['value']} differs from ranking {g.metrics.do_min}")
    return row


SPOT_MARK = " ✓"


def _spot_checked(row: pd.Series) -> bool:
    """True only for a reading the evidence marks as matched in the manual spot check."""
    return str(row["page_verified"]).startswith("spot-checked")


def _page_check(evidence: pd.DataFrame, lang: str) -> str:
    """Disclosure of the partial manual PDF check, counted from the evidence table."""
    checked = evidence[evidence["page_verified"].astype(str).str.startswith("spot-checked")]
    if checked.empty:
        return WORDS[lang]["page_check_none"]
    pages = checked[["year", "source_page"]].drop_duplicates()
    return WORDS[lang]["page_check"].format(n=len(checked), p=len(pages))


def _ranked(ranking: rk.Ranking, ev: pd.DataFrame, table: cr.CriteriaTable, lang: str) -> str:
    w = WORDS[lang]
    do_b, bod_b, ph_b = table[("B", rk.DO)], table[("B", rk.BOD)], table[("B", rk.PH)]
    lines = []
    for g in ranking.ghats:
        m = g.metrics
        if m.do_usable == 0:
            do = w["do_none"]
        elif m.do_fail:
            low = _lowest_do(ev, g)
            do = w["do_fail"].format(
                fail=compare_phrase(do_b, lang, "fail"), n=m.do_fail, N=m.do_usable, min=_fmt(m.do_min),
                year=low["year"], festival=w["festival"][low["festival"]], phase=w["phase"][low["phase"]],
                page=low["source_page"], mark=SPOT_MARK if _spot_checked(low) else "",
            )
        else:
            do = w["do_ok"].format(ok=compare_phrase(do_b, lang, "ok"), N=m.do_usable)
        parts = [do, w["bod"].format(fail=compare_phrase(bod_b, lang, "fail", unit=False), n=m.bod_fail,
                                     N=m.bod_usable)
                 if m.bod_usable else w["bod_none"]]
        if m.ph_out:
            parts.append(w["ph"].format(fail=compare_phrase(ph_b, lang, "fail"), n=m.ph_out, N=m.ph_usable))
        if "DATA_GAP" in g.flag_codes:
            parts.append(w["gap_note"])
        if "SITE_IDENTITY" in g.flag_codes:
            parts.append(w["identity_note"])
        head = w["head"].format(tier=g.tier, risk=w["high_risk"] if g.high_risk else "")
        lines.append(f"{g.rank}. **{g.site}** — {head}: {'; '.join(parts)}{w['end']}")
    return "\n".join(lines)


def _bod_summary(ranking: rk.Ranking, ev: pd.DataFrame, table: cr.CriteriaTable, lang: str) -> str:
    w = WORDS[lang]
    k = sum("BOD_OFTEN_HIGH" in g.flag_codes for g in ranking.ghats)
    fail = compare_phrase(table[("B", rk.BOD)], lang, "fail_words")
    text = w["bod_summary"].format(fail=fail, k=k, n=len(ranking.ghats))
    pre = ev[(ev["parameter"] == rk.BOD) & (ev["phase"] == "pre") & ev["class_b_result"].isin([cr.PASS, cr.FAIL])]
    if len(pre):
        text += w["bod_pre"].format(n=int((pre["class_b_result"] == cr.FAIL).sum()), N=len(pre))
    return text + w["end"]


def _item(a: pl.PlannedAction, plan: pl.Plan, lang: str) -> str:
    return f"{_task_label(a, plan.end, lang)} {_window(a.start, a.end, lang)}{'' if a.verified else DAGGER}"


def _pre_actions(ranking: rk.Ranking, plan: pl.Plan, lang: str) -> str:
    """Tasks starting before D, by ghat. Tasks identical at every ghat go on one line."""
    w = WORDS[lang]
    by_site = {g.site: [a for a in plan.for_site(g.site) if a.start < plan.event_date] for g in ranking.ghats}
    keys = {g: {(_task_label(a, plan.end, lang), a.start, a.end) for a in tasks} for g, tasks in by_site.items()}
    shared = set.intersection(*keys.values()) if keys else set()
    lines = []
    if shared and len(by_site) > 1:
        first = next(iter(by_site.values()))
        common = [a for a in first if (_task_label(a, plan.end, lang), a.start, a.end) in shared]
        lines.append(f"- **{w['all_ghats'].format(n=len(by_site))}:** " + "; ".join(_item(a, plan, lang) for a in common))
    else:
        shared = set()
    for g in ranking.ghats:
        own = [a for a in by_site[g.site] if (_task_label(a, plan.end, lang), a.start, a.end) not in shared]
        if own:
            lines.append(f"- **#{g.rank} {g.site}:** " + "; ".join(_item(a, plan, lang) for a in own))
    return "\n".join(lines) or w["none"]


def _post_actions(ranking: rk.Ranking, plan: pl.Plan, lang: str) -> str:
    """Tasks running after D, grouped by task and dates; ghats named by rank."""
    groups: dict[tuple, list[pl.PlannedAction]] = {}
    for a in sorted(plan.actions, key=lambda a: (a.start, a.end, a.order)):
        if a.end > plan.event_date:
            groups.setdefault((_task_label(a, plan.end, lang), a.start, a.end), []).append(a)
    ranks = {g.site: g.rank for g in ranking.ghats}
    lines = []
    for (label, start, end), actions in groups.items():
        sites = sorted({ranks[a.site] for a in actions})
        where = (WORDS[lang]["all_ghats_short"].format(n=len(ranks)) if len(sites) == len(ranks)
                 else ", ".join(f"#{r}" for r in sites))
        mark = "" if all(a.verified for a in actions) else DAGGER
        lines.append(f"- {label} {_window(start, end, lang)}: {where}{mark}")
    return "\n".join(lines) or WORDS[lang]["none"]


def _targets(table: cr.CriteriaTable, lang: str) -> tuple[str, list[str]]:
    w = WORDS[lang]
    items, untested = [], []
    for t in od.class_b_targets(table):
        name = w["parameter"].get(t.parameter, t.parameter)
        items.append(f"{name} {t.target}" + ("" if t.tested_in_data else w["not_tested"]))
        if not t.tested_in_data:
            untested.append(name if lang == "hi" else name.lower())
    return "; ".join(items), untested


def _gaps(ranking: rk.Ranking, lang: str) -> str:
    w = WORDS[lang]
    items = [w["gap_item"].format(rank=g.rank, n=f.counts["cells"])
             for g in ranking.ghats for f in g.flags if f.code == "DATA_GAP"]
    return w["gaps"].format(items=", ".join(items)) if items else w["gaps_none"]


def _identity(ranking: rk.Ranking, plan: pl.Plan, lang: str) -> str:
    w = WORDS[lang]
    out = []
    for g in ranking.ghats:
        if "SITE_IDENTITY" in g.flag_codes:
            check = next((a for a in plan.for_site(g.site) if a.task_group == "Site identity check"), None)
            out.append(w["identity"].format(rank=g.rank, window=_window(check.start, check.end, lang))
                       if check else w["identity_nocheck"].format(rank=g.rank))
    return " ".join(out) or w["identity_none"]


def _scope(ranking: rk.Ranking, lang: str) -> str:
    w = WORDS[lang]
    festivals = _join([w["festival"][f] for f in ranking.festivals], lang)
    years = f"{ranking.years[0]}–{ranking.years[-1]}" if len(ranking.years) > 1 else str(ranking.years[0])
    phases = w["all_phases"] if ranking.phases == load.PHASES else ", ".join(w["phase"][p] for p in ranking.phases)
    return f"{festivals} {years}, {phases}"


# ------------------------------------------------------------ public API

def brief_values(
    ranking: rk.Ranking,
    plan: pl.Plan,
    evidence: pd.DataFrame,
    table: cr.CriteriaTable | None = None,
    lang: str = "en",
    generated_on: date | str | None = None,
    resources: str | None = None,
    hindi_reviewed: bool = False,
) -> dict[str, str]:
    """Every value inserted into the template, keyed by placeholder name.

    evidence: evidence.build_evidence() output. generated_on defaults to today.
    resources: text from a future estimator; None prints "Not estimated".
    """
    if lang not in LANGUAGES:
        raise ValueError(f"language {lang!r} not supported; use one of {LANGUAGES}")
    table = table if table is not None else cr.load_criteria_table()
    w = WORDS[lang]
    try:
        generated = pl.as_event_date(generated_on) if generated_on is not None else date.today()
    except ValueError as exc:
        raise ValueError(f"generation date {generated_on!r} is not a valid date (use YYYY-MM-DD)") from exc
    ev = _scope_evidence(evidence, ranking)
    targets, untested = _targets(table, lang)
    return {
        "event_date": _date(plan.event_date, lang),
        "event_short": _date(plan.event_date, lang, year=False),
        "event_year": str(plan.event_date.year),
        "d7_date": _date(plan.end, lang),
        "d7_short": _date(plan.end, lang, year=False),
        "generated_on": _date(generated, lang),
        "scope": _scope(ranking, lang),
        "n_ghats": str(len(ranking.ghats)),
        "class_b": targets,
        "targets": targets,
        "ranked": _ranked(ranking, ev, table, lang),
        "legend": w["legend"] if SPOT_MARK in _ranked(ranking, ev, table, lang) else w["legend_plain"],
        "page_check": _page_check(evidence, lang),
        "bod_summary": _bod_summary(ranking, ev, table, lang),
        "pre_actions": _pre_actions(ranking, plan, lang),
        "post_actions": _post_actions(ranking, plan, lang),
        "resources": resources if resources else w["resources_none"],
        "coliform_note": w["coliform_note"].format(names=_join(untested, lang)) if untested else w["coliform_all"],
        "gaps": _gaps(ranking, lang),
        "identity": _identity(ranking, plan, lang),
        "warning_note": w["warning"] if any(not a.verified for a in plan.actions) else "",
        "review_notice": "" if (lang == "en" or hindi_reviewed) else HINDI_REVIEW_NOTICE,
    }


def load_template(lang: str) -> Template:
    path = TEMPLATE_DIR / f"brief_{lang}.md"
    if not path.is_file():
        raise FileNotFoundError(f"brief template missing: {path}")
    return Template(path.read_text(encoding="utf-8"))


def build_brief(
    ranking: rk.Ranking,
    plan: pl.Plan,
    evidence: pd.DataFrame,
    table: cr.CriteriaTable | None = None,
    lang: str = "en",
    generated_on: date | str | None = None,
    resources: str | None = None,
    hindi_reviewed: bool = False,
) -> str:
    """Render the brief as Markdown. Raises if the template has an unknown placeholder."""
    values = brief_values(ranking, plan, evidence, table, lang, generated_on, resources, hindi_reviewed)
    text = load_template(lang).substitute(values)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def build_briefs(
    ranking: rk.Ranking,
    plan: pl.Plan,
    evidence: pd.DataFrame,
    table: cr.CriteriaTable | None = None,
    generated_on: date | str | None = None,
    resources: str | None = None,
    hindi_reviewed: bool = False,
) -> dict[str, str]:
    """{"en": ..., "hi": ...}"""
    return {lang: build_brief(ranking, plan, evidence, table, lang, generated_on, resources, hindi_reviewed)
            for lang in LANGUAGES}


if __name__ == "__main__":
    import sys

    from ghatwatch import evidence as evm

    data = load.load_all()
    ranking = rk.rank_ghats(data)
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    text = build_brief(ranking, pl.plan_actions(ranking), evm.build_evidence(data), lang=lang)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    print(f"[{word_count(text)} words]")
