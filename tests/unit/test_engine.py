"""Unit tests for risk aggregation engine (Issue #9)."""

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import Project, Task, parse_file
from src.risk_engine.engine import (
    Risk,
    RiskCategory,
    RiskSeverity,
    ProjectRiskSummary,
    PortfolioRiskReport,
    analyse_portfolio,
    SEVERITY_ORDER,
)

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
REF_DATE = date(2026, 2, 19)


# ──────────────────────────────────────────────
# Dataclass and serialisation tests
# ──────────────────────────────────────────────


class TestRiskDataclass:

    def test_to_dict(self):
        risk = Risk(
            project_name="Alpha",
            category=RiskCategory.BLOCKED_WORK,
            severity=RiskSeverity.HIGH,
            title="Task blocked",
            explanation="Something is blocked",
            suggested_mitigation="Fix it",
        )
        d = risk.to_dict()
        assert d["project_name"] == "Alpha"
        assert d["category"] == "Blocked Work"
        assert d["severity"] == "High"
        assert d["title"] == "Task blocked"

    def test_default_mitigation(self):
        risk = Risk(
            project_name="Alpha",
            category=RiskCategory.BLOCKED_WORK,
            severity=RiskSeverity.HIGH,
            title="Test",
            explanation="Test",
        )
        assert risk.suggested_mitigation == ""


class TestProjectRiskSummary:

    def test_rag_red_critical(self):
        s = ProjectRiskSummary("Alpha", "Active", 3, RiskSeverity.CRITICAL)
        assert s.rag_status == "Red"

    def test_rag_red_high(self):
        s = ProjectRiskSummary("Alpha", "Active", 2, RiskSeverity.HIGH)
        assert s.rag_status == "Red"

    def test_rag_amber_medium(self):
        s = ProjectRiskSummary("Alpha", "Active", 1, RiskSeverity.MEDIUM)
        assert s.rag_status == "Amber"

    def test_rag_green_low(self):
        s = ProjectRiskSummary("Alpha", "Active", 1, RiskSeverity.LOW)
        assert s.rag_status == "Green"

    def test_rag_green_no_risks(self):
        s = ProjectRiskSummary("Alpha", "Active", 0, RiskSeverity.LOW)
        assert s.rag_status == "Green"

    def test_to_dict(self):
        s = ProjectRiskSummary("Alpha", "Active", 2, RiskSeverity.HIGH)
        d = s.to_dict()
        assert d["project_name"] == "Alpha"
        assert d["rag_status"] == "Red"
        assert d["risk_count"] == 2


class TestPortfolioRiskReport:

    def test_to_dict(self):
        report = PortfolioRiskReport(
            total_risks=5,
            projects_at_risk=2,
            portfolio_rag="Red",
        )
        d = report.to_dict()
        assert d["total_risks"] == 5
        assert d["portfolio_rag"] == "Red"


# ──────────────────────────────────────────────
# Aggregation tests with synthetic data
# ──────────────────────────────────────────────


class TestAnalysePortfolioSynthetic:

    def test_empty_portfolio(self):
        report = analyse_portfolio([])
        assert report.total_risks == 0
        assert report.projects_at_risk == 0
        assert report.portfolio_rag == "Green"

    def test_clean_project_green(self):
        project = Project(
            name="Clean", status="On Track",
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
            budget=100000, actual_spend=20000,
            tasks=[
                Task(name="T1", status="Done", priority="High"),
                Task(name="T2", status="In Progress", priority="Medium"),
            ],
        )
        report = analyse_portfolio([project], reference_date=REF_DATE)
        assert report.total_risks == 0
        assert report.portfolio_rag == "Green"

    def test_risky_project_flags(self):
        project = Project(
            name="Risky", status="At Risk",
            start_date=date(2025, 9, 1), end_date=date(2026, 4, 30),
            budget=200000, actual_spend=185000,
            tasks=[
                Task(name="T1", status="Blocked", priority="Critical",
                     comments="Blocked by vendor"),
                Task(name="T2", status="In Progress", priority="High",
                     sprint="Sprint 8",
                     previous_sprints=["S3", "S4", "S5", "S6", "S7"]),
            ],
        )
        report = analyse_portfolio([project], reference_date=REF_DATE)
        assert report.total_risks > 0
        assert report.projects_at_risk == 1
        assert report.portfolio_rag == "Red"

    def test_top_n_limits_risks(self):
        """Generate more than top_n risks and verify truncation."""
        tasks = [
            Task(name=f"Blocked-{i}", status="Blocked", priority="Medium")
            for i in range(10)
        ]
        project = Project(name="Many", status="Active", tasks=tasks)
        report = analyse_portfolio([project], top_n=3, reference_date=REF_DATE)
        summary = report.project_summaries[0]
        assert summary.risk_count == 3

    def test_risks_sorted_by_severity(self):
        project = Project(
            name="Mixed", status="Active",
            tasks=[
                Task(name="Low", status="Blocked", priority="Low"),
                Task(name="Critical", status="Blocked", priority="Critical",
                     comments="Blocked by vendor"),
                Task(name="Medium", status="On Hold", priority="Medium"),
            ],
        )
        report = analyse_portfolio([project], reference_date=REF_DATE)
        risks = report.project_summaries[0].risks
        severities = [r.severity for r in risks]
        severity_values = [SEVERITY_ORDER[s] for s in severities]
        assert severity_values == sorted(severity_values)

    def test_multiple_projects_sorted_worst_first(self):
        clean = Project(
            name="Clean", status="On Track",
            tasks=[Task(name="T1", status="Done", priority="Low")],
        )
        risky = Project(
            name="Risky", status="At Risk",
            tasks=[Task(name="T1", status="Blocked", priority="Critical")],
        )
        report = analyse_portfolio([clean, risky], reference_date=REF_DATE)
        names = [s.project_name for s in report.project_summaries]
        assert names[0] == "Risky"

    def test_all_four_detectors_run(self):
        """Project with risks from all 4 categories."""
        project = Project(
            name="Everything", status="At Risk",
            start_date=date(2025, 9, 1), end_date=date(2026, 4, 30),
            budget=200000, actual_spend=190000,
            tasks=[
                # Blocked
                Task(name="T1", status="Blocked", priority="High"),
                # Carry-over
                Task(name="T2", status="In Progress", priority="High",
                     previous_sprints=["S1", "S2", "S3", "S4"]),
                # Dependencies
                Task(name="T3", status="To Do", priority="High",
                     comments="Depends on T1. Waiting for T2"),
            ],
        )
        report = analyse_portfolio([project], top_n=10, reference_date=REF_DATE)
        categories = {r.category for r in report.project_summaries[0].risks}
        assert RiskCategory.BLOCKED_WORK in categories
        assert RiskCategory.CHRONIC_CARRYOVER in categories
        assert RiskCategory.BURN_RATE in categories
        assert RiskCategory.DEPENDENCY in categories


# ──────────────────────────────────────────────
# Integration with sample data
# ──────────────────────────────────────────────


class TestAnalysePortfolioSampleData:

    @pytest.fixture()
    def report(self) -> PortfolioRiskReport:
        projects = parse_file(SAMPLE_CSV)
        return analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)

    def test_six_project_summaries(self, report):
        assert len(report.project_summaries) == 6

    def test_portfolio_rag_is_red(self, report):
        """Portfolio should be Red — Gamma and Epsilon have Critical risks."""
        assert report.portfolio_rag == "Red"

    def test_projects_at_risk_count(self, report):
        """Multiple projects should have risks."""
        assert report.projects_at_risk >= 4  # Alpha, Beta, Gamma, Epsilon at minimum

    def test_total_risks_reasonable(self, report):
        """Should find meaningful number of risks across portfolio."""
        assert report.total_risks >= 10

    def test_gamma_is_worst(self, report):
        """Gamma (burn rate + carry-over) should be among the top."""
        gamma = next(s for s in report.project_summaries if s.project_name == "Gamma")
        assert gamma.rag_status == "Red"

    def test_epsilon_flagged(self, report):
        """Epsilon (96.7% budget consumed) should be Red."""
        epsilon = next(s for s in report.project_summaries if s.project_name == "Epsilon")
        assert epsilon.rag_status == "Red"

    def test_alpha_flagged(self, report):
        """Alpha has blocked work and dependencies → should have risks."""
        alpha = next(s for s in report.project_summaries if s.project_name == "Alpha")
        assert alpha.risk_count > 0

    def test_delta_lower_risk(self, report):
        """Delta is the healthy control case — fewer/lower risks."""
        delta = next(s for s in report.project_summaries if s.project_name == "Delta")
        assert delta.risk_count <= 2

    def test_serialisation_roundtrip(self, report):
        """to_dict should produce valid JSON-serialisable output."""
        import json
        d = report.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["portfolio_rag"] == "Red"
        assert len(parsed["project_summaries"]) == 6

    def test_each_risk_has_required_fields(self, report):
        for summary in report.project_summaries:
            for risk in summary.risks:
                assert risk.project_name
                assert risk.category
                assert risk.severity
                assert risk.title
                assert risk.explanation
