"""Tests for ghatwatch.plan: rules config, date windows, per-ghat actions, overview."""

from dataclasses import replace
from datetime import date, datetime

import pandas as pd
import pytest

from ghatwatch import load
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

D = date(2026, 10, 20)


@pytest.fixture(scope="module")
def ranking():
    return rk.rank_ghats(load.load_all())


@pytest.fixture(scope="module")
def rules():
    return pl.load_action_rules()


@pytest.fixture(scope="module")
def plan(ranking):
    return pl.plan_actions(ranking)


def _rules_df() -> pd.DataFrame:
    return pd.read_csv(pl.RULES_FILE, dtype=str, keep_default_na=False, encoding="utf-8")


def _write_rules(df, tmp_path):
    path = tmp_path / "action_rules.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def _ghat(site, flags=(), rank=1, tier=4, high_risk=False):
    """Minimal GhatRank carrying only what the planner reads."""
    ev = rk.Evidence(2025, "Durga", "pre", "Dissolved oxygen", 3.0, "3", "numeric", 12, site)
    return rk.GhatRank(
        rank=rank, site=site, water_body="Lake", tier=tier, tier_label="", high_risk=high_risk, metrics=None,
        flags=tuple(rk.Flag(code, site, {}, f"{code} text", (ev,)) for code in flags),
    )


def _ranking(*ghats):
    return rk.Ranking(festivals=load.FESTIVALS, years=load.YEARS, phases=load.PHASES, ghats=tuple(ghats))


# ------------------------------------------------------------ dates

@pytest.mark.parametrize(
    "when, start, end",
    [
        ("D-9 to D-7", date(2026, 10, 11), date(2026, 10, 13)),
        ("D-7 to D-2", date(2026, 10, 13), date(2026, 10, 18)),
        ("D-6 to D-3", date(2026, 10, 14), date(2026, 10, 17)),
        ("D-5 to D", date(2026, 10, 15), date(2026, 10, 20)),
        ("D-3 to D+7", date(2026, 10, 17), date(2026, 10, 27)),
        ("D-2 to D+2", date(2026, 10, 18), date(2026, 10, 22)),
        ("D to D+7", date(2026, 10, 20), date(2026, 10, 27)),
        ("D+7", date(2026, 10, 27), date(2026, 10, 27)),
        ("D", date(2026, 10, 20), date(2026, 10, 20)),
        ("D-9 to D-5", date(2026, 10, 11), date(2026, 10, 15)),
    ],
)
def test_window_conversion(when, start, end):
    assert pl.window_dates(when, D) == (start, end)


@pytest.mark.parametrize(
    "start, end, label",
    [(date(2026, 10, 11), date(2026, 10, 13), "11–13 Oct"), (date(2026, 10, 27), date(2026, 10, 27), "27 Oct"),
     (date(2026, 10, 30), date(2026, 11, 2), "30 Oct–2 Nov")],
)
def test_window_label(start, end, label):
    assert pl.window_label(start, end) == label


def test_every_configured_window_inside_plan_period(rules):
    start, end = pl.plan_period(D)
    assert (start, end) == (date(2026, 10, 11), date(2026, 10, 27))
    for r in rules:
        s, e = pl.window_dates(r.when, D)
        assert start <= s <= e <= end


def test_event_and_d_plus_7(plan):
    assert plan.event_date == D
    d7 = [a for a in plan.actions if a.triggers == (pl.ALL_GHATS,) and a.task_group == "Water sampling"]
    assert len(d7) == 7
    assert {(a.start, a.end) for a in d7} == {(date(2026, 10, 27), date(2026, 10, 27))}
    assert all("total coliform" in a.action_en for a in d7)
    assert all(plan.start <= a.start <= a.end <= plan.end for a in plan.actions)


@pytest.mark.parametrize("bad", ["D-", "T-3", "D-3 to", "D-3..D+7", "D+3 to D-3", "D +3", ""])
def test_invalid_windows_raise(bad):
    with pytest.raises(ValueError, match="window"):
        pl.parse_window(bad)


@pytest.mark.parametrize("bad", ["2026-13-40", "20 Oct 2026", "", 20261020, None])
def test_invalid_event_dates_raise(bad, ranking):
    with pytest.raises(ValueError, match="event date"):
        pl.plan_actions(ranking, event_date=bad)


def test_event_date_accepts_iso_string_and_datetime(ranking, plan):
    assert pl.plan_actions(ranking, event_date="2026-10-20") == plan
    assert pl.plan_actions(ranking, event_date=datetime(2026, 10, 20, 18, 30)) == plan


def test_other_event_date_shifts_everything(ranking):
    shifted = pl.plan_actions(ranking, event_date=date(2027, 10, 9))
    assert shifted.start == date(2027, 9, 30) and shifted.end == date(2027, 10, 16)
    assert shifted.overview[0].window == "30 Sep–2 Oct"


# ------------------------------------------------------------ rules config

def test_rules_file_shape(rules):
    df = _rules_df()
    assert tuple(df.columns[:7]) == pl.RULE_COLUMNS
    assert len(rules) == 8
    assert {r.task_group for r in rules} <= set(pl.TASK_GROUPS)
    assert all(r.action_en and r.action_hi for r in rules)
    # Nothing is verified without a citation; nothing claims to be official.
    assert all(not r.verified for r in rules)
    assert all(r.source.startswith("team recommendation") for r in rules)
    assert all(not r.hi_reviewed for r in rules)


def test_rules_text_is_utf8_hindi(rules):
    assert all(any("ऀ" <= ch <= "ॿ" for ch in r.action_hi) for r in rules)


@pytest.mark.parametrize("column", pl.RULE_COLUMNS)
def test_missing_rule_column_raises(tmp_path, column):
    path = _write_rules(_rules_df().drop(columns=column), tmp_path)
    with pytest.raises(load.DataValidationError, match=column):
        pl.load_action_rules(path)


@pytest.mark.parametrize(
    "column, value, message",
    [
        ("trigger_flag", "DO_LOW", "not a ranking flag"),
        ("trigger_flag", "ALL_GHATS|DATA_GAP", "cannot be combined"),
        ("task_group", "Cleaning", "not one of"),
        ("when", "D-3..D+7", "not understood"),
        ("when", "D-12 to D-9", "outside the plan period"),
        ("when", "D+8", "outside the plan period"),
        ("verified", "maybe", "yes or no"),
        ("verified", "yes", "cite the guideline"),
        ("action_hi", "", "blank"),
        ("action_hi_reviewed", "perhaps", "yes or no"),
    ],
)
def test_invalid_rule_values_raise(tmp_path, column, value, message):
    df = _rules_df()
    df.loc[2, column] = value
    with pytest.raises(load.DataValidationError, match=message) as exc:
        pl.load_action_rules(_write_rules(df, tmp_path))
    assert exc.value.field_name == column
    assert "row 3" in str(exc.value)


def test_verified_yes_with_citation_is_accepted(tmp_path, ranking):
    df = _rules_df()
    df.loc[2, "verified"] = "yes"
    df.loc[2, "source"] = "CPCB idol immersion guidelines (example citation for test)"
    p = pl.plan_actions(ranking, _write_rules(df, tmp_path))
    bod = [a for a in p.actions if a.triggers == ("BOD_OFTEN_HIGH",)]
    assert bod and all(a.verified and a.warning is None for a in bod)


def test_missing_rules_file_raises(tmp_path, ranking):
    with pytest.raises(load.DataValidationError, match="file not found"):
        pl.plan_actions(ranking, tmp_path / "none.csv")


def test_rules_editable_without_code(tmp_path, ranking):
    df = _rules_df()
    df.loc[len(df)] = ["PH_OUT", "Extra pH check", "अतिरिक्त pH जाँच", "Water sampling", "D+1", "team recommendation", "no", "no"]
    p = pl.plan_actions(ranking, _write_rules(df, tmp_path))
    extra = [a for a in p.actions if a.action_en == "Extra pH check"]
    assert {a.site for a in extra} == {g.site for g in ranking.ghats if "PH_OUT" in g.flag_codes}
    assert {a.window for a in extra} == {"21 Oct"}


# ------------------------------------------------------------ applying rules

def test_all_ghats_actions_for_all_seven(plan, ranking, rules):
    all_rules = [r for r in rules if r.triggers == (pl.ALL_GHATS,)]
    assert len(all_rules) == 2
    for r in all_rules:
        sites = {a.site for a in plan.actions if r.rule_id in a.rule_ids}
        assert sites == {g.site for g in ranking.ghats}
    # Includes a tier 4 ghat in a synthetic ranking.
    p = pl.plan_actions(_ranking(_ghat("Quiet", tier=4)))
    assert {a.task_group for a in p.actions} == {"Barricading & nets", "Water sampling"}


def test_flag_actions_only_for_matching_ghats(plan, ranking, rules):
    flags = {g.site: set(g.flag_codes) for g in ranking.ghats}
    for r in rules:
        if r.triggers == (pl.ALL_GHATS,):
            continue
        sites = {a.site for a in plan.actions if r.rule_id in a.rule_ids}
        assert sites == {s for s, f in flags.items() if f & set(r.triggers)}, r.rule_id
        for a in plan.actions:
            if r.rule_id in a.rule_ids:
                assert set(a.triggers) <= flags[a.site]


def test_data_gap_ghats_get_pre_immersion_sampling(plan, ranking):
    gap_sites = [g.site for g in ranking.ghats if "DATA_GAP" in g.flag_codes]
    assert gap_sites
    for site in gap_sites:
        assert any(a.task_group == "Water sampling" and a.end < D and "DATA_GAP" in a.triggers
                   for a in plan.for_site(site))


def test_site_identity_ghats_get_field_check(plan, ranking):
    sites = [g.site for g in ranking.ghats if "SITE_IDENTITY" in g.flag_codes]
    assert sites == ["Rani Kamlapati ghat / Kamla Park kund"]
    checks = [a for a in plan.for_site(sites[0]) if a.task_group == "Site identity check"]
    assert len(checks) == 1 and checks[0].window == "11–15 Oct"


def test_guarantee_enforced_when_rule_removed(tmp_path, ranking):
    df = _rules_df()
    path = _write_rules(df[df["trigger_flag"] != "DATA_GAP"], tmp_path)
    with pytest.raises(pl.PlanError, match="DATA_GAP"):
        pl.plan_actions(ranking, path)
    path = _write_rules(df[df["trigger_flag"] != "SITE_IDENTITY"], tmp_path)
    with pytest.raises(pl.PlanError, match="SITE_IDENTITY"):
        pl.plan_actions(ranking, path)


def test_multiple_flags_do_not_duplicate(plan):
    # Bairagarh has DO_SEVERE and DO_ZERO: one shared rule, one task.
    severe = [a for a in plan.for_site("Bairagarh (Sant Hirdaram) kund") if "R1" in a.rule_ids]
    assert len(severe) == 1
    assert severe[0].triggers == ("DO_SEVERE", "DO_ZERO")
    # Evidence from both flags, no repeats.
    assert len(severe[0].evidence) == len(set(severe[0].evidence)) == 6
    keys = [(a.site, a.action_en, a.start, a.end) for a in plan.actions]
    assert len(keys) == len(set(keys))


def test_identical_rows_merge(tmp_path, ranking):
    df = _rules_df()
    dup = df.iloc[[2]].copy()  # BOD rule
    dup["trigger_flag"] = "PH_OUT"
    p = pl.plan_actions(ranking, _write_rules(pd.concat([df, dup]), tmp_path))
    hathaikheda = [a for a in p.for_site("Hathaikheda dam / kund") if a.task_group == "Cleaning & debris"]
    assert len(hathaikheda) == 1
    assert hathaikheda[0].triggers == ("BOD_OFTEN_HIGH", "PH_OUT")
    assert hathaikheda[0].rule_ids == ("R3", "R9")


def test_distinct_actions_kept(plan):
    # DO_SEVERE (pre-immersion aerators + daily checks) and DO_OFTEN_LOW
    # (aeration during/after + D+1/3/7 checks) are different tasks.
    aeration = [a for a in plan.for_site("Bairagarh (Sant Hirdaram) kund") if a.task_group == "Aeration"]
    assert len(aeration) == 2
    assert {a.window for a in aeration} == {"17–27 Oct", "20–27 Oct"}
    assert aeration[0].action_en != aeration[1].action_en
    # PH_OUT and DATA_GAP sampling both kept at Khatlapura.
    sampling = [a for a in plan.for_site("Khatlapura ghat") if a.task_group == "Water sampling"]
    assert len(sampling) == 3


def test_unverified_warning_and_texts_survive(plan, rules):
    by_id = {r.rule_id: r for r in rules}
    for a in plan.actions:
        assert a.verified is False
        assert a.warning == pl.UNVERIFIED_WARNING == "Recommendation — verify with MPPCB / CPCB guidelines."
        rule = by_id[a.rule_ids[0]]
        assert (a.action_en, a.action_hi, a.source) == (rule.action_en, rule.action_hi, rule.source)
    frame = plan.to_frame()
    assert (frame["verified"] == "no").all() and (frame["warning"] == pl.UNVERIFIED_WARNING).all()


def test_evidence_only_on_flag_actions(plan, ranking):
    flags = {(g.site, f.code): f for g in ranking.ghats for f in g.flags}
    for a in plan.actions:
        if a.triggers == (pl.ALL_GHATS,):
            assert a.evidence == ()
        elif "SITE_IDENTITY" not in a.triggers:
            expected = {e for t in a.triggers for e in flags[(a.site, t)].evidence}
            assert set(a.evidence) == expected and a.evidence


def test_order_follows_rank_then_date(plan):
    assert [a.order for a in plan.actions] == list(range(1, len(plan.actions) + 1))
    keys = [(a.ghat_rank, a.start, a.end) for a in plan.actions]
    assert keys == sorted(keys)


def test_counts(plan):
    per_site = {s: len(plan.for_site(s)) for s in dict.fromkeys(a.site for a in plan.actions)}
    assert per_site == {
        "Bairagarh (Sant Hirdaram) kund": 6, "Malikhedi kund": 6, "Khatlapura ghat": 5,
        "Rani Kamlapati ghat / Kamla Park kund": 5, "Shahpura lake ghat": 4, "Prempura ghat": 6,
        "Hathaikheda dam / kund": 4,
    }
    assert len(plan.actions) == 36


def test_deterministic(ranking, plan):
    again = pl.plan_actions(ranking)
    assert again == plan
    shuffled = replace(ranking, ghats=tuple(reversed(ranking.ghats)))
    assert pl.plan_actions(shuffled) == plan


# ------------------------------------------------------------ overview

def test_overview_windows(plan):
    assert [w.window for w in plan.overview] == [
        "11–13 Oct", "14–17 Oct", "18–19 Oct", "20 Oct", "21–22 Oct", "23–26 Oct", "27 Oct",
    ]


def test_overview_sites_come_from_ranking(plan, ranking):
    def sites(window, prefix):
        w = next(w for w in plan.overview if w.window == window)
        return next(a.sites for a in w.activities if a.text_en.startswith(prefix))

    tier1 = tuple(g.site for g in ranking.ghats if g.tier == 1)
    assert sites("14–17 Oct", "Arrange aerators") == tier1
    assert sites("18–19 Oct", "Re-check DO") == tier1
    assert sites("11–13 Oct", "Field check") == ("Rani Kamlapati ghat / Kamla Park kund",)
    assert set(sites("11–13 Oct", "Request priority")) == {g.site for g in ranking.ghats if "DATA_GAP" in g.flag_codes}
    assert sites("23–26 Oct", "Follow-up DO") == tuple(g.site for g in ranking.ghats if g.high_risk)
    assert len(sites("27 Oct", "One-week-after")) == 7


def test_overview_drops_activities_no_ghat_needs():
    p = pl.plan_actions(_ranking(_ghat("Quiet")))
    texts = [a.text_en for w in p.overview for a in w.activities]
    assert not any(t.startswith(("Field check", "Arrange aerators", "Aerators running")) for t in texts)
    assert "Officer approves the priority list" in texts


def test_plan_makes_no_completion_claims(plan):
    assert "not show that tasks are scheduled, accepted or resourced" in plan.note
    text = " ".join([a.action_en for a in plan.actions] + [x.text_en for w in plan.overview for x in w.activities]).lower()
    for word in ("completed", "done", "accepted", "approved by"):
        assert word not in text
