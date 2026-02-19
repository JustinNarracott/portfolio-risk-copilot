"""Unit tests for chronic carry-over detection (Issue #6)."""

from pathlib import Path

import pytest

from src.ingestion.parser import Project, Task, parse_file
from src.risk_engine.carryover import detect_carryover, _is_complete, _calculate_severity
from src.risk_engine.engine import RiskCategory, RiskSeverity

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"


# ──────────────────────────────────────────────
# Helper tests
# ──────────────────────────────────────────────


class TestIsComplete:

    def test_done(self):
        assert _is_complete(Task(name="T", status="Done")) is True

    def test_complete(self):
        assert _is_complete(Task(name="T", status="Complete")) is True

    def test_completed(self):
        assert _is_complete(Task(name="T", status="Completed")) is True

    def test_closed(self):
        assert _is_complete(Task(name="T", status="Closed")) is True

    def test_resolved(self):
        assert _is_complete(Task(name="T", status="Resolved")) is True

    def test_in_progress_not_complete(self):
        assert _is_complete(Task(name="T", status="In Progress")) is False

    def test_blocked_not_complete(self):
        assert _is_complete(Task(name="T", status="Blocked")) is False

    def test_case_insensitive(self):
        assert _is_complete(Task(name="T", status="DONE")) is True


class TestCalculateSeverity:

    def test_critical_priority(self):
        task = Task(name="T", status="In Progress", priority="Critical")
        assert _calculate_severity(task, 3) == RiskSeverity.CRITICAL

    def test_high_priority(self):
        task = Task(name="T", status="In Progress", priority="High")
        assert _calculate_severity(task, 3) == RiskSeverity.HIGH

    def test_medium_priority(self):
        task = Task(name="T", status="In Progress", priority="Medium")
        assert _calculate_severity(task, 3) == RiskSeverity.MEDIUM

    def test_elevated_at_5_sprints(self):
        task = Task(name="T", status="In Progress", priority="High")
        assert _calculate_severity(task, 5) == RiskSeverity.CRITICAL  # High → Critical

    def test_medium_elevated_at_5_sprints(self):
        task = Task(name="T", status="In Progress", priority="Medium")
        assert _calculate_severity(task, 5) == RiskSeverity.HIGH  # Medium → High

    def test_critical_stays_critical_at_5(self):
        task = Task(name="T", status="In Progress", priority="Critical")
        assert _calculate_severity(task, 5) == RiskSeverity.CRITICAL


# ──────────────────────────────────────────────
# Detection tests with synthetic data
# ──────────────────────────────────────────────


class TestDetectCarryoverSynthetic:

    def _make_project(self, tasks: list[Task]) -> Project:
        return Project(name="TestProject", status="In Progress", tasks=tasks)

    def test_task_with_3_previous_sprints_flagged(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 sprint="Sprint 6", previous_sprints=["Sprint 3", "Sprint 4", "Sprint 5"]),
        ])
        risks = detect_carryover(project)
        assert len(risks) == 1
        assert risks[0].category == RiskCategory.CHRONIC_CARRYOVER
        assert "3 sprints" in risks[0].title

    def test_task_with_2_previous_sprints_not_flagged(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 sprint="Sprint 5", previous_sprints=["Sprint 3", "Sprint 4"]),
        ])
        risks = detect_carryover(project)
        assert len(risks) == 0

    def test_completed_task_not_flagged(self):
        """Completed tasks should not be flagged even with many carry-overs."""
        project = self._make_project([
            Task(name="Build API", status="Done", priority="High",
                 sprint="Sprint 6", previous_sprints=["Sprint 3", "Sprint 4", "Sprint 5"]),
        ])
        risks = detect_carryover(project)
        assert len(risks) == 0

    def test_custom_threshold(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 sprint="Sprint 4", previous_sprints=["Sprint 2", "Sprint 3"]),
        ])
        risks = detect_carryover(project, threshold=2)
        assert len(risks) == 1

    def test_no_previous_sprints(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 sprint="Sprint 3", previous_sprints=[]),
        ])
        risks = detect_carryover(project)
        assert len(risks) == 0

    def test_multiple_tasks_sorted_by_severity(self):
        project = self._make_project([
            Task(name="Low task", status="In Progress", priority="Low",
                 previous_sprints=["S1", "S2", "S3"]),
            Task(name="Critical task", status="In Progress", priority="Critical",
                 previous_sprints=["S1", "S2", "S3"]),
        ])
        risks = detect_carryover(project)
        assert len(risks) == 2
        assert risks[0].severity == RiskSeverity.CRITICAL
        assert risks[1].severity == RiskSeverity.LOW

    def test_explanation_includes_sprint_history(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 sprint="Sprint 6", previous_sprints=["Sprint 3", "Sprint 4", "Sprint 5"],
                 assignee="Alice"),
        ])
        risks = detect_carryover(project)
        explanation = risks[0].explanation
        assert "Sprint 3" in explanation
        assert "Sprint 6" in explanation
        assert "Alice" in explanation
        assert "3 sprints" in explanation

    def test_mitigation_provided(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 previous_sprints=["S1", "S2", "S3"]),
        ])
        risks = detect_carryover(project)
        assert risks[0].suggested_mitigation != ""
        assert "re-scoped" in risks[0].suggested_mitigation.lower() or "broken" in risks[0].suggested_mitigation.lower()

    def test_empty_project(self):
        project = self._make_project([])
        risks = detect_carryover(project)
        assert risks == []


# ──────────────────────────────────────────────
# Detection tests with sample data
# ──────────────────────────────────────────────


class TestDetectCarryoverSampleData:

    @pytest.fixture()
    def projects(self) -> list[Project]:
        return parse_file(SAMPLE_CSV)

    def test_gamma_core_migration_flagged(self, projects):
        """Gamma's core platform migration has 4 previous sprints — should flag."""
        gamma = next(p for p in projects if p.name == "Gamma")
        risks = detect_carryover(gamma)
        migration_risks = [r for r in risks if "core platform migration" in r.title.lower()]
        assert len(migration_risks) == 1
        assert "4 sprints" in migration_risks[0].title

    def test_gamma_data_migration_not_flagged(self, projects):
        """Gamma's data migration pipeline has 2 previous sprints — below threshold."""
        gamma = next(p for p in projects if p.name == "Gamma")
        risks = detect_carryover(gamma)
        data_risks = [r for r in risks if "data migration pipeline" in r.title.lower()]
        assert len(data_risks) == 0

    def test_epsilon_audit_not_flagged_at_default(self, projects):
        """Epsilon's regulatory audit has 2 previous sprints — below default threshold of 3."""
        epsilon = next(p for p in projects if p.name == "Epsilon")
        risks = detect_carryover(epsilon)
        audit_risks = [r for r in risks if "regulatory" in r.title.lower()]
        assert len(audit_risks) == 0

    def test_epsilon_audit_flagged_at_threshold_2(self, projects):
        """Epsilon's regulatory audit flags with threshold=2."""
        epsilon = next(p for p in projects if p.name == "Epsilon")
        risks = detect_carryover(epsilon, threshold=2)
        audit_risks = [r for r in risks if "regulatory" in r.title.lower()]
        assert len(audit_risks) == 1

    def test_delta_no_carryover(self, projects):
        """Delta has minimal carry-over — control case."""
        delta = next(p for p in projects if p.name == "Delta")
        risks = detect_carryover(delta)
        assert len(risks) == 0

    def test_zeta_no_carryover(self, projects):
        """Zeta has no carry-over — control case."""
        zeta = next(p for p in projects if p.name == "Zeta")
        risks = detect_carryover(zeta)
        assert len(risks) == 0
