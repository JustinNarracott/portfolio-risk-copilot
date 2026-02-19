"""Unit tests for scenario input parser (Issue #11)."""

import pytest

from src.scenario.parser import (
    ActionType,
    ParseError,
    ScenarioAction,
    parse_scenario,
)


# ──────────────────────────────────────────────
# Budget change parsing
# ──────────────────────────────────────────────


class TestBudgetIncrease:

    def test_percentage(self):
        r = parse_scenario("increase Project Beta budget by 20%")
        assert r.action == ActionType.BUDGET_INCREASE
        assert r.project == "Beta"
        assert r.amount == pytest.approx(0.20)

    def test_percentage_decimal(self):
        r = parse_scenario("increase Project Alpha budget by 15.5%")
        assert r.amount == pytest.approx(0.155)

    def test_absolute_amount(self):
        r = parse_scenario("increase Project Beta budget by £50,000")
        assert r.action == ActionType.BUDGET_INCREASE
        assert r.amount_absolute == 50_000.0

    def test_absolute_dollar(self):
        r = parse_scenario("increase Project Beta budget by $100,000")
        assert r.amount_absolute == 100_000.0

    def test_boost_verb(self):
        r = parse_scenario("boost Project Gamma budget by 10%")
        assert r.action == ActionType.BUDGET_INCREASE
        assert r.amount == pytest.approx(0.10)

    def test_alternative_phrasing(self):
        r = parse_scenario("increase the budget for Project Delta by 25%")
        assert r.action == ActionType.BUDGET_INCREASE
        assert r.project == "Delta"
        assert r.amount == pytest.approx(0.25)


class TestBudgetDecrease:

    def test_decrease_percentage(self):
        r = parse_scenario("decrease Project Alpha budget by 10%")
        assert r.action == ActionType.BUDGET_DECREASE
        assert r.amount == pytest.approx(0.10)

    def test_reduce_verb(self):
        r = parse_scenario("reduce Project Gamma budget by 15%")
        assert r.action == ActionType.BUDGET_DECREASE

    def test_lower_verb(self):
        r = parse_scenario("lower Project Beta budget by 5%")
        assert r.action == ActionType.BUDGET_DECREASE

    def test_absolute_decrease(self):
        r = parse_scenario("decrease Project Alpha budget by £30,000")
        assert r.action == ActionType.BUDGET_DECREASE
        assert r.amount_absolute == 30_000.0


# ──────────────────────────────────────────────
# Scope cut parsing
# ──────────────────────────────────────────────


class TestScopeCut:

    def test_cut_scope(self):
        r = parse_scenario("cut Project Beta scope by 30%")
        assert r.action == ActionType.SCOPE_CUT
        assert r.project == "Beta"
        assert r.amount == pytest.approx(0.30)

    def test_reduce_scope(self):
        r = parse_scenario("reduce Project Alpha scope by 50%")
        assert r.action == ActionType.SCOPE_CUT
        assert r.amount == pytest.approx(0.50)

    def test_trim_scope(self):
        r = parse_scenario("trim Project Gamma scope by 10%")
        assert r.action == ActionType.SCOPE_CUT

    def test_alternative_phrasing(self):
        r = parse_scenario("cut the scope for Project Delta by 25%")
        assert r.action == ActionType.SCOPE_CUT
        assert r.project == "Delta"


# ──────────────────────────────────────────────
# Delay parsing
# ──────────────────────────────────────────────


class TestDelay:

    def test_delay_weeks(self):
        r = parse_scenario("delay Project Gamma by 2 weeks")
        assert r.action == ActionType.DELAY
        assert r.project == "Gamma"
        assert r.duration_weeks == 2

    def test_delay_months(self):
        r = parse_scenario("delay Project Alpha by 3 months")
        assert r.duration_weeks == 12  # 3 * 4

    def test_delay_quarter(self):
        r = parse_scenario("delay Project Gamma by 1 quarter")
        assert r.duration_weeks == 13

    def test_delay_quarters(self):
        r = parse_scenario("delay Project Beta by 2 quarters")
        assert r.duration_weeks == 26

    def test_push_back_verb(self):
        r = parse_scenario("push back Project Delta by 4 weeks")
        assert r.action == ActionType.DELAY
        assert r.duration_weeks == 4

    def test_postpone_verb(self):
        r = parse_scenario("postpone Project Alpha by 1 month")
        assert r.action == ActionType.DELAY
        assert r.duration_weeks == 4

    def test_year_delay(self):
        r = parse_scenario("delay Project Gamma by 1 year")
        assert r.duration_weeks == 52


# ──────────────────────────────────────────────
# Remove parsing
# ──────────────────────────────────────────────


class TestRemove:

    def test_remove(self):
        r = parse_scenario("remove Project Delta")
        assert r.action == ActionType.REMOVE
        assert r.project == "Delta"

    def test_cancel(self):
        r = parse_scenario("cancel Project Beta")
        assert r.action == ActionType.REMOVE

    def test_drop(self):
        r = parse_scenario("drop Project Alpha")
        assert r.action == ActionType.REMOVE

    def test_remove_from_portfolio(self):
        r = parse_scenario("remove Project Delta from portfolio")
        assert r.action == ActionType.REMOVE
        assert r.project == "Delta"

    def test_without_project_prefix(self):
        r = parse_scenario("remove Delta")
        assert r.action == ActionType.REMOVE
        assert r.project == "Delta"


# ──────────────────────────────────────────────
# Case preservation
# ──────────────────────────────────────────────


class TestCasePreservation:

    def test_preserves_original_case(self):
        r = parse_scenario("delay Project Gamma by 1 quarter")
        assert r.project == "Gamma"  # Not "project gamma"

    def test_preserves_mixed_case(self):
        r = parse_scenario("remove Project MyApp-v2")
        assert r.project == "MyApp-v2"

    def test_stores_original_description(self):
        text = "increase Project Beta budget by 20%"
        r = parse_scenario(text)
        assert r.description == text


# ──────────────────────────────────────────────
# Error handling
# ──────────────────────────────────────────────


class TestErrorHandling:

    def test_empty_input(self):
        with pytest.raises(ParseError, match="Empty"):
            parse_scenario("")

    def test_whitespace_only(self):
        with pytest.raises(ParseError, match="Empty"):
            parse_scenario("   ")

    def test_unparseable_input(self):
        with pytest.raises(ParseError, match="Could not parse"):
            parse_scenario("do something weird with the portfolio")

    def test_gibberish(self):
        with pytest.raises(ParseError):
            parse_scenario("asdfghjkl")

    def test_partial_match(self):
        with pytest.raises(ParseError):
            parse_scenario("increase budget")  # No project specified
