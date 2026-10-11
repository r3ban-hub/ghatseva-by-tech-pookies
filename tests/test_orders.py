"""Tests for ghatwatch.orders: assignments config, routing, guarantees, rendering."""

import re
from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from ghatwatch import load
from ghatwatch import orders as od
from ghatwatch import plan as pl
from ghatwatch import ranking as rk

SAMPLING_ROLE = "MPPCB regional office, Bhopal"


@pytest.fixture(scope="module")
def data():
    return load.load_all()


@pytest.fixture(scope="module")
def ranking(data):
    return rk.rank_ghats(data)


@pytest.fixture(scope="module")
def plan(ranking):
    return pl.plan_actions(ranking)


@pytest.fixture(scope="module")
def orders(ranking, plan, data):
    return od.work_orders(ranking, plan, readings=data.readings)


@pytest.fixture(scope="module")
def by_site(orders):
    return {o.site: o for o in orders}


def _df() -> pd.DataFrame:
    return pd.read_csv(od.ASSIGNMENTS_FILE, dtype=str, keep_default_na=False, encoding="utf-8")


def _write(df, tmp_path):
    path = tmp_path / "ghat_assignments.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    return path


# ------------------------------------------------------------ config file

def test_config_has_35_role_only_rows():
    df = _df()
    assert len(df) == 35
    assert set(zip(df["site"], df["task_group"])) == {(s, t) for s in load.SITES for t in pl.TASK_GROUPS}
    # No ward numbers or BMC roles invented.
    assert (df["zone_ward"] == "").all()
    assert set(df["responsible_role"]) == {"", SAMPLING_ROLE}
    assert set(df["report_to_role"]) == {"Visarjan nodal officer, BMC"}
    # The provisional MPPCB role is explicitly marked as an assumption.
    sampling = df[df["responsible_role"] == SAMPLING_ROLE]
    assert (sampling["task_group"] == "Water sampling").all() and len(sampling) == 7
    assert (sampling["role_is_assumption"] == "yes").all()
    assert sampling["note"].str.startswith("ASSUMPTION").all()


def test_loaded_assignments_keep_blanks():
    a = od.load_assignments()
    assert all(v is None for v in a.zone_ward.values())
    cleaning = a.by_key[("Malikhedi kund", "Cleaning & debris")]
    assert cleaning.responsible_role is None
    assert a.by_key[("Malikhedi kund", "Water sampling")].role_is_assumption


@pytest.mark.parametrize("column", od.ASSIGNMENT_COLUMNS)
def test_missing_column_raises(tmp_path, column):
    with pytest.raises(load.DataValidationError, match=column):
        od.load_assignments(_write(_df().drop(columns=column), tmp_path))


@pytest.mark.parametrize(
    "column, value, message",
    [
        ("site", "Upper Lake ghat", "not one of the 7"),
        ("task_group", "Cleaning", "not one of"),
        ("role_is_assumption", "maybe", "yes or no"),
    ],
)
def test_invalid_values_raise(tmp_path, column, value, message):
    df = _df()
    df.loc[4, column] = value
    with pytest.raises(load.DataValidationError, match=message) as exc:
        od.load_assignments(_write(df, tmp_path))
    assert exc.value.field_name == column and "row 5" in str(exc.value)
    assert exc.value.source == "ghat_assignments.csv"


def test_duplicate_assignment_raises(tmp_path):
    df = _df()
    df = pd.concat([df, df.iloc[[3]]], ignore_index=True)
    with pytest.raises(load.DataValidationError, match="more than once"):
        od.load_assignments(_write(df, tmp_path))


def test_conflicting_wards_raise(tmp_path):
    df = _df()
    df.loc[0, "zone_ward"] = "Zone 7"
    df.loc[1, "zone_ward"] = "Zone 8"
    with pytest.raises(load.DataValidationError, match="conflicting"):
        od.load_assignments(_write(df, tmp_path))


@pytest.mark.parametrize("column", ["responsible_role", "report_to_role", "zone_ward", "note"])
@pytest.mark.parametrize(
    "value, message",
    [
        ("0000000000", "phone"),
        ("+00 00000 00000", "phone"),
        ("Zone engineer (000-0000000)", "phone"),
        ("officer@example.org", "email"),
        ("Sanitation in-charge, contact zone7.office@example.org", "email"),
        ("Shri R. Sharma", "person's name"),
        ("Mrs Gupta, zone office", "person's name"),
    ],
)
def test_personal_data_rejected(tmp_path, column, value, message):
    df = _df()
    df.loc[0, column] = value
    with pytest.raises(load.DataValidationError, match=message) as exc:
        od.load_assignments(_write(df, tmp_path))
    assert exc.value.field_name == column


@pytest.mark.parametrize("value", ["Zone 7 sanitation in-charge", "Ward 12", "Zone engineer (water works)",
                                   "Executive engineer, Zone 14"])
def test_role_titles_with_short_numbers_allowed(tmp_path, value):
    df = _df()
    df.loc[0, "responsible_role"] = value
    df.loc[0:4, "zone_ward"] = "Zone 7, Ward 12"
    a = od.load_assignments(_write(df, tmp_path))
    assert a.by_key[(df.loc[0, "site"], df.loc[0, "task_group"])].responsible_role == value
    assert a.zone_ward[df.loc[0, "site"]] == "Zone 7, Ward 12"


# ------------------------------------------------------------ orders

def test_seven_orders_in_rank_order(orders, ranking):
    assert len(orders) == 7
    assert [o.site for o in orders] == [g.site for g in ranking.ghats]
    assert {o.site for o in orders} == set(load.SITES)


def test_every_planned_action_on_its_order(orders, plan):
    on_orders = [t.action for o in orders for t in o.tasks]
    assert sorted(on_orders, key=lambda a: a.order) == list(plan.actions)
    for o in orders:
        assert tuple(t.action for t in o.tasks) == plan.for_site(o.site)
        assert [t.number for t in o.tasks] == list(range(1, len(o.tasks) + 1))
        assert all(t.action.site == o.site for t in o.tasks)


def test_routing_by_task_group(tmp_path, ranking, plan):
    df = _df()
    roles = {"Cleaning & debris": "Zone sanitation in-charge", "Aeration": "Zone engineer (water works)",
             "Barricading & nets": "Zone engineer (civil)", "Site identity check": "Zone officer"}
    for group, role in roles.items():
        df.loc[df["task_group"] == group, "responsible_role"] = role
    result = od.work_orders(ranking, plan, _write(df, tmp_path))
    roles["Water sampling"] = SAMPLING_ROLE
    for o in result:
        for t in o.tasks:
            assert t.responsible == roles[t.action.task_group]
            assert t.responsible_assigned


def test_routing_per_site(tmp_path, ranking, plan):
    df = _df()
    df.loc[(df["site"] == "Prempura ghat") & (df["task_group"] == "Cleaning & debris"), "responsible_role"] = "Zone 9 sanitation in-charge"
    result = {o.site: o for o in od.work_orders(ranking, plan, _write(df, tmp_path))}
    prem = [t for t in result["Prempura ghat"].tasks if t.action.task_group == "Cleaning & debris"]
    other = [t for t in result["Khatlapura ghat"].tasks if t.action.task_group == "Cleaning & debris"]
    assert prem[0].responsible == "Zone 9 sanitation in-charge"
    assert other[0].responsible == od.ASSIGN_BLANK


def test_unassigned_roles_print_blank(by_site):
    for o in by_site.values():
        md = od.to_markdown(o)
        for t in o.tasks:
            if t.action.task_group == "Water sampling":
                assert t.responsible == SAMPLING_ROLE and t.responsible_is_assumption
            else:
                assert t.responsible == od.ASSIGN_BLANK and not t.responsible_assigned
        assert "Assign: ________" in md
        assert "| |  |" not in md  # no empty responsible cells
        assert "*(assumed — confirm)*" in md


def test_missing_assignment_rows_still_listed(tmp_path, ranking, plan):
    df = _df()
    df = df[df["task_group"] != "Aeration"]
    result = {o.site: o for o in od.work_orders(ranking, plan, _write(df, tmp_path))}
    aeration = [t for t in result["Bairagarh (Sant Hirdaram) kund"].tasks if t.action.task_group == "Aeration"]
    assert len(aeration) == 2
    assert all(t.responsible == od.ASSIGN_BLANK and t.report_to is None for t in aeration)
    assert "| Assign: ________ | ☐ |" in od.to_markdown(result["Bairagarh (Sant Hirdaram) kund"])


def test_data_gap_ghats_have_pre_immersion_sampling(orders):
    gaps = [o for o in orders if any(f.code == "DATA_GAP" for f in o.flags)]
    assert len(gaps) == 4
    for o in gaps:
        assert any(t.action.task_group == "Water sampling" and t.action.end < date(2026, 10, 20) for t in o.tasks)


def test_site_identity_ghats_have_field_check(orders):
    flagged = [o for o in orders if any(f.code == "SITE_IDENTITY" for f in o.flags)]
    assert [o.site for o in flagged] == ["Rani Kamlapati ghat / Kamla Park kund"]
    assert any(t.action.task_group == "Site identity check" for t in flagged[0].tasks)


def test_guarantee_violations_raise(ranking, plan, data):
    # A hand-edited plan that lost the DATA_GAP sampling task must not produce an order.
    trimmed = replace(plan, actions=tuple(a for a in plan.actions if "DATA_GAP" not in a.triggers))
    with pytest.raises(pl.PlanError, match="DATA_GAP"):
        od.work_orders(ranking, trimmed)
    trimmed = replace(plan, actions=tuple(a for a in plan.actions if a.task_group != "Site identity check"))
    with pytest.raises(pl.PlanError, match="SITE_IDENTITY"):
        od.work_orders(ranking, trimmed)


def test_unknown_site_rejected(ranking, plan):
    with pytest.raises(ValueError, match="not in the ranking"):
        od.work_order("Nowhere ghat", ranking, plan, od.load_assignments())


def test_actual_dates_not_offsets(by_site):
    for o in by_site.values():
        md = od.to_markdown(o)
        assert not re.search(r"\bD[+-]\d", md)
        for t in o.tasks:
            assert f"| {t.action.window} 2026 |" in md
    bairagarh = od.to_markdown(by_site["Bairagarh (Sant Hirdaram) kund"])
    assert "| 13–18 Oct 2026 |" in bairagarh and "| 27 Oct 2026 |" in bairagarh


def test_class_b_target_and_d7_date(by_site):
    o = by_site["Hathaikheda dam / kund"]
    assert o.target_sample_date == date(2026, 10, 27)
    assert [(t.parameter, t.target, t.tested_in_data) for t in o.targets] == [
        ("Dissolved oxygen", "≥ 5 mg/l", True), ("BOD", "≤ 3 mg/l", True),
        ("pH", "6.5–8.5", True), ("Total coliform", "≤ 500 MPN/100 ml", False),
    ]
    md = od.to_markdown(o)
    assert "sample on 27 Oct 2026" in md
    assert "Total coliform ≤ 500 MPN/100 ml — not tested in the supplied data" in md


def test_evidence_preserved_from_ranking(by_site, ranking, data):
    src = data.readings.set_index(list(load.KEY_COLUMNS))
    for g in ranking.ghats:
        o = by_site[g.site]
        assert o.flags == g.flags  # same objects: texts and evidence untouched
        for t in o.tasks:
            for e in t.action.evidence:
                key = (e.year, e.festival, g.site, e.phase, e.parameter)
                if e.source_page is None:
                    assert key not in src.index
                else:
                    assert src.loc[key, "source_page"] == e.source_page
    md = od.to_markdown(by_site["Bairagarh (Sant Hirdaram) kund"])
    assert "2023 p.26, p.60" in md
    assert "no page (no table in report)" in md  # absent tables shown as such, not given a page


def test_names_as_printed_not_resolved(by_site):
    rani = by_site["Rani Kamlapati ghat / Kamla Park kund"]
    assert set(rani.names_as_printed) == {"Ganesh", "Durga"}
    assert any("kamla park" in n.lower() for n in rani.names_as_printed["Ganesh"])
    assert any("lower lake" in n.lower() for n in rani.names_as_printed["Durga"])
    md = od.to_markdown(rani)
    assert "does not choose between them" in md
    assert rani.site == "Rani Kamlapati ghat / Kamla Park kund"
    assert "does not choose" not in od.to_markdown(by_site["Prempura ghat"])


def test_names_fallback_without_readings(ranking, plan):
    o = od.work_orders(ranking, plan)[0]
    assert o.names_as_printed and all(o.names_as_printed.values())


def test_warning_and_texts_survive(by_site):
    for o in by_site.values():
        md = od.to_markdown(o)
        for t in o.tasks:
            assert t.action.warning == pl.UNVERIFIED_WARNING
            assert t.action.action_en in md and t.action.action_hi in md
        assert md.count("⚠ " + pl.UNVERIFIED_WARNING) == len(o.tasks)
        assert md.count(pl.PROVISIONAL_HINDI) == len(o.tasks)


def test_header_and_footer(by_site):
    o = by_site["Bairagarh (Sant Hirdaram) kund"]
    assert (o.issued_by, o.issue_date, o.event_date) == ("Visarjan nodal officer, BMC", date(2026, 10, 11), date(2026, 10, 20))
    assert o.zone_ward is None and o.zone_ward_display == "________"
    md = od.to_markdown(o)
    assert "**Zone / ward:** ________" in md
    assert "**Tier 1, HIGH RISK**" in md
    assert md.rstrip().endswith(od.FOOTER)
    assert od.FOOTER == ("Generated from MPPCB visarjan reports 2023–2025 by Visarjan Ghat Watch. "
                         "Recommendations for officer verification. Not an official MPPCB assessment.")
    assert "does not send work orders or collect reports" in md
    assert "not yet been checked against the report PDFs" in md
    assert "not flagged high risk" in od.to_markdown(by_site["Khatlapura ghat"])


def test_issue_date_override(ranking, plan):
    o = od.work_orders(ranking, plan, issue_date="2026-10-12")[0]
    assert o.issue_date == date(2026, 10, 12)
    with pytest.raises(ValueError, match="issue date"):
        od.work_orders(ranking, plan, issue_date="12/10/2026")


def test_no_personal_data_or_claims(orders):
    text = "\n".join(od.to_markdown(o) for o in orders)
    assert not re.search(r"[\w.+-]+@[\w-]+\.", text)
    assert not re.search(r"\d(?:[\s\-]*\d){9,}", text)
    lowered = text.lower()
    for phrase in ("completed", "approved by", "accepted by", "has agreed", "toxic", "unsafe", "disease", "poison"):
        assert phrase not in lowered
    assert "☑" not in text and "[x]" not in lowered


def test_deterministic(ranking, plan, data, orders):
    again = od.work_orders(ranking, plan, readings=data.readings)
    assert again == orders
    assert [od.to_markdown(o) for o in again] == [od.to_markdown(o) for o in orders]


def test_task_counts(orders):
    assert {o.site: len(o.tasks) for o in orders} == {
        "Bairagarh (Sant Hirdaram) kund": 6, "Malikhedi kund": 6, "Khatlapura ghat": 5,
        "Rani Kamlapati ghat / Kamla Park kund": 5, "Shahpura lake ghat": 4, "Prempura ghat": 6,
        "Hathaikheda dam / kund": 4,
    }
