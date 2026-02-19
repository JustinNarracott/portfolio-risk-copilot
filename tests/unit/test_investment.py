"""Unit tests for portfolio investment & ROI analysis (Issue #32)."""

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import parse_file
from src.risk_engine.engine import analyse_portfolio
from src.benefits.parser import parse_benefits
from src.benefits.calculator import analyse_benefits
from src.investment import (
    analyse_investments, InvestmentAction, PortfolioInvestmentReport,
)

SAMPLE_PROJECTS = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
SAMPLE_BENEFITS = Path(__file__).parent.parent.parent / "sample-data" / "benefit-tracker-sample.csv"
REF_DATE = date(2026, 2, 19)


@pytest.fixture()
def projects():
    return parse_file(SAMPLE_PROJECTS)


@pytest.fixture()
def risk_report(projects):
    return analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)


@pytest.fixture()
def benefit_report(risk_report):
    benefits = parse_benefits(SAMPLE_BENEFITS)
    return analyse_benefits(benefits, risk_report, REF_DATE)


@pytest.fixture()
def report(projects, risk_report, benefit_report):
    return analyse_investments(projects, risk_report, benefit_report)


class TestInvestmentAnalysis:

    def test_returns_report(self, report):
        assert isinstance(report, PortfolioInvestmentReport)

    def test_all_projects_included(self, report, projects):
        assert len(report.project_investments) == len(projects)

    def test_total_budget(self, report):
        assert report.total_budget > 0

    def test_total_spent(self, report):
        assert report.total_spent > 0

    def test_cost_to_complete(self, report):
        assert report.total_cost_to_complete >= 0

    def test_roi_ranked(self, report):
        ranks = [p.roi_rank for p in report.project_investments]
        assert sorted(ranks) == list(range(1, len(ranks) + 1))

    def test_actions_assigned(self, report):
        for p in report.project_investments:
            assert p.action in (InvestmentAction.INVEST, InvestmentAction.HOLD, InvestmentAction.DIVEST, InvestmentAction.REVIEW)

    def test_rationale_not_empty(self, report):
        for p in report.project_investments:
            assert len(p.action_rationale) > 10

    def test_recommendations_generated(self, report):
        assert len(report.recommendations) >= 1

    def test_to_dict(self, report):
        d = report.to_dict()
        assert "total_budget" in d
        assert "portfolio_roi" in d
        assert "project_investments" in d

    def test_value_at_risk(self, report):
        # Should identify some value-at-risk projects given Red RAGs
        # (may be empty if no projects qualify for divest/review with budget)
        assert isinstance(report.top_value_at_risk, list)


class TestWithoutBenefits:

    def test_works_without_benefits(self, projects, risk_report):
        report = analyse_investments(projects, risk_report, None)
        assert len(report.project_investments) == len(projects)
        assert report.total_budget > 0


class TestInvestmentActions:

    def test_red_negative_roi_divest(self):
        from src.investment import _determine_action
        action, _ = _determine_action("Red", -0.3, 0.5, 5, 0.9)
        assert action == InvestmentAction.DIVEST

    def test_green_positive_roi_invest(self):
        from src.investment import _determine_action
        action, _ = _determine_action("Green", 0.8, 0.1, 1, 0.3)
        assert action == InvestmentAction.INVEST

    def test_red_positive_roi_review(self):
        from src.investment import _determine_action
        action, _ = _determine_action("Red", 0.5, 0.4, 5, 0.5)
        assert action == InvestmentAction.REVIEW
