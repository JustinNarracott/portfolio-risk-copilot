"""Unit tests for dependency keyword scanner (Issue #8)."""

from pathlib import Path

import pytest

from src.ingestion.parser import Project, Task, parse_file
from src.risk_engine.dependencies import (
    detect_dependencies,
    _is_active,
    _find_dependency_matches,
    _extract_context,
)
from src.risk_engine.engine import RiskCategory, RiskSeverity

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"


# ──────────────────────────────────────────────
# Helper tests
# ──────────────────────────────────────────────


class TestIsActive:

    def test_in_progress(self):
        assert _is_active(Task(name="T", status="In Progress")) is True

    def test_to_do(self):
        assert _is_active(Task(name="T", status="To Do")) is True

    def test_blocked(self):
        assert _is_active(Task(name="T", status="Blocked")) is True

    def test_done_not_active(self):
        assert _is_active(Task(name="T", status="Done")) is False

    def test_complete_not_active(self):
        assert _is_active(Task(name="T", status="Complete")) is False

    def test_case_insensitive(self):
        assert _is_active(Task(name="T", status="IN PROGRESS")) is True


class TestFindDependencyMatches:

    def test_depends_on(self):
        task = Task(name="T", status="To Do", comments="Depends on API completion")
        matches = _find_dependency_matches(task)
        assert len(matches) == 1
        assert matches[0]["keyword"] == "depends on"
        assert "API completion" in matches[0]["context"]

    def test_blocked_by(self):
        task = Task(name="T", status="To Do", comments="Blocked by infrastructure team")
        matches = _find_dependency_matches(task)
        assert len(matches) == 1
        assert "infrastructure" in matches[0]["context"]

    def test_multiple_keywords(self):
        task = Task(name="T", status="To Do",
                    comments="Depends on API. Also waiting for vendor approval")
        matches = _find_dependency_matches(task)
        assert len(matches) == 2

    def test_no_keywords(self):
        task = Task(name="T", status="To Do", comments="Making progress")
        matches = _find_dependency_matches(task)
        assert len(matches) == 0

    def test_empty_comments(self):
        task = Task(name="T", status="To Do", comments="")
        matches = _find_dependency_matches(task)
        assert len(matches) == 0

    def test_case_insensitive(self):
        task = Task(name="T", status="To Do", comments="DEPENDS ON the API team")
        matches = _find_dependency_matches(task)
        assert len(matches) == 1

    def test_prerequisite_keyword(self):
        task = Task(name="T", status="To Do",
                    comments="Prerequisite: all APIs must be deployed")
        matches = _find_dependency_matches(task)
        assert len(matches) == 1


class TestExtractContext:

    def test_extracts_after_keyword(self):
        text = "Depends on API completion from Bob"
        context = _extract_context(text, 0, "Depends on")
        assert context == "API completion from Bob"

    def test_stops_at_sentence_boundary(self):
        text = "Depends on API. Also needs testing"
        context = _extract_context(text, 0, "Depends on")
        assert context == "API"

    def test_strips_leading_colon(self):
        text = "Prerequisite: all APIs deployed"
        context = _extract_context(text, 0, "Prerequisite")
        assert context == "all APIs deployed"

    def test_truncates_long_context(self):
        text = "Depends on " + "a" * 200
        context = _extract_context(text, 0, "Depends on")
        assert len(context) <= 80


# ──────────────────────────────────────────────
# Detection tests with synthetic data
# ──────────────────────────────────────────────


class TestDetectDependenciesSynthetic:

    def _make_project(self, tasks: list[Task]) -> Project:
        return Project(name="TestProject", status="In Progress", tasks=tasks)

    def test_single_dependency(self):
        project = self._make_project([
            Task(name="Build API", status="To Do", priority="High",
                 comments="Depends on database migration"),
        ])
        risks = detect_dependencies(project)
        assert len(risks) == 1
        assert risks[0].category == RiskCategory.DEPENDENCY
        assert "1 dependency" in risks[0].title

    def test_multiple_dependencies_elevates_severity(self):
        project = self._make_project([
            Task(name="Build API", status="To Do", priority="Medium",
                 comments="Depends on auth service. Waiting for vendor API. Requires infra setup"),
        ])
        risks = detect_dependencies(project)
        assert len(risks) == 1
        assert "3 dependencies" in risks[0].title
        assert risks[0].severity == RiskSeverity.HIGH  # Medium + 3 deps → High

    def test_completed_task_skipped(self):
        project = self._make_project([
            Task(name="Build API", status="Done", priority="High",
                 comments="Depends on database migration"),
        ])
        risks = detect_dependencies(project)
        assert len(risks) == 0

    def test_no_dependencies(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 comments="Making good progress on this"),
        ])
        risks = detect_dependencies(project)
        assert len(risks) == 0

    def test_sorted_by_severity(self):
        project = self._make_project([
            Task(name="Low task", status="To Do", priority="Low",
                 comments="Depends on something"),
            Task(name="Critical task", status="To Do", priority="Critical",
                 comments="Depends on something else"),
        ])
        risks = detect_dependencies(project)
        assert risks[0].severity == RiskSeverity.CRITICAL
        assert risks[1].severity == RiskSeverity.LOW

    def test_explanation_includes_context(self):
        project = self._make_project([
            Task(name="Build API", status="To Do", priority="High",
                 assignee="Alice", comments="Depends on auth service completion"),
        ])
        risks = detect_dependencies(project)
        assert "Alice" in risks[0].explanation
        assert "auth service" in risks[0].explanation

    def test_mitigation_provided(self):
        project = self._make_project([
            Task(name="Build API", status="To Do", priority="High",
                 comments="Depends on auth service"),
        ])
        risks = detect_dependencies(project)
        assert risks[0].suggested_mitigation != ""

    def test_empty_project(self):
        project = self._make_project([])
        assert detect_dependencies(project) == []


# ──────────────────────────────────────────────
# Detection tests with sample data
# ──────────────────────────────────────────────


class TestDetectDependenciesSampleData:

    @pytest.fixture()
    def projects(self) -> list[Project]:
        return parse_file(SAMPLE_CSV)

    def test_alpha_has_dependencies(self, projects):
        """Alpha has multiple tasks with dependency keywords."""
        alpha = next(p for p in projects if p.name == "Alpha")
        risks = detect_dependencies(alpha)
        assert len(risks) > 0

    def test_alpha_frontend_depends_on_api(self, projects):
        """Alpha's frontend dashboard depends on API completion."""
        alpha = next(p for p in projects if p.name == "Alpha")
        risks = detect_dependencies(alpha)
        frontend_risks = [r for r in risks if "frontend" in r.title.lower() or "dashboard" in r.title.lower()]
        assert len(frontend_risks) > 0

    def test_alpha_tests_depend_on_multiple(self, projects):
        """Alpha's integration tests wait for auth API and payment gateway."""
        alpha = next(p for p in projects if p.name == "Alpha")
        risks = detect_dependencies(alpha)
        test_risks = [r for r in risks if "write" in r.title.lower() or "test" in r.title.lower()]
        assert len(test_risks) > 0

    def test_delta_low_dependency_risk(self, projects):
        """Delta has minimal dependency indicators."""
        delta = next(p for p in projects if p.name == "Delta")
        risks = detect_dependencies(delta)
        # Delta has some "Depends on" in comments but fewer than other projects
        assert len(risks) <= 2

    def test_zeta_has_dependency(self, projects):
        """Zeta's tech architecture depends on product strategy."""
        zeta = next(p for p in projects if p.name == "Zeta")
        risks = detect_dependencies(zeta)
        arch_risks = [r for r in risks if "architecture" in r.title.lower()]
        assert len(arch_risks) > 0

    def test_all_risks_have_explanations(self, projects):
        for project in projects:
            risks = detect_dependencies(project)
            for risk in risks:
                assert risk.explanation, f"Empty explanation: {risk.title}"
                assert risk.suggested_mitigation, f"Empty mitigation: {risk.title}"
