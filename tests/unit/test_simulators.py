"""Unit tests for scenario simulators (Issues #13, #14, #15)."""

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import Project, Task, parse_file
from src.scenario.graph import DependencyGraph, build_dependency_graph
from src.scenario.parser import ActionType, ScenarioAction
from src.scenario.simulator import simulate, ScenarioResult, _calc_runway_weeks

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
REF_DATE = date(2026, 2, 19)


def _make_projects() -> list[Project]:
    """Create a small test portfolio."""
    return [
        Project(
            name="Alpha", status="In Progress",
            start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            budget=100_000, actual_spend=45_000,
            tasks=[Task(name="T1", status="In Progress", comments="Depends on Beta API")],
        ),
        Project(
            name="Beta", status="Planning",
            start_date=date(2026, 2, 1), end_date=date(2026, 8, 31),
            budget=150_000, actual_spend=10_000,
            tasks=[Task(name="T2", status="To Do")],
        ),
        Project(
            name="Gamma", status="At Risk",
            start_date=date(2025, 9, 1), end_date=date(2026, 4, 30),
            budget=200_000, actual_spend=185_000,
            tasks=[Task(name="T3", status="In Progress", comments="Depends on Alpha delivery")],
        ),
    ]


def _make_graph(projects: list[Project]) -> DependencyGraph:
    return build_dependency_graph(projects)


# ──────────────────────────────────────────────
# Budget simulator (Issue #13)
# ──────────────────────────────────────────────


class TestBudgetSimulator:

    def test_budget_increase_percentage(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_INCREASE, project="Beta", amount=0.20)
        result = simulate(action, projects, graph, REF_DATE)

        assert len(result.impacts) == 1
        assert result.impacts[0].project_name == "Beta"
        assert "150,000 → 180,000" in result.impacts[0].changes["budget"]

    def test_budget_increase_absolute(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_INCREASE, project="Beta", amount_absolute=50_000)
        result = simulate(action, projects, graph, REF_DATE)
        assert "150,000 → 200,000" in result.impacts[0].changes["budget"]

    def test_budget_decrease(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_DECREASE, project="Alpha", amount=0.10)
        result = simulate(action, projects, graph, REF_DATE)
        assert "100,000 → 90,000" in result.impacts[0].changes["budget"]

    def test_budget_decrease_below_spend_warns(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        # Decrease Gamma budget by 50% → 100k, but already spent 185k
        action = ScenarioAction(action=ActionType.BUDGET_DECREASE, project="Gamma", amount=0.50)
        result = simulate(action, projects, graph, REF_DATE)
        assert any("over budget" in w.lower() for w in result.warnings)

    def test_budget_decrease_floor_zero(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_DECREASE, project="Beta", amount=2.0)
        result = simulate(action, projects, graph, REF_DATE)
        assert "→ 0" in result.impacts[0].changes["budget"]

    def test_runway_changes(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_INCREASE, project="Gamma", amount=0.50)
        result = simulate(action, projects, graph, REF_DATE)
        assert "runway_weeks" in result.impacts[0].changes

    def test_after_state_updated(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_INCREASE, project="Beta", amount=0.20)
        result = simulate(action, projects, graph, REF_DATE)
        assert result.after_state["Beta"]["budget"] == 180_000


# ──────────────────────────────────────────────
# Scope cut simulator (Issue #14)
# ──────────────────────────────────────────────


class TestScopeCutSimulator:

    def test_scope_cut_30pct(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.SCOPE_CUT, project="Beta", amount=0.30)
        result = simulate(action, projects, graph, REF_DATE)

        direct = result.impacts[0]
        assert direct.project_name == "Beta"
        assert "100% → 70%" in direct.changes["scope"]

    def test_delivery_date_shifts(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.SCOPE_CUT, project="Beta", amount=0.30)
        result = simulate(action, projects, graph, REF_DATE)

        direct = result.impacts[0]
        assert int(direct.changes["days_saved"]) > 0

    def test_no_dates_handles_gracefully(self):
        projects = [Project(name="NoDates", status="Active", budget=100_000,
                            tasks=[Task(name="T1", status="To Do")])]
        graph = build_dependency_graph(projects)
        action = ScenarioAction(action=ActionType.SCOPE_CUT, project="NoDates", amount=0.20)
        result = simulate(action, projects, graph, REF_DATE)
        assert result.impacts[0].changes["days_saved"] == "0"

    def test_cascade_to_dependents(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        # Alpha depends on Beta, so cutting Beta scope should cascade
        if graph.get_all_dependents("Beta"):
            action = ScenarioAction(action=ActionType.SCOPE_CUT, project="Beta", amount=0.30)
            result = simulate(action, projects, graph, REF_DATE)
            cascade_impacts = [i for i in result.impacts if i.impact_type == "cascade"]
            assert len(cascade_impacts) > 0


# ──────────────────────────────────────────────
# Delay simulator (Issue #15)
# ──────────────────────────────────────────────


class TestDelaySimulator:

    def test_delay_shifts_dates(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.DELAY, project="Beta", duration_weeks=4)
        result = simulate(action, projects, graph, REF_DATE)

        direct = result.impacts[0]
        assert direct.project_name == "Beta"
        assert "delay_weeks" in direct.changes
        assert direct.changes["delay_weeks"] == "4"

    def test_end_date_shifted_correctly(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.DELAY, project="Beta", duration_weeks=4)
        result = simulate(action, projects, graph, REF_DATE)

        # Beta end date: 2026-08-31 + 28 days = 2026-09-28
        assert "2026-09-28" in result.after_state["Beta"]["end_date"]

    def test_cascade_delay_on_dependents(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        # Check if any project depends on Beta
        dependents = graph.get_all_dependents("Beta")
        if dependents:
            action = ScenarioAction(action=ActionType.DELAY, project="Beta", duration_weeks=4)
            result = simulate(action, projects, graph, REF_DATE)
            cascade = [i for i in result.impacts if i.impact_type == "cascade"]
            assert len(cascade) > 0
            assert any("cascade" in w.lower() for w in result.warnings)

    def test_no_dates_handles_gracefully(self):
        projects = [Project(name="NoDates", status="Active",
                            tasks=[Task(name="T1", status="To Do")])]
        graph = build_dependency_graph(projects)
        action = ScenarioAction(action=ActionType.DELAY, project="NoDates", duration_weeks=2)
        result = simulate(action, projects, graph, REF_DATE)
        assert "N/A" in result.impacts[0].changes["end_date"]


# ──────────────────────────────────────────────
# Remove simulator
# ──────────────────────────────────────────────


class TestRemoveSimulator:

    def test_remove_project(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="Beta")
        result = simulate(action, projects, graph, REF_DATE)

        direct = result.impacts[0]
        assert direct.project_name == "Beta"
        assert "Removed" in direct.changes["status"]

    def test_budget_freed_reported(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="Beta")
        result = simulate(action, projects, graph, REF_DATE)
        assert "150,000" in result.impacts[0].changes["budget_freed"]

    def test_remaining_budget_reported(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="Beta")
        result = simulate(action, projects, graph, REF_DATE)
        # Beta: 150k budget - 10k spent = 140k remaining
        assert "140,000" in result.impacts[0].changes["remaining_budget"]

    def test_broken_dependencies_flagged(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        dependents = graph.get_dependents("Beta")
        if dependents:
            action = ScenarioAction(action=ActionType.REMOVE, project="Beta")
            result = simulate(action, projects, graph, REF_DATE)
            assert any("break" in w.lower() for w in result.warnings)

    def test_after_state_marked_removed(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="Beta")
        result = simulate(action, projects, graph, REF_DATE)
        assert result.after_state["Beta"]["status"] == "Removed"


# ──────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────


class TestSimulatorEdgeCases:

    def test_unknown_project_warns(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="DoesNotExist")
        result = simulate(action, projects, graph, REF_DATE)
        assert any("not found" in w.lower() for w in result.warnings)

    def test_case_insensitive_project_match(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="beta")
        result = simulate(action, projects, graph, REF_DATE)
        assert result.impacts[0].project_name == "Beta"

    def test_result_serialisable(self):
        import json
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_INCREASE, project="Beta", amount=0.20)
        result = simulate(action, projects, graph, REF_DATE)
        json_str = json.dumps(result.to_dict())
        parsed = json.loads(json_str)
        assert "impacts" in parsed

    def test_before_state_captured(self):
        projects = _make_projects()
        graph = _make_graph(projects)
        action = ScenarioAction(action=ActionType.BUDGET_INCREASE, project="Beta", amount=0.20)
        result = simulate(action, projects, graph, REF_DATE)
        assert result.before_state["Beta"]["budget"] == 150_000


# ──────────────────────────────────────────────
# Runway helper
# ──────────────────────────────────────────────


class TestRunwayCalc:

    def test_runway_calculation(self):
        project = Project(
            name="Test", status="Active",
            start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            budget=100_000, actual_spend=50_000,
        )
        runway = _calc_runway_weeks(project, date(2026, 2, 19))
        assert runway is not None
        assert runway > 0

    def test_runway_zero_budget(self):
        project = Project(name="Test", status="Active", budget=0)
        assert _calc_runway_weeks(project, REF_DATE) is None

    def test_runway_no_dates(self):
        project = Project(name="Test", status="Active", budget=100_000, actual_spend=50_000)
        assert _calc_runway_weeks(project, REF_DATE) is None
