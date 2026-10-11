"""Tests for ghatwatch.brief: templates, code-filled figures, disclosures, wording."""

import re
from dataclasses import replace
from datetime import date

import pytest

from ghatwatch import brief as br
from ghatwatch import criteria as cr
from ghatwatch import evidence as evm
from ghatwatch import load
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

GEN = "2026-10-11"


@pytest.fixture(scope="module")
def data():
    return load.load_all()


@pytest.fixture(scope="module")
def table():
    return cr.load_criteria_table()


@pytest.fixture(scope="module")
def ranking(data, table):
    return rk.rank_ghats(data, table)


@pytest.fixture(scope="module")
def plan(ranking):
    return pl.plan_actions(ranking)


@pytest.fixture(scope="module")
def evidence(data, table):
    return evm.build_evidence(data, table)


@pytest.fixture(scope="module")
def briefs(ranking, plan, evidence, table):
    return br.build_briefs(ranking, plan, evidence, table, generated_on=GEN)


# ------------------------------------------------------------ templates

def _placeholders(text):
    return set(re.findall(r"\$(\w+)", text))


def test_templates_exist_and_differ():
    en = (br.TEMPLATE_DIR / "brief_en.md").read_text(encoding="utf-8")
    hi = (br.TEMPLATE_DIR / "brief_hi.md").read_text(encoding="utf-8")
    assert en != hi
    devanagari = sum("ऀ" <= ch <= "ॿ" for ch in hi)
    latin = sum(ch.isascii() and ch.isalpha() for ch in re.sub(r"\$\w+|MPPCB|CPCB|BMC|PDF|B|DO|BOD|pH", "", hi))
    assert devanagari > 5 * latin  # written in Hindi, not copied English
    assert _placeholders(hi) - _placeholders(en) == {"review_notice"}
    assert _placeholders(en) <= _placeholders(hi)


@pytest.mark.parametrize("lang", br.LANGUAGES)
def test_templates_hold_no_statistics(lang):
    text = (br.TEMPLATE_DIR / f"brief_{lang}.md").read_text(encoding="utf-8")
    # Only section numbers ("## 4." / "section 4") may appear as digits.
    without_sections = re.sub(r"^## \d\.|section \d|खंड \d|\$\w+", "", text, flags=re.M)
    assert not re.search(r"\d", without_sections)


def test_placeholders_all_filled(ranking, plan, evidence, table):
    for lang in br.LANGUAGES:
        values = br.brief_values(ranking, plan, evidence, table, lang, GEN)
        tmpl = (br.TEMPLATE_DIR / f"brief_{lang}.md").read_text(encoding="utf-8")
        assert _placeholders(tmpl) <= set(values)
        assert "$" not in br.build_brief(ranking, plan, evidence, table, lang, GEN)


def test_bad_language(ranking, plan, evidence):
    with pytest.raises(ValueError, match="language"):
        br.build_brief(ranking, plan, evidence, lang="fr")


# ------------------------------------------------------------ figures from code

RANKED_EN = re.compile(
    r"^(\d)\. \*\*(.+?)\*\* — Tier (\d)(, high risk)?: "
    r"(?:DO <5 mg/l in (\d+)/(\d+), lowest ([\d.]+) \((\d{4}) (\w+) ([\w -]+?), p\.(\d+)( ✓)?\)|DO ≥5 mg/l in all (\d+))"
    r"; BOD >3 in (\d+)/(\d+)(?:; pH outside 6\.5–8\.5 in (\d+)/(\d+))?",
    re.M,
)


def test_ranked_lines_match_ranking(briefs, ranking, evidence):
    lines = RANKED_EN.findall(briefs["en"])
    assert len(lines) == 7
    ph_words = {"pre-immersion": "pre", "during": "during", "1 week after": "after"}
    for g, m in zip(ranking.ghats, lines):
        rank, site, tier, hr, n, N, low, year, fest, phase, page, mark, all_n, bod_n, bod_N, ph_n, ph_N = m
        mt = g.metrics
        assert (int(rank), site, int(tier), bool(hr)) == (g.rank, g.site, g.tier, g.high_risk)
        assert (int(bod_n), int(bod_N)) == (mt.bod_fail, mt.bod_usable)
        assert (int(ph_n or 0), int(ph_N or mt.ph_usable)) == (mt.ph_out, mt.ph_usable)
        if all_n:
            assert mt.do_fail == 0 and int(all_n) == mt.do_usable
            continue
        assert (int(n), int(N), float(low)) == (mt.do_fail, mt.do_usable, mt.do_min)
        # The cited reading exists in the evidence with that value and page.
        row = evidence[(evidence["site"] == site) & (evidence["parameter"] == "Dissolved oxygen")
                       & (evidence["year"] == int(year)) & (evidence["festival"] == fest)
                       & (evidence["phase"] == ph_words[phase])]
        assert len(row) == 1
        assert float(row["value"].iloc[0]) == float(low)
        assert row["source_page"].iloc[0] == int(page)
        # ✓ appears exactly when the evidence marks this reading as spot-checked.
        assert bool(mark) == row["page_verified"].iloc[0].startswith("spot-checked")


def test_every_number_traceable(briefs, ranking, plan, evidence, table):
    allowed = {str(x) for x in (1, 2, 3, 4, 5, 6, 7)}  # ranks, tiers, section numbers, "1 week after"
    for g in ranking.ghats:
        m = g.metrics
        allowed |= {str(v) for v in (m.do_fail, m.do_usable, m.bod_fail, m.bod_usable, m.ph_out, m.ph_usable)}
        if m.do_min is not None:
            allowed.add(f"{m.do_min:g}")
        for f in g.flags:
            if f.code == "DATA_GAP":
                allowed.add(str(f.counts["cells"]))
    do = evidence[(evidence["parameter"] == "Dissolved oxygen") & evidence["class_b_result"].isin(["pass", "fail"])]
    allowed |= {str(p) for p in do["source_page"]} | {str(y) for y in do["year"]}
    pre_bod = evidence[(evidence["parameter"] == "BOD") & (evidence["phase"] == "pre")
                       & evidence["class_b_result"].isin(["pass", "fail"])]
    allowed |= {str(len(pre_bod)), str(int((pre_bod["class_b_result"] == "fail").sum()))}
    for a in plan.actions:
        allowed |= {str(a.start.day), str(a.end.day), str(a.start.year)}
    allowed |= {str(plan.event_date.day), str(plan.end.day), "11", "2026"}
    for c in cr.criteria_for_class(table, "B"):
        allowed |= set(re.findall(r"\d+(?:\.\d+)?", c.limit_as_printed + " " + c.unit))
    allowed |= {"2023", "2025"}
    checked = evidence[evidence["page_verified"].str.startswith("spot-checked")]
    allowed |= {str(len(checked)), str(len(checked[["year", "source_page"]].drop_duplicates()))}
    for lang, text in briefs.items():
        numbers = set(re.findall(r"\d+(?:\.\d+)?", text))
        assert numbers <= allowed, (lang, numbers - allowed)


def test_bod_summary_from_data(briefs, ranking):
    k = sum("BOD_OFTEN_HIGH" in g.flag_codes for g in ranking.ghats)
    assert f"BOD was above 3 mg/l in most readings at {k} of 7 ghats, including 32 of 37 pre-immersion readings." in briefs["en"]


def test_all_seven_ghats(briefs, ranking):
    for g in ranking.ghats:
        assert g.site in briefs["en"] and g.site in briefs["hi"]


# ------------------------------------------------------------ dates and actions

def test_dates(briefs):
    en, hi = briefs["en"], briefs["hi"]
    assert "Durga visarjan, 20 Oct 2026" in en and "Before 20 Oct" in en
    assert "Target for the 27 Oct 2026 sample" in en and "to 27 Oct" in en
    assert "27 अक्टूबर 2026 के नमूने का लक्ष्य" in hi and "दुर्गा विसर्जन, 20 अक्टूबर 2026" in hi
    assert "generated 11 Oct 2026" in en
    assert not re.search(r"\bD[+-]\d", en + hi)


def test_pre_actions_grouped_by_ghat(briefs, ranking, plan):
    section = briefs["en"].split("## 3.")[1].split("## 4.")[0]
    assert "**All 7 ghats:** barricades, nets or booms 15–20 Oct†; offerings collection and clean-up 18–22 Oct†" in section
    for g in ranking.ghats:
        own = [a for a in plan.for_site(g.site) if a.start < plan.event_date and a.triggers != (pl.ALL_GHATS,)
               and a.task_group != "Cleaning & debris"]
        if own:
            line = next(l for l in section.splitlines() if f"#{g.rank} {g.site}" in l)
            for a in own:
                assert pl.window_label(a.start, a.end) in line
    gap_ghats = [g for g in ranking.ghats if "DATA_GAP" in g.flag_codes]
    for g in gap_ghats:
        assert re.search(rf"#{g.rank} .*priority sampling 13–18 Oct", section)


def test_post_actions_and_targets(briefs):
    en = briefs["en"]
    section = en.split("## 4.")[1].split("## 5.")[0]
    assert "aerators, daily DO checks 17–27 Oct: #1, #2, #4, #5, #6†" in section
    assert "one-week-after sampling 27 Oct: all 7 ghats†" in section
    assert "DO ≥ 5 mg/l; BOD ≤ 3 mg/l; pH 6.5–8.5; Total coliform ≤ 500 MPN/100 ml (not tested in the supplied data)" in section


def test_warning_preserved(briefs):
    assert "† Recommendation — verify with MPPCB / CPCB guidelines." in briefs["en"]
    assert "Recommendation — verify with MPPCB / CPCB guidelines." in briefs["hi"]
    assert "not official instructions" in briefs["en"] and "आधिकारिक निर्देश नहीं" in briefs["hi"]


def test_no_warning_when_all_verified(ranking, plan, evidence):
    verified = replace(plan, actions=tuple(replace(a, verified=True, warning=None) for a in plan.actions))
    text = br.build_brief(ranking, verified, evidence, generated_on=GEN)
    assert "†" not in text and pl.UNVERIFIED_WARNING not in text


# ------------------------------------------------------------ disclosures

def test_disclosures(briefs):
    en, hi = briefs["en"], briefs["hi"]
    assert "No total coliform readings in the supplied data, so no ghat can be confirmed as meeting Class B." in en
    assert "No 2026 readings" in en
    assert "Readings show levels, not causes, and support no health conclusions." in en
    assert "#4: report tables may describe two different places under this name; field check 11–15 Oct." in en
    assert "A partial manual check matched 12 readings on 8 pages with the PDFs; all other page references are not yet checked." in en
    assert "✓ = cited reading matched the PDF page in a partial manual check." in en
    assert "not counted as passing: #1 (15), #2 (15), #3 (1), #6 (4)" in en
    assert "टोटल कोलीफॉर्म की कोई रीडिंग नहीं" in hi and "2026 की कोई रीडिंग नहीं" in hi
    assert "दो अलग जगहें" in hi and "बाकी पृष्ठों की जाँच अभी नहीं हुई है" in hi
    assert "not an official MPPCB assessment" in en and "MPPCB का आधिकारिक आकलन नहीं" in hi


def test_resources_not_estimated(briefs, ranking, plan, evidence):
    assert "Not estimated: no sourced rates are available yet." in briefs["en"]
    assert "अनुमान नहीं लगाया गया" in briefs["hi"]
    for text in briefs.values():
        assert not re.search(r"₹|\bRs\b|rupee|person-day|लाख|रुपये", text, re.I)
    custom = br.build_brief(ranking, plan, evidence, generated_on=GEN, resources="(estimator output)")
    assert "(estimator output)" in custom and "Not estimated" not in custom


def test_hindi_review_notice(ranking, plan, evidence, briefs):
    assert br.HINDI_REVIEW_NOTICE in briefs["hi"]
    assert "Provisional translation — requires fluent review" in briefs["hi"]
    assert br.HINDI_REVIEW_NOTICE not in briefs["en"]
    reviewed = br.build_brief(ranking, plan, evidence, lang="hi", generated_on=GEN, hindi_reviewed=True)
    assert br.HINDI_REVIEW_NOTICE not in reviewed


# ------------------------------------------------------------ wording

BANNED_EN = [r"\btoxic", r"\bunsafe\b", r"\bsafe\b", r"\bdisease", r"\bpoison", r"caused by immersion",
             r"\bclean\b(?!-up)", r"\bapprov", r"\bcompliant\b", r"\bmeets class b\b"]
BANNED_HI = ["विषैल", "ज़हरील", "जहरील", "असुरक्षित", "सुरक्षित", "बीमारी", "रोग", "स्वच्छ", "मंज़ूर", "स्वीकृत"]


def test_banned_words(briefs):
    en = briefs["en"].lower()
    for pattern in BANNED_EN:
        assert not re.search(pattern, en), pattern
    assert "clean-up" in en  # allowed: an action, not a status
    for word in BANNED_HI:
        assert word not in briefs["hi"], word


def test_banned_word_check_catches_status_use():
    assert re.search(BANNED_EN[6], "the water is clean")
    assert not re.search(BANNED_EN[6], "post-visarjan clean-up")


def test_absent_data_distinguished_from_failure(ranking, plan, evidence, table):
    durga25 = rk.rank_ghats(load.load_all(), table, festivals="Durga", years=2025)
    text = br.build_brief(durga25, pl.plan_actions(durga25), evidence, table, generated_on=GEN)
    line = next(l for l in text.splitlines() if "Bairagarh" in l and "Tier" in l)
    assert "no usable DO reading" in line and "no usable BOD reading" in line and "data gaps" in line
    assert "Durga 2025" in text


def test_lowest_do_must_match_ranking(ranking, plan, evidence):
    tampered = evidence.copy()
    i = tampered.index[(tampered["site"] == "Malikhedi kund") & (tampered["value"].astype(str) == "0.6")][0]
    tampered.loc[i, "value"] = 0.5
    with pytest.raises(ValueError, match="differs from ranking"):
        br.build_brief(ranking, plan, tampered, generated_on=GEN)


def test_deterministic(ranking, plan, evidence, table, briefs):
    assert br.build_briefs(ranking, plan, evidence, table, generated_on=GEN) == briefs
    assert br.build_briefs(ranking, plan, evidence, table, generated_on=date(2026, 10, 11)) == briefs


def test_length(briefs):
    # Approximately one page: bounded so the brief cannot silently grow.
    assert br.prose_word_count(briefs["en"]) <= 450
    assert br.prose_word_count(briefs["hi"]) <= 560


def test_bad_generation_date_named_correctly(ranking, plan, evidence):
    with pytest.raises(ValueError, match="generation date 'bad'"):
        br.build_brief(ranking, plan, evidence, generated_on="bad")
