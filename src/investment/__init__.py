"""
Portfolio investment & ROI analysis engine.

Calculates cost-to-complete, ROI per project, investment efficiency rankings,
and Invest/Hold/Divest recommendations.

Sprint 6 — Issue #32.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from enum import Enum

from src.ingestion.parser import Project
from src.risk_engine.engine import PortfolioRiskReport, RiskSeverity
from src.benefits.calculator import PortfolioBenefitReport


class InvestmentAction(Enum):
    INVEST = "Invest"
    HOLD = "Hold"
    DIVEST = "Divest"
    REVIEW = "Review"


@dataclass
class ProjectInvestment:
    """Investment analysis for a single project."""
    project_name: str
    budget: float
    actual_spend: float
    cost_to_complete: float
    pct_budget_consumed: float
    expected_benefit: float
    adjusted_benefit: float
    roi: float                    # (adjusted_benefit - budget) / budget
    roi_rank: int                 # 1 = best ROI
    rag_status: str
    risk_count: int
    drift_pct: float
    action: InvestmentAction
    action_rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "budget": self.budget,
            "actual_spend": self.actual_spend,
            "cost_to_complete": round(self.cost_to_complete),
            "pct_budget_consumed": round(self.pct_budget_consumed * 100, 1),
            "expected_benefit": self.expected_benefit,
            "adjusted_benefit": round(self.adjusted_benefit),
            "roi": round(self.roi * 100, 1),
            "roi_rank": self.roi_rank,
            "rag_status": self.rag_status,
            "action": self.action.value,
            "action_rationale": self.action_rationale,
        }


@dataclass
class PortfolioInvestmentReport:
    """Portfolio-level investment analysis."""
    total_budget: float
    total_spent: float
    total_cost_to_complete: float
    pct_budget_consumed: float
    total_expected_benefit: float
    total_adjusted_benefit: float
    portfolio_roi: float
    project_investments: list[ProjectInvestment]
    top_value_at_risk: list[ProjectInvestment]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_budget": self.total_budget,
            "total_spent": self.total_spent,
            "total_cost_to_complete": round(self.total_cost_to_complete),
            "pct_budget_consumed": round(self.pct_budget_consumed * 100, 1),
            "total_expected_benefit": self.total_expected_benefit,
            "total_adjusted_benefit": round(self.total_adjusted_benefit),
            "portfolio_roi": round(self.portfolio_roi * 100, 1),
            "project_investments": [p.to_dict() for p in self.project_investments],
            "recommendations": self.recommendations,
        }


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def analyse_investments(
    projects: list[Project],
    risk_report: PortfolioRiskReport,
    benefit_report: PortfolioBenefitReport | None = None,
) -> PortfolioInvestmentReport:
    """Run full portfolio investment analysis."""

    project_investments: list[ProjectInvestment] = []

    for project in projects:
        pi = _analyse_project_investment(project, risk_report, benefit_report)
        project_investments.append(pi)

    # Rank by ROI (highest first)
    sorted_by_roi = sorted(project_investments, key=lambda x: x.roi, reverse=True)
    for rank, pi in enumerate(sorted_by_roi, 1):
        pi.roi_rank = rank

    # Sort output by rank
    project_investments = sorted_by_roi

    # Portfolio totals
    total_budget = sum(p.budget for p in project_investments)
    total_spent = sum(p.actual_spend for p in project_investments)
    total_ctc = sum(p.cost_to_complete for p in project_investments)
    pct_consumed = total_spent / total_budget if total_budget > 0 else 0.0
    total_expected = sum(p.expected_benefit for p in project_investments)
    total_adjusted = sum(p.adjusted_benefit for p in project_investments)
    portfolio_roi = (total_adjusted - total_budget) / total_budget if total_budget > 0 else 0.0

    # Top value at risk (projects where we're spending but benefit is eroding)
    value_at_risk = [
        p for p in project_investments
        if p.action in (InvestmentAction.DIVEST, InvestmentAction.REVIEW) and p.budget > 0
    ]
    value_at_risk.sort(key=lambda x: x.budget, reverse=True)

    recommendations = _generate_investment_recommendations(
        project_investments, total_budget, total_adjusted, portfolio_roi
    )

    return PortfolioInvestmentReport(
        total_budget=total_budget,
        total_spent=total_spent,
        total_cost_to_complete=total_ctc,
        pct_budget_consumed=pct_consumed,
        total_expected_benefit=total_expected,
        total_adjusted_benefit=total_adjusted,
        portfolio_roi=portfolio_roi,
        project_investments=project_investments,
        top_value_at_risk=value_at_risk[:3],
        recommendations=recommendations,
    )


# ──────────────────────────────────────────────
# Per-project analysis
# ──────────────────────────────────────────────

def _analyse_project_investment(
    project: Project,
    risk_report: PortfolioRiskReport,
    benefit_report: PortfolioBenefitReport | None,
) -> ProjectInvestment:
    budget = project.budget or 0.0
    actual = project.actual_spend or 0.0
    ctc = max(0, budget - actual)
    pct_consumed = actual / budget if budget > 0 else 0.0

    # Get RAG and risk count from risk report
    rag = "Green"
    risk_count = 0
    for s in risk_report.project_summaries:
        if s.project_name.lower() == project.name.lower():
            rag = s.rag_status
            risk_count = s.risk_count
            break

    # Get benefit data
    expected_benefit = 0.0
    adjusted_benefit = 0.0
    drift_pct = 0.0
    if benefit_report:
        for bs in benefit_report.project_summaries:
            if bs.project_name.lower() == project.name.lower():
                expected_benefit = bs.total_expected
                adjusted_benefit = bs.adjusted_expected
                drift_pct = bs.drift_pct
                break
    else:
        # No benefit report — use budget as proxy (conservative)
        expected_benefit = budget
        adjusted_benefit = budget * {"Red": 0.5, "Amber": 0.7, "Green": 0.9}.get(rag, 0.7)

    # ROI calculation
    roi = (adjusted_benefit - budget) / budget if budget > 0 else 0.0

    # Invest/Hold/Divest decision
    action, rationale = _determine_action(rag, roi, drift_pct, risk_count, pct_consumed)

    return ProjectInvestment(
        project_name=project.name,
        budget=budget,
        actual_spend=actual,
        cost_to_complete=ctc,
        pct_budget_consumed=pct_consumed,
        expected_benefit=expected_benefit,
        adjusted_benefit=adjusted_benefit,
        roi=roi,
        roi_rank=0,  # Set after sorting
        rag_status=rag,
        risk_count=risk_count,
        drift_pct=drift_pct,
        action=action,
        action_rationale=rationale,
    )


def _determine_action(
    rag: str, roi: float, drift_pct: float, risk_count: int, pct_consumed: float,
) -> tuple[InvestmentAction, str]:
    """Determine Invest/Hold/Divest with rationale."""

    # Strong positive ROI + Green/Amber = Invest
    if roi > 0.5 and rag in ("Green", "Amber") and drift_pct < 0.3:
        return InvestmentAction.INVEST, (
            f"Strong ROI ({roi:.0%}) with manageable risk. "
            f"Consider accelerating delivery to realise benefits sooner."
        )

    # Positive ROI but Red / high drift = Review
    if roi > 0 and (rag == "Red" or drift_pct > 0.3):
        return InvestmentAction.REVIEW, (
            f"Positive ROI ({roi:.0%}) but delivery at risk (RAG: {rag}, drift: {drift_pct:.0%}). "
            f"Protect the benefit case — resolve blockers or adjust scope to lock in remaining value."
        )

    # Negative ROI + Red = Divest
    if roi < 0 and rag == "Red":
        return InvestmentAction.DIVEST, (
            f"Negative ROI ({roi:.0%}) and Red delivery status. "
            f"Recommend stopping discretionary spend and redirecting budget to higher-value projects."
        )

    # Negative ROI but Green = Review (might be early stage)
    if roi < 0 and rag == "Green":
        return InvestmentAction.REVIEW, (
            f"ROI currently negative ({roi:.0%}) but delivery is on track. "
            f"May be early-stage investment — confirm benefit timeline and reassess at next cycle."
        )

    # High budget consumed + low ROI = Divest
    if pct_consumed > 0.8 and roi < 0.1:
        return InvestmentAction.DIVEST, (
            f"Budget {pct_consumed:.0%} consumed with minimal return ({roi:.0%} ROI). "
            f"Consider controlled wind-down or scope reduction."
        )

    # Default = Hold
    return InvestmentAction.HOLD, (
        f"Moderate position (ROI: {roi:.0%}, RAG: {rag}). "
        f"Continue current trajectory with standard risk monitoring."
    )


# ──────────────────────────────────────────────
# Recommendations
# ──────────────────────────────────────────────

def _generate_investment_recommendations(
    investments: list[ProjectInvestment],
    total_budget: float, total_adjusted: float, portfolio_roi: float,
) -> list[str]:
    recs: list[str] = []

    divests = [p for p in investments if p.action == InvestmentAction.DIVEST]
    invests = [p for p in investments if p.action == InvestmentAction.INVEST]
    reviews = [p for p in investments if p.action == InvestmentAction.REVIEW]

    if divests:
        names = ", ".join(p.project_name for p in divests[:3])
        freed = sum(p.cost_to_complete for p in divests)
        recs.append(
            f"Divest: {names} — stop or reduce discretionary spend. "
            f"Potential £{freed:,.0f} reallocation to higher-value projects."
        )

    if invests:
        names = ", ".join(p.project_name for p in invests[:3])
        recs.append(
            f"Accelerate: {names} — strong ROI and manageable risk. "
            f"Consider additional resource to pull delivery forward."
        )

    if reviews:
        names = ", ".join(p.project_name for p in reviews[:3])
        recs.append(
            f"Review: {names} — positive potential but delivery risk is eroding the benefit case. "
            f"Schedule deep-dive review within 2 weeks."
        )

    if portfolio_roi < 0:
        recs.append(
            f"Portfolio ROI is negative ({portfolio_roi:.0%}). "
            f"The current investment mix is not generating adequate return. "
            f"Recommend portfolio rebalancing — shift budget from low-ROI to high-ROI projects."
        )

    if not recs:
        recs.append(
            "Portfolio investment is broadly healthy. Continue standard monitoring "
            "and reassess allocation at next quarterly review."
        )

    return recs
