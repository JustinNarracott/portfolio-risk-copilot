"""Unit tests for burn rate alert detection (Issue #7)."""

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import Project, parse_file
from src.risk_engine.burnrate import detect_burn_rate, _burn_rate_severity, _fmt_pct, _fmt_currency
from src.risk_engine.engine import RiskCategory, RiskSeverity

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"

# Reference date for consistent testing (mid-February 2026)
REF_DATE = date(2026, 2, 19)


# ──────────────────────────────────────────────
# Helper tests
# ──────────────────────────────────────────────


class TestFormatHelpers:

    def test_fmt_pct(self):
        assert _fmt_pct(0.925) == "92%"

    def test_fmt_pct_100(self):
        assert _fmt_pct(1.0) == "100%"

    def test_fmt_currency(self):
        assert _fmt_currency(185000) == "185,000"

    def test_fmt_currency_large(self):
        assert _fmt_currency(1500000) == "1,500,000"


class TestBurnRateSeverity:

    def test_95pct_spent_is_critical(self):
        assert _burn_rate_severity(0.96, 0.15) == RiskSeverity.CRITICAL

    def test_90pct_with_20pct_remaining_is_critical(self):
        assert _burn_rate_severity(0.92, 0.25) == RiskSeverity.CRITICAL

    def test_90pct_with_12pct_remaining_is_high(self):
        assert _burn_rate_severity(0.91, 0.12) == RiskSeverity.HIGH


# ──────────────────────────────────────────────
# Detection tests with synthetic data
# ──────────────────────────────────────────────


class TestDetectBurnRateSynthetic:

    def test_high_spend_with_time_remaining(self):
        """92% spent with 40% time remaining → should flag."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            budget=100000, actual_spend=92000,
        )
        risks = detect_burn_rate(project, reference_date=date(2026, 3, 15))
        assert len(risks) == 1
        assert risks[0].category == RiskCategory.BURN_RATE

    def test_healthy_spend(self):
        """50% spent with 50% time remaining → should NOT flag."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
            budget=100000, actual_spend=50000,
        )
        risks = detect_burn_rate(project, reference_date=date(2026, 7, 1))
        assert len(risks) == 0

    def test_overspend_flagged(self):
        """Actual > budget → Critical overspend risk."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            budget=100000, actual_spend=110000,
        )
        risks = detect_burn_rate(project, reference_date=date(2026, 3, 15))
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.CRITICAL
        assert "exceeded budget" in risks[0].title.lower()

    def test_zero_budget_skipped(self):
        """Projects with no budget should be skipped."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            budget=0, actual_spend=0,
        )
        risks = detect_burn_rate(project)
        assert len(risks) == 0

    def test_no_dates_high_spend_still_flags(self):
        """90%+ spend without dates → High severity warning."""
        project = Project(
            name="TestProject", status="In Progress",
            budget=100000, actual_spend=95000,
        )
        risks = detect_burn_rate(project)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.HIGH
        assert "timeline data" in risks[0].explanation.lower() or "unavailable" in risks[0].explanation.lower()

    def test_no_dates_low_spend_ok(self):
        """50% spend without dates → no flag."""
        project = Project(
            name="TestProject", status="In Progress",
            budget=100000, actual_spend=50000,
        )
        risks = detect_burn_rate(project)
        assert len(risks) == 0

    def test_project_near_end_high_spend_ok(self):
        """95% spent with only 5% time remaining → NOT flagged (time_remaining < threshold)."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            budget=100000, actual_spend=95000,
        )
        # Reference date near end: ~95% through
        risks = detect_burn_rate(project, reference_date=date(2026, 6, 20))
        assert len(risks) == 0

    def test_reference_date_defaults_to_today(self):
        """Should work without explicit reference_date."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2020, 1, 1), end_date=date(2020, 12, 31),
            budget=100000, actual_spend=95000,
        )
        # Project end date is in the past, so time_remaining will be 0
        risks = detect_burn_rate(project)
        assert len(risks) == 0  # Past end date, no time remaining

    def test_explanation_is_plain_english(self):
        project = Project(
            name="Gamma", status="At Risk",
            start_date=date(2025, 9, 1), end_date=date(2026, 4, 30),
            budget=200000, actual_spend=185000,
        )
        risks = detect_burn_rate(project, reference_date=REF_DATE)
        assert len(risks) == 1
        explanation = risks[0].explanation
        assert "Gamma" in explanation
        assert "185,000" in explanation
        assert "200,000" in explanation

    def test_mitigation_provided(self):
        project = Project(
            name="Gamma", status="At Risk",
            start_date=date(2025, 9, 1), end_date=date(2026, 4, 30),
            budget=200000, actual_spend=185000,
        )
        risks = detect_burn_rate(project, reference_date=REF_DATE)
        assert risks[0].suggested_mitigation != ""
        assert "steering committee" in risks[0].suggested_mitigation.lower()

    def test_zero_duration_project_skipped(self):
        """Project with same start and end date should be skipped."""
        project = Project(
            name="TestProject", status="In Progress",
            start_date=date(2026, 3, 1), end_date=date(2026, 3, 1),
            budget=100000, actual_spend=95000,
        )
        risks = detect_burn_rate(project, reference_date=date(2026, 3, 1))
        # Zero duration → still should flag via no-dates path since division would fail
        # Actually total_duration=0 → returns []
        assert len(risks) == 0


# ──────────────────────────────────────────────
# Detection tests with sample data
# ──────────────────────────────────────────────


class TestDetectBurnRateSampleData:

    @pytest.fixture()
    def projects(self) -> list[Project]:
        return parse_file(SAMPLE_CSV)

    def test_gamma_flagged(self, projects):
        """Gamma: 185k/200k (92.5%) spent with ~2.5 months remaining → should flag."""
        gamma = next(p for p in projects if p.name == "Gamma")
        risks = detect_burn_rate(gamma, reference_date=REF_DATE)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.CRITICAL

    def test_epsilon_flagged(self, projects):
        """Epsilon: 58k/60k (96.7%) spent with ~1.5 months remaining → should flag."""
        epsilon = next(p for p in projects if p.name == "Epsilon")
        risks = detect_burn_rate(epsilon, reference_date=REF_DATE)
        assert len(risks) == 1
        assert risks[0].severity == RiskSeverity.CRITICAL

    def test_alpha_not_flagged(self, projects):
        """Alpha: 45k/100k (45%) → healthy, should NOT flag."""
        alpha = next(p for p in projects if p.name == "Alpha")
        risks = detect_burn_rate(alpha, reference_date=REF_DATE)
        assert len(risks) == 0

    def test_beta_not_flagged(self, projects):
        """Beta: 10k/150k (6.7%) → very early, should NOT flag."""
        beta = next(p for p in projects if p.name == "Beta")
        risks = detect_burn_rate(beta, reference_date=REF_DATE)
        assert len(risks) == 0

    def test_zeta_not_flagged(self, projects):
        """Zeta: 15k/120k (12.5%) → healthy, should NOT flag."""
        zeta = next(p for p in projects if p.name == "Zeta")
        risks = detect_burn_rate(zeta, reference_date=REF_DATE)
        assert len(risks) == 0

    def test_delta_not_flagged(self, projects):
        """Delta: 22k/80k (27.5%) → healthy, should NOT flag."""
        delta = next(p for p in projects if p.name == "Delta")
        risks = detect_burn_rate(delta, reference_date=REF_DATE)
        assert len(risks) == 0
