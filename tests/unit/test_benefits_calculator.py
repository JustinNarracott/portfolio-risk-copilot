"""Unit tests for benefits calculator & drift detection (Issue #30)."""

from datetime import date
from pathlib import Path

import pytest

from src.benefits.parser import parse_benefits, Benefit, BenefitStatus, BenefitCategory, BenefitConfidence
from src.benefits.calculator import analyse_benefits, DriftRAG, PortfolioBenefitReport
from src.ingestion.parser import parse_file
from src.risk_engine.engine import analyse_portfolio

SAMPLE_BENEFITS = Path(__file__).parent.parent.parent / "sample-data" / "benefit-tracker-sample.csv"
SAMPLE_PROJECTS = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
REF_DATE = date(2026, 2, 19)


@pytest.fixture()
def benefits():
    return parse_benefits(SAMPLE_BENEFITS)


@pytest.fixture()
def risk_report():
    projects = parse_file(SAMPLE_PROJECTS)
    return analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)


class TestAnalyseBenefits:

    def test_returns_report(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert isinstance(report, PortfolioBenefitReport)

    def test_total_expected(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert report.total_expected == 2750000  # 500k + 750k + 300k + 200k + 0 + 1M

    def test_total_realised(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert report.total_realised == 150000  # Only Gamma has realised

    def test_realisation_pct(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert report.realisation_pct == pytest.approx(150000 / 2750000, abs=0.01)

    def test_drift_detected(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert report.portfolio_drift_pct > 0  # Should detect drift given Red projects

    def test_adjusted_less_than_expected(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert report.total_adjusted < report.total_expected

    def test_project_summaries_count(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert len(report.project_summaries) == 6

    def test_at_risk_value_positive(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert report.total_at_risk_value > 0

    def test_recommendations_generated(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert len(report.recommendations) >= 1

    def test_top_benefits_at_risk(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        assert len(report.top_benefits_at_risk) >= 1

    def test_to_dict(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        d = report.to_dict()
        assert "total_expected" in d
        assert "portfolio_drift_pct" in d
        assert "recommendations" in d


class TestProjectDrift:

    def test_gamma_partial_realisation(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        gamma = [s for s in report.project_summaries if s.project_name == "Gamma"][0]
        assert gamma.total_realised == 150000
        assert gamma.realisation_pct == pytest.approx(0.5, abs=0.01)

    def test_epsilon_at_risk(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        epsilon = [s for s in report.project_summaries if s.project_name == "Epsilon"][0]
        assert len(epsilon.benefits_at_risk) >= 1

    def test_drift_explanations_plain_english(self, benefits, risk_report):
        report = analyse_benefits(benefits, risk_report, REF_DATE)
        for s in report.project_summaries:
            if s.drift_pct > 0.05:
                assert "£" in s.drift_explanation
                assert "drift" in s.drift_explanation.lower() or "forecast" in s.drift_explanation.lower()


class TestDriftRAGThresholds:

    def test_green_under_15(self):
        from src.benefits.calculator import _drift_rag
        assert _drift_rag(0.10) == DriftRAG.GREEN

    def test_amber_15_to_30(self):
        from src.benefits.calculator import _drift_rag
        assert _drift_rag(0.20) == DriftRAG.AMBER

    def test_red_over_30(self):
        from src.benefits.calculator import _drift_rag
        assert _drift_rag(0.35) == DriftRAG.RED


class TestWithoutRiskReport:

    def test_works_without_risk_report(self, benefits):
        report = analyse_benefits(benefits, None, REF_DATE)
        assert report.total_expected > 0
        assert len(report.project_summaries) == 6
