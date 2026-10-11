"""Tests for ghatwatch.ranking: metrics, tiers, flags, tie-breaks, evidence."""

import itertools
import math

import pandas as pd
import pytest

from ghatwatch import criteria as cr
from ghatwatch import load
from ghatwatch import ranking as rk

UNITS = {rk.DO: "mg/l", rk.BOD: "mg/l", rk.PH: ""}
SLOTS = list(itertools.product(load.YEARS, load.PHASES))  # 9 distinct (year, phase) cells per parameter


@pytest.fixture(scope="module")
def table():
    return cr.load_criteria_table()


@pytest.fixture(scope="module")
def data():
    return load.load_all()


@pytest.fixture(scope="module")
def real(data, table):
    return rk.rank_ghats(data, table)


def site_rows(name, do=(), bod=(), ph=(), conf="high"):
    """Synthetic grid rows. Each list item is a number, a value_state, or (value_state, value)."""
    rows = []
    for parameter, values in ((rk.DO, do), (rk.BOD, bod), (rk.PH, ph)):
        for (year, phase), v in zip(SLOTS, values):
            state, value = ("numeric", v) if not isinstance(v, (str, tuple)) else ((v, math.nan) if isinstance(v, str) else v)
            present = state != "no_table"
            rows.append({
                "year": year, "festival": "Durga", "site": name, "phase": phase, "parameter": parameter,
                "water_body": "Test lake" if present else math.nan,
                "value": value, "unit_assumed": UNITS[parameter] if present else math.nan,
                "flag": "" if present else math.nan,
                "value_as_printed": (f"{value:g}" if state == "numeric" else state) if present else math.nan,
                "site_as_printed": f"{name} as printed" if present else math.nan,
                "site_match_confidence": conf if present else math.nan,
                "source_page": 10 + year % 10 if present else pd.NA,
                "value_state": state,
            })
    return rows


def grid(*sites):
    df = pd.DataFrame([r for s in sites for r in s])
    df["year"] = df["year"].astype("Int64")
    df["source_page"] = df["source_page"].astype("Int64")
    return df


def rank(table, *sites, contradictory=frozenset(), **filters):
    return rk.rank_grid(grid(*sites), table, contradictory, **filters)


def by_site(ranking):
    return {g.site: g for g in ranking.ghats}


# ------------------------------------------------------------ tiers and thresholds

def test_four_tiers(table):
    r = by_site(rank(
        table,
        site_rows("T1", do=[4.5, 4.9, 6.0]),              # 2/3 below 5
        site_rows("T2", do=[4.99, 5.0, 6.0, 7.0]),        # 1/4 below 5
        site_rows("T3", do=[5.0, 6.0], bod=[3.01]),       # DO ok, BOD fails
        site_rows("T4", do=[5.0], bod=[3.0], ph=[6.5, 8.5]),  # all on the boundary: pass
    ))
    assert {s: g.tier for s, g in r.items()} == {"T1": 1, "T2": 2, "T3": 3, "T4": 4}
    assert [g.site for g in rank(table, site_rows("T4", do=[5.0]), site_rows("T1", do=[1.0])).ghats] == ["T1", "T4"]
    assert "clean" not in r["T4"].tier_label.lower() and "safe" not in r["T4"].tier_label.lower()


def test_ph_alone_gives_tier_3(table):
    r = by_site(rank(table, site_rows("P", do=[6.0], ph=[6.49])))
    assert r["P"].tier == 3


def test_do_fail_rate_exactly_half_is_not_often_low(table):
    r = by_site(rank(table, site_rows("Half", do=[4.5, 6.0]), site_rows("More", do=[4.5, 4.5, 6.0])))
    assert r["Half"].metrics.do_fail_rate == 0.5
    assert r["Half"].tier == 2
    assert "DO_OFTEN_LOW" not in r["Half"].flag_codes
    assert not r["Half"].high_risk
    assert r["More"].tier == 1
    assert "DO_OFTEN_LOW" in r["More"].flag_codes
    assert r["More"].high_risk


def test_do_severe_and_zero(table):
    r = by_site(rank(table, site_rows("Severe", do=[3.99, 6.0, 6.0]), site_rows("Four", do=[4.0, 6.0, 6.0]),
                     site_rows("Zero", do=[0.0, 6.0, 6.0])))
    assert "DO_SEVERE" in r["Severe"].flag_codes and r["Severe"].high_risk
    assert r["Severe"].tier == 2  # high risk is independent of tier
    assert "DO_SEVERE" not in r["Four"].flag_codes and not r["Four"].high_risk
    assert {"DO_SEVERE", "DO_ZERO"} <= set(r["Zero"].flag_codes)
    assert r["Zero"].metrics.do_zero == 1
    assert "DO_ZERO" not in r["Severe"].flag_codes


@pytest.mark.parametrize("bod, flagged", [([3.01, 3.01, 3.0], True), ([3.01, 3.0], False), ([3.0, 3.0], False)])
def test_bod_often_high_threshold(table, bod, flagged):
    g = rank(table, site_rows("S", do=[6.0], bod=bod)).ghats[0]
    assert ("BOD_OFTEN_HIGH" in g.flag_codes) is flagged


@pytest.mark.parametrize("ph, flagged", [([6.49], True), ([6.5], False), ([8.5], False), ([8.51], True)])
def test_ph_out_threshold(table, ph, flagged):
    g = rank(table, site_rows("S", do=[6.0], ph=ph)).ghats[0]
    assert ("PH_OUT" in g.flag_codes) is flagged
    assert g.metrics.ph_out == int(flagged)


# ------------------------------------------------------------ missing and contradictory

def test_non_numeric_states_never_counted(table):
    # Each state carries a value that would fail if it were (wrongly) used.
    do = [("not_sampled", 0.0), ("no_table", 0.0), ("bdl", 0.0), ("nd", 0.0), ("unknown_flag", 0.0), 6.0]
    bod = [("bdl", 99.0), ("nd", 99.0), 2.0]
    ph = [("unknown_flag", 2.0), 7.0]
    g = rank(table, site_rows("S", do=do, bod=bod, ph=ph)).ghats[0]
    m = g.metrics
    assert (m.do_usable, m.do_fail, m.do_severe, m.do_zero, m.do_min) == (1, 0, 0, 0, 6.0)
    assert (m.bod_usable, m.bod_fail, m.bod_median) == (1, 0, 2.0)
    assert (m.ph_usable, m.ph_out) == (1, 0)
    assert g.tier == 4
    gap = next(f for f in g.flags if f.code == "DATA_GAP")
    assert gap.counts["cells"] == 8
    assert all(e.value is None for e in gap.evidence)


def test_contradictory_rows_excluded(table):
    sites = [site_rows("S", do=[0.0, 4.5, 6.0])]
    key = (2023, "Durga", "S", "pre", rk.DO)  # the 0.0 reading
    g = rank(table, *sites, contradictory=frozenset({key})).ghats[0]
    assert (g.metrics.do_usable, g.metrics.do_fail, g.metrics.do_zero) == (2, 1, 0)
    assert g.tier == 2  # 1 of 2 usable below 5
    assert "DO_ZERO" not in g.flag_codes and "DO_SEVERE" not in g.flag_codes
    assert "DATA_GAP" in g.flag_codes
    # Without the contradiction the same data is tier 1 (2 of 3 below 5).
    assert rank(table, *sites).ghats[0].tier == 1


def test_contradictions_from_loader_reach_ranking(tmp_path, table):
    raw = pd.read_csv(load.DATA_DIR / load.READINGS_FILE, dtype=str, keep_default_na=False, encoding="utf-8")
    zero = raw.index[(raw["parameter"] == rk.DO) & (raw["value_as_printed"] == "0")]
    assert len(zero) == 4
    raw.loc[zero, "flag"] = "BDL"  # value 0 and a flag: contradictory
    raw.to_csv(tmp_path / load.READINGS_FILE, index=False, encoding="utf-8")
    (tmp_path / load.CRITERIA_FILE).write_bytes((load.DATA_DIR / load.CRITERIA_FILE).read_bytes())
    bairagarh = by_site(rk.rank_ghats(load.load_all(tmp_path), table))["Bairagarh (Sant Hirdaram) kund"]
    assert bairagarh.metrics.do_zero == 0
    assert bairagarh.metrics.do_usable == 9
    assert "DO_ZERO" not in bairagarh.flag_codes


def test_gaps_do_not_lower_tier(table):
    base = dict(do=[3.0, 6.0, 6.0], bod=[5.0, 5.0])
    with_gaps = dict(do=[3.0, 6.0, 6.0, "not_sampled", "no_table", "not_sampled"], bod=[5.0, 5.0, "no_table"], ph=["no_table"])
    a = rank(table, site_rows("S", **base)).ghats[0]
    b = rank(table, site_rows("S", **with_gaps)).ghats[0]
    assert a.tier == b.tier == 2
    assert a.metrics.do_fail_rate == b.metrics.do_fail_rate
    assert "DATA_GAP" in b.flag_codes and "DATA_GAP" not in a.flag_codes


def test_no_usable_data_gives_none_not_zero(table):
    g = rank(table, site_rows("Empty", do=["not_sampled", "no_table"], bod=["no_table"], ph=["not_sampled"])).ghats[0]
    m = g.metrics
    assert m.do_fail_rate is None and m.do_severe_rate is None and m.bod_fail_rate is None
    assert m.bod_median is None and m.do_min is None and m.bod_max is None
    assert m.coverage == 0.0
    assert g.tier == 4
    assert g.flag_codes == ("DATA_GAP",)


def test_missing_metric_sorts_after_real_value(table):
    # Same tier 4 and DO; one has BOD 0/1 failing, the other has no BOD at all.
    r = rank(table, site_rows("A-noBOD", do=[6.0], bod=["not_sampled"]), site_rows("Z-BOD", do=[6.0], bod=[2.0]))
    assert [g.site for g in r.ghats] == ["Z-BOD", "A-noBOD"]


# ------------------------------------------------------------ coverage

def test_coverage_uses_expected_grid(real):
    r = by_site(real)
    bairagarh = r["Bairagarh (Sant Hirdaram) kund"].metrics
    assert (bairagarh.coverage_numeric, bairagarh.coverage_expected) == (39, 54)  # 2 seasons absent / partial
    assert r["Rani Kamlapati ghat / Kamla Park kund"].metrics.coverage == 1.0
    assert all(g.metrics.coverage_expected == 54 for g in real.ghats)


def test_coverage_counts_no_table_cells(table):
    g = rank(table, site_rows("S", do=[6.0, "no_table"], bod=[2.0, "not_sampled"])).ghats[0]
    assert (g.metrics.coverage_numeric, g.metrics.coverage_expected) == (2, 4)


# ------------------------------------------------------------ tie-breakers

@pytest.mark.parametrize(
    "winner, loser",
    [
        # 1. DO fail rate (both tier 2)
        (dict(do=[4.5, 6.0, 6.0]), dict(do=[4.5, 6.0, 6.0, 6.0])),
        # 2. DO severe share (same DO fail rate)
        (dict(do=[3.0, 6.0]), dict(do=[4.5, 6.0])),
        # 3. BOD fail rate (same DO)
        (dict(do=[4.5, 6.0], bod=[4.0, 4.0]), dict(do=[4.5, 6.0], bod=[4.0, 2.0])),
        # 4. median BOD (same BOD fail rate)
        (dict(do=[4.5, 6.0], bod=[10.0, 2.0]), dict(do=[4.5, 6.0], bod=[5.0, 2.0])),
    ],
)
def test_tie_breakers_in_order(table, winner, loser):
    # Winner is named "Z" so alphabetical order alone would put it last.
    r = rank(table, site_rows("A", **loser), site_rows("Z", **winner))
    assert r.ghats[0].tier == r.ghats[1].tier
    assert [g.site for g in r.ghats] == ["Z", "A"]


def test_earlier_tie_breaker_beats_later(table):
    # Z: higher DO fail rate but lower BOD; A: lower DO fail rate, worse everything else.
    r = rank(table, site_rows("A", do=[3.0, 6.0, 6.0], bod=[9.0, 9.0]), site_rows("Z", do=[4.5, 6.0], bod=[2.0]))
    assert [g.site for g in r.ghats] == ["Z", "A"]


def test_name_is_last_tie_breaker(table):
    same = dict(do=[4.5, 6.0], bod=[4.0])
    assert [g.site for g in rank(table, site_rows("B", **same), site_rows("A", **same)).ghats] == ["A", "B"]


def test_deterministic_and_order_independent(table, data):
    a = rk.rank_ghats(data, table)
    b = rk.rank_ghats(data, table)
    shuffled = data.grid.sample(frac=1, random_state=7)
    c = rk.rank_grid(shuffled, table)
    for other in (b, c):
        pd.testing.assert_frame_equal(a.to_frame(), other.to_frame())
        assert a.ghats == other.ghats  # flags, texts and evidence identical


# ------------------------------------------------------------ site identity and evidence

def test_site_identity_flag(table, real):
    r = by_site(rank(table, site_rows("M", do=[6.0], conf="medium"), site_rows("H", do=[6.0])))
    assert "SITE_IDENTITY" in r["M"].flag_codes
    assert "SITE_IDENTITY" not in r["H"].flag_codes
    flagged = [g.site for g in real.ghats if "SITE_IDENTITY" in g.flag_codes]
    assert flagged == ["Rani Kamlapati ghat / Kamla Park kund"]


def test_site_identity_independent_of_filter(table, data):
    # Rani Kamlapati is flagged even when only Ganesh tables are in scope.
    r = by_site(rk.rank_ghats(data, table, festivals="Ganesh"))
    assert "SITE_IDENTITY" in r["Rani Kamlapati ghat / Kamla Park kund"].flag_codes


def test_evidence_pages_come_from_source_rows(real, data):
    src = data.readings.set_index(list(load.KEY_COLUMNS))
    checked = 0
    for g in real.ghats:
        for f in g.flags:
            for e in f.evidence:
                key = (e.year, e.festival, g.site, e.phase, e.parameter)
                if e.value_state == "no_table":
                    assert e.source_page is None and key not in src.index
                    assert "no page" in e.page_ref
                else:
                    row = src.loc[key]
                    assert e.source_page == row["source_page"]
                    assert e.value_as_printed == row["value_as_printed"]
                    assert e.site_as_printed == row["site_as_printed"]
                checked += 1
    assert checked > 100


def test_do_zero_evidence_matches_prd(real):
    zero = next(f for f in real.ghats[0].flags if f.code == "DO_ZERO")
    assert [(e.year, e.festival, e.phase, e.source_page) for e in zero.evidence] == [
        (2023, "Ganesh", "after", 26), (2023, "Durga", "pre", 60), (2023, "Durga", "during", 60), (2025, "Ganesh", "during", 28),
    ]
    assert "2023 Ganesh after, p.26" in zero.text_en


def test_flag_texts_follow_templates(real):
    r = by_site(real)
    texts = {f.code: f.text_en for f in r["Bairagarh (Sant Hirdaram) kund"].flags}
    assert texts["DO_SEVERE"] == ("Dissolved oxygen fell below 4 mg/l in 6 of 13 readings (lowest 0). "
                                  "Pages: 2023 p.26, p.60; 2024 p.25; 2025 p.28.")
    assert texts["DO_OFTEN_LOW"] == "Dissolved oxygen was below the bathing standard of 5 mg/l in 11 of 13 readings."
    assert texts["BOD_OFTEN_HIGH"] == "BOD was above the bathing limit of 3 mg/l in 13 of 13 readings (highest 14)."
    assert texts["DATA_GAP"].endswith("Missing data is not counted as passing.")
    assert "2025 Durga (pre, during, after)" in texts["DATA_GAP"]
    ph = next(f for f in r["Hathaikheda dam / kund"].flags if f.code == "PH_OUT")
    assert ph.text_en == "pH was outside 6.5–8.5 in 3 of 18 readings (8.92, 9.2, 8.71)."


# ------------------------------------------------------------ filters

def test_filters_keep_all_seven_ghats(table, data):
    r = rk.rank_ghats(data, table, festivals="Durga", years=2025)
    assert len(r.ghats) == 7
    assert (r.festivals, r.years, r.phases) == (("Durga",), (2025,), load.PHASES)
    b = by_site(r)["Bairagarh (Sant Hirdaram) kund"]
    assert b.metrics.do_usable == 0 and b.metrics.do_fail_rate is None
    assert b.metrics.coverage == 0.0 and "DATA_GAP" in b.flag_codes
    rani = by_site(r)["Rani Kamlapati ghat / Kamla Park kund"]
    assert rani.metrics.do_severe == 3  # all three 2025 Durga DO readings below 4


def test_phase_filter(table, data):
    r = rk.rank_ghats(data, table, phases=["pre"])
    assert all(g.metrics.coverage_expected == 18 for g in r.ghats)


@pytest.mark.parametrize("filters", [{"festivals": "Diwali"}, {"years": 2022}, {"phases": ["post"]}, {"phases": []}])
def test_bad_filters_raise(table, data, filters):
    with pytest.raises(ValueError):
        rk.rank_ghats(data, table, **filters)


# ------------------------------------------------------------ PRD §6.5 comparison

PRD_6_5 = [
    # site, tier, DO<5, DO N, DO<4, min DO, BOD>3, BOD N, pH out, pH N, flags
    ("Bairagarh (Sant Hirdaram) kund", 1, 11, 13, 6, 0.0, 13, 13, 0, 13,
     {"DO_SEVERE", "DO_ZERO", "DO_OFTEN_LOW", "BOD_OFTEN_HIGH", "DATA_GAP"}),
    ("Malikhedi kund", 1, 9, 13, 3, 0.6, 11, 13, 0, 13, {"DO_SEVERE", "DO_OFTEN_LOW", "BOD_OFTEN_HIGH", "DATA_GAP"}),
    ("Khatlapura ghat", 2, 8, 18, 0, 4.0, 15, 17, 1, 18, {"BOD_OFTEN_HIGH", "PH_OUT", "DATA_GAP"}),
    ("Rani Kamlapati ghat / Kamla Park kund", 2, 6, 18, 4, 2.4, 18, 18, 0, 18, {"DO_SEVERE", "BOD_OFTEN_HIGH", "SITE_IDENTITY"}),
    ("Shahpura lake ghat", 2, 5, 18, 3, 2.5, 18, 18, 0, 18, {"DO_SEVERE", "BOD_OFTEN_HIGH"}),
    ("Prempura ghat", 2, 3, 18, 1, 3.9, 9, 15, 2, 17, {"DO_SEVERE", "BOD_OFTEN_HIGH", "PH_OUT", "DATA_GAP"}),
    ("Hathaikheda dam / kund", 3, 0, 18, 0, 5.1, 16, 18, 3, 18, {"BOD_OFTEN_HIGH", "PH_OUT"}),
]


def test_real_ranking_matches_prd_preliminary_table(real):
    got = [
        (g.site, g.tier, g.metrics.do_fail, g.metrics.do_usable, g.metrics.do_severe, g.metrics.do_min,
         g.metrics.bod_fail, g.metrics.bod_usable, g.metrics.ph_out, g.metrics.ph_usable, set(g.flag_codes))
        for g in real.ghats
    ]
    assert got == PRD_6_5
    assert [g.site for g in real.ghats if g.high_risk] == [row[0] for row in PRD_6_5 if row[0] != "Hathaikheda dam / kund" and row[0] != "Khatlapura ghat"]
