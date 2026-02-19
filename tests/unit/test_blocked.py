"""Unit tests for blocked work detection (Issue #5)."""

from pathlib import Path

import pytest

from src.ingestion.parser import Project, Task, parse_file
from src.risk_engine.blocked import (
    detect_blocked_work,
    _is_status_blocked,
    _has_blocker_keyword,
    _severity_from_priority,
    _elevate_severity,
)
from src.risk_engine.engine import RiskCategory, RiskSeverity

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"


# ──────────────────────────────────────────────
# Helper function tests
# ──────────────────────────────────────────────


class TestStatusBlocked:

    def test_blocked_status(self):
        task = Task(name="T1", status="Blocked")
        assert _is_status_blocked(task) is True

    def test_on_hold_status(self):
        task = Task(name="T1", status="On Hold")
        assert _is_status_blocked(task) is True

    def test_waiting_status(self):
        task = Task(name="T1", status="Waiting")
        assert _is_status_blocked(task) is True

    def test_in_progress_not_blocked(self):
        task = Task(name="T1", status="In Progress")
        assert _is_status_blocked(task) is False

    def test_done_not_blocked(self):
        task = Task(name="T1", status="Done")
        assert _is_status_blocked(task) is False

    def test_case_insensitive(self):
        task = Task(name="T1", status="BLOCKED")
        assert _is_status_blocked(task) is True

    def test_whitespace_stripped(self):
        task = Task(name="T1", status="  On Hold  ")
        assert _is_status_blocked(task) is True


class TestBlockerKeywords:

    def test_blocked_by_keyword(self):
        task = Task(name="T1", status="In Progress", comments="Blocked by infrastructure team")
        found, context = _has_blocker_keyword(task)
        assert found is True
        assert "Blocked by infrastructure" in context

    def test_waiting_for_keyword(self):
        task = Task(name="T1", status="In Progress", comments="Waiting for vendor response")
        found, context = _has_blocker_keyword(task)
        assert found is True
        assert "Waiting for vendor" in context

    def test_no_keyword(self):
        task = Task(name="T1", status="In Progress", comments="Making good progress on this")
        found, context = _has_blocker_keyword(task)
        assert found is False
        assert context == ""

    def test_empty_comments(self):
        task = Task(name="T1", status="In Progress", comments="")
        found, context = _has_blocker_keyword(task)
        assert found is False

    def test_case_insensitive(self):
        task = Task(name="T1", status="In Progress", comments="BLOCKED BY the API team")
        found, _ = _has_blocker_keyword(task)
        assert found is True

    def test_stalled_keyword(self):
        task = Task(name="T1", status="In Progress", comments="Work has stalled due to resource issues")
        found, _ = _has_blocker_keyword(task)
        assert found is True


class TestSeverityMapping:

    def test_critical_priority(self):
        assert _severity_from_priority("Critical") == RiskSeverity.CRITICAL

    def test_high_priority(self):
        assert _severity_from_priority("High") == RiskSeverity.HIGH

    def test_medium_priority(self):
        assert _severity_from_priority("Medium") == RiskSeverity.MEDIUM

    def test_low_priority(self):
        assert _severity_from_priority("Low") == RiskSeverity.LOW

    def test_unknown_defaults_to_medium(self):
        assert _severity_from_priority("Unknown") == RiskSeverity.MEDIUM

    def test_case_insensitive(self):
        assert _severity_from_priority("HIGH") == RiskSeverity.HIGH


class TestSeverityElevation:

    def test_low_to_medium(self):
        assert _elevate_severity(RiskSeverity.LOW) == RiskSeverity.MEDIUM

    def test_medium_to_high(self):
        assert _elevate_severity(RiskSeverity.MEDIUM) == RiskSeverity.HIGH

    def test_high_to_critical(self):
        assert _elevate_severity(RiskSeverity.HIGH) == RiskSeverity.CRITICAL

    def test_critical_stays_critical(self):
        assert _elevate_severity(RiskSeverity.CRITICAL) == RiskSeverity.CRITICAL


# ──────────────────────────────────────────────
# Detection tests with synthetic data
# ──────────────────────────────────────────────


class TestDetectBlockedWorkSynthetic:

    def _make_project(self, tasks: list[Task]) -> Project:
        return Project(name="TestProject", status="In Progress", tasks=tasks)

    def test_status_blocked_detected(self):
        project = self._make_project([
            Task(name="Build API", status="Blocked", priority="High"),
        ])
        risks = detect_blocked_work(project)
        assert len(risks) == 1
        assert risks[0].category == RiskCategory.BLOCKED_WORK
        assert risks[0].severity == RiskSeverity.HIGH

    def test_comment_blocked_detected(self):
        project = self._make_project([
            Task(name="Build API", status="In Progress", priority="High",
                 comments="Blocked by infrastructure team"),
        ])
        risks = detect_blocked_work(project)
        assert len(risks) == 1
        assert "blocker in comments" in risks[0].title.lower()

    def test_both_status_and_comment_elevates_severity(self):
        project = self._make_project([
            Task(name="Build API", status="Blocked", priority="High",
                 comments="Blocked by vendor API changes"),
        ])
        risks = detect_blocked_work(project)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.CRITICAL  # High → Critical

    def test_no_blocked_tasks(self):
        project = self._make_project([
            Task(name="Build API", status="Done", priority="High"),
            Task(name="Write tests", status="In Progress", priority="Medium"),
        ])
        risks = detect_blocked_work(project)
        assert len(risks) == 0

    def test_multiple_blocked_tasks(self):
        project = self._make_project([
            Task(name="Task A", status="Blocked", priority="Critical"),
            Task(name="Task B", status="On Hold", priority="Low"),
            Task(name="Task C", status="Done", priority="High"),
        ])
        risks = detect_blocked_work(project)
        assert len(risks) == 2
        assert risks[0].severity == RiskSeverity.CRITICAL  # Task A
        assert risks[1].severity == RiskSeverity.LOW  # Task B

    def test_sorted_by_severity(self):
        project = self._make_project([
            Task(name="Low task", status="Blocked", priority="Low"),
            Task(name="Critical task", status="Blocked", priority="Critical"),
            Task(name="Medium task", status="On Hold", priority="Medium"),
        ])
        risks = detect_blocked_work(project)
        severities = [r.severity for r in risks]
        assert severities == [RiskSeverity.CRITICAL, RiskSeverity.MEDIUM, RiskSeverity.LOW]

    def test_explanation_is_plain_english(self):
        project = self._make_project([
            Task(name="Build API", status="Blocked", priority="High",
                 assignee="Bob", comments="Blocked by infra team"),
        ])
        risks = detect_blocked_work(project)
        explanation = risks[0].explanation
        assert "TestProject" in explanation
        assert "Build API" in explanation
        assert "Bob" in explanation
        assert "high-priority" in explanation

    def test_mitigation_provided(self):
        project = self._make_project([
            Task(name="Build API", status="Blocked", priority="High"),
        ])
        risks = detect_blocked_work(project)
        assert risks[0].suggested_mitigation != ""
        assert "escalat" in risks[0].suggested_mitigation.lower()

    def test_empty_project(self):
        project = self._make_project([])
        risks = detect_blocked_work(project)
        assert risks == []

    def test_unassigned_task(self):
        project = self._make_project([
            Task(name="Build API", status="Blocked", priority="High", assignee=""),
        ])
        risks = detect_blocked_work(project)
        assert "unassigned" in risks[0].explanation


# ──────────────────────────────────────────────
# Detection tests with sample data
# ──────────────────────────────────────────────


class TestDetectBlockedWorkSampleData:
    """Tests using the real sample Jira export."""

    @pytest.fixture()
    def projects(self) -> list[Project]:
        return parse_file(SAMPLE_CSV)

    def test_alpha_blocked_tasks(self, projects):
        """Alpha has payment gateway (Blocked status + comment) and auth API (comment only)."""
        alpha = next(p for p in projects if p.name == "Alpha")
        risks = detect_blocked_work(alpha)

        risk_titles = [r.title for r in risks]
        # Payment gateway is Blocked status
        assert any("payment gateway" in t.lower() for t in risk_titles)
        # Auth API has "Blocked by" in comments
        assert any("authentication" in t.lower() for t in risk_titles)

    def test_alpha_payment_gateway_severity(self, projects):
        """Payment gateway is Critical priority + Blocked status + comment = Critical severity."""
        alpha = next(p for p in projects if p.name == "Alpha")
        risks = detect_blocked_work(alpha)
        payment_risk = next(r for r in risks if "payment gateway" in r.title.lower())
        assert payment_risk.severity == RiskSeverity.CRITICAL

    def test_epsilon_on_hold_tasks(self, projects):
        """Epsilon has staff training on hold."""
        epsilon = next(p for p in projects if p.name == "Epsilon")
        risks = detect_blocked_work(epsilon)
        assert any("staff training" in r.title.lower() for r in risks)

    def test_gamma_on_hold_task(self, projects):
        """Gamma has user training material on hold."""
        gamma = next(p for p in projects if p.name == "Gamma")
        risks = detect_blocked_work(gamma)
        assert any("training material" in r.title.lower() for r in risks)

    def test_delta_low_risk(self, projects):
        """Delta has no blocked tasks (control case)."""
        delta = next(p for p in projects if p.name == "Delta")
        risks = detect_blocked_work(delta)
        assert len(risks) == 0

    def test_zeta_low_risk(self, projects):
        """Zeta has no blocked tasks (control case)."""
        zeta = next(p for p in projects if p.name == "Zeta")
        risks = detect_blocked_work(zeta)
        assert len(risks) == 0

    def test_all_risks_have_explanations(self, projects):
        """Every detected risk has a non-empty explanation."""
        for project in projects:
            risks = detect_blocked_work(project)
            for risk in risks:
                assert risk.explanation, f"Empty explanation for {risk.title}"
                assert risk.suggested_mitigation, f"Empty mitigation for {risk.title}"
