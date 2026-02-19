"""
Benefits realisation calculator & drift detection.

Calculates realisation rates, detects benefits drift, and generates
CXO-readable explanations of value at risk.

Sprint 5 — Issue #30.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from src.benefits.parser import (
    Benefit, BenefitCategory, BenefitConfidence, BenefitStatus,
)
from src.risk_engine.engine import PortfolioRiskReport, RiskSeverity


class DriftRAG:
    RED = "Red"
    AMBER = "Amber"
    GREEN = "Green"


@dataclass
class ProjectBenefitSummary:
    """Benefits summary for a single project."""
    project_name: str
    benefits: list[Benefit]
    total_expected: float
    total_realised: float
    realisation_pct: float
    adjusted_expected: float  # Expected value adjusted for delivery confidence
    drift_pct: float          # % drift from original expected
    drift_rag: str            # Red (>30%), Amber (>15%), Green
    benefits_at_risk_value: float
    benefits_at_risk: list[Benefit]
    drift_explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "total_expected": self.total_expected,
            "total_realised": self.total_realised,
            "realisation_pct": round(self.realisation_pct * 100, 1),
            "adjusted_expected": round(self.adjusted_expected),
            "drift_pct": round(self.drift_pct * 100, 1),
            "drift_rag": self.drift_rag,
            "benefits_at_risk_value": round(self.benefits_at_risk_value),
            "drift_explanation": self.drift_explanation,
        }


@dataclass
class PortfolioBenefitReport:
    """Portfolio-level benefits analysis."""
    total_expected: float
    total_realised: float
    total_adjusted: float
    realisation_pct: float
    portfolio_drift_pct: float
    portfolio_drift_rag: str
    total_at_risk_value: float
    project_summaries: list[ProjectBenefitSummary]
    top_benefits_at_risk: list[Benefit]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_expected": self.total_expected,
            "total_realised": self.total_realised,
            "total_adjusted": round(self.total_adjusted),
            "realisation_pct": round(self.realisation_pct * 100, 1),
            "portfolio_drift_pct": round(self.portfolio_drift_pct * 100, 1),
            "portfolio_drift_rag": self.portfolio_drift_rag,
            "total_at_risk_value": round(self.total_at_risk_value),
            "project_summaries": [s.to_dict() for s in self.project_summaries],
            "recommendations": self.recommendations,
        }


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def analyse_benefits(
    benefits: list[Benefit],
    risk_report: PortfolioRiskReport | None = None,
    reference_date: date | None = None,
) -> PortfolioBenefitReport:
    """Run full benefits analysis: realisation, drift, recommendations."""
    ref = reference_date or date.today()

    # Group by project
    by_project: dict[str, list[Benefit]] = {}
    for b in benefits:
        by_project.setdefault(b.project_name, []).append(b)

    # Build per-project summaries
    project_summaries: list[ProjectBenefitSummary] = []
    for proj_name, proj_benefits in sorted(by_project.items()):
        summary = _analyse_project_benefits(proj_name, proj_benefits, risk_report, ref)
        project_summaries.append(summary)

    # Portfolio totals
    total_expected = sum(s.total_expected for s in project_summaries)
    total_realised = sum(s.total_realised for s in project_summaries)
    total_adjusted = sum(s.adjusted_expected for s in project_summaries)
    realisation_pct = total_realised / total_expected if total_expected > 0 else 0.0
    drift_pct = (total_expected - total_adjusted) / total_expected if total_expected > 0 else 0.0
    drift_rag = _drift_rag(drift_pct)
    total_at_risk = sum(s.benefits_at_risk_value for s in project_summaries)

    # Top benefits at risk (across all projects)
    all_at_risk: list[Benefit] = []
    for s in project_summaries:
        all_at_risk.extend(s.benefits_at_risk)
    all_at_risk.sort(key=lambda b: b.unrealised_value, reverse=True)
    top_at_risk = all_at_risk[:5]

    # Generate recommendations
    recommendations = _generate_recommendations(
        project_summaries, total_expected, total_at_risk, drift_pct
    )

    return PortfolioBenefitReport(
        total_expected=total_expected,
        total_realised=total_realised,
        total_adjusted=total_adjusted,
        realisation_pct=realisation_pct,
        portfolio_drift_pct=drift_pct,
        portfolio_drift_rag=drift_rag,
        total_at_risk_value=total_at_risk,
        project_summaries=project_summaries,
        top_benefits_at_risk=top_at_risk,
        recommendations=recommendations,
    )


# ──────────────────────────────────────────────
# Per-project analysis
# ──────────────────────────────────────────────

def _analyse_project_benefits(
    project_name: str,
    benefits: list[Benefit],
    risk_report: PortfolioRiskReport | None,
    ref: date,
) -> ProjectBenefitSummary:
    """Analyse benefits for a single project."""
    total_expected = sum(b.expected_value for b in benefits)
    total_realised = sum(b.realised_value for b in benefits)
    realisation_pct = total_realised / total_expected if total_expected > 0 else 0.0

    # Get delivery confidence from risk report
    confidence_factor = _get_confidence_factor(project_name, risk_report)

    # Adjusted expected = expected × confidence factor (for unrealised portion)
    adjusted = 0.0
    for b in benefits:
        if b.status == BenefitStatus.REALISED:
            adjusted += b.expected_value  # Already realised — no adjustment
        elif b.status == BenefitStatus.CANCELLED:
            adjusted += 0.0  # Written off
        else:
            bf = _benefit_confidence_multiplier(b, confidence_factor, ref)
            adjusted += b.expected_value * bf

    drift_pct = (total_expected - adjusted) / total_expected if total_expected > 0 else 0.0
    drift_rag = _drift_rag(drift_pct)

    # Benefits at risk — include at-risk status, low confidence, OR project has significant drift
    at_risk = [
        b for b in benefits
        if b.is_at_risk
        or b.confidence == BenefitConfidence.LOW
        or (drift_pct > 0.30 and b.status != BenefitStatus.REALISED and b.unrealised_value > 0)
    ]
    # Deduplicate
    seen = set()
    unique_at_risk = []
    for b in at_risk:
        if b.benefit_id not in seen:
            seen.add(b.benefit_id)
            unique_at_risk.append(b)
    at_risk = unique_at_risk
    at_risk_value = sum(b.unrealised_value for b in at_risk)

    # Drift explanation
    explanation = _build_drift_explanation(project_name, benefits, total_expected, adjusted, drift_pct, ref)

    return ProjectBenefitSummary(
        project_name=project_name,
        benefits=benefits,
        total_expected=total_expected,
        total_realised=total_realised,
        realisation_pct=realisation_pct,
        adjusted_expected=adjusted,
        drift_pct=drift_pct,
        drift_rag=drift_rag,
        benefits_at_risk_value=at_risk_value,
        benefits_at_risk=at_risk,
        drift_explanation=explanation,
    )


def _get_confidence_factor(project_name: str, risk_report: PortfolioRiskReport | None) -> float:
    """Derive delivery confidence from risk report. 1.0 = fully confident, 0.0 = zero confidence."""
    if risk_report is None:
        return 0.8  # Conservative default

    for s in risk_report.project_summaries:
        if s.project_name.lower() == project_name.lower():
            # Base from RAG
            rag_base = {"Red": 0.5, "Amber": 0.7, "Green": 0.9}.get(s.rag_status, 0.8)

            # Adjust for risk count
            risk_penalty = min(s.risk_count * 0.03, 0.2)

            # Adjust for critical risks
            critical_count = sum(1 for r in s.risks if r.severity == RiskSeverity.CRITICAL)
            critical_penalty = critical_count * 0.05

            return max(0.2, rag_base - risk_penalty - critical_penalty)

    return 0.8


def _benefit_confidence_multiplier(b: Benefit, project_confidence: float, ref: date) -> float:
    """Per-benefit confidence multiplier."""
    base = project_confidence

    # Status adjustments
    status_multiplier = {
        BenefitStatus.ON_TRACK: 1.0,
        BenefitStatus.PARTIAL: 0.85,
        BenefitStatus.NOT_STARTED: 0.7,
        BenefitStatus.AT_RISK: 0.5,
        BenefitStatus.DELAYED: 0.4,
        BenefitStatus.CANCELLED: 0.0,
        BenefitStatus.REALISED: 1.0,
    }.get(b.status, 0.7)

    # Overdue adjustment
    overdue_penalty = 0.0
    if b.target_date and b.target_date < ref and b.status != BenefitStatus.REALISED:
        days_overdue = (ref - b.target_date).days
        overdue_penalty = min(days_overdue / 180, 0.3)  # Max 30% penalty for 6+ months overdue

    # Confidence level
    conf_mult = {BenefitConfidence.HIGH: 1.0, BenefitConfidence.MEDIUM: 0.85, BenefitConfidence.LOW: 0.6}
    conf_factor = conf_mult.get(b.confidence, 0.85)

    return max(0.0, base * status_multiplier * conf_factor - overdue_penalty)


def _drift_rag(drift_pct: float) -> str:
    if drift_pct > 0.30:
        return DriftRAG.RED
    elif drift_pct > 0.15:
        return DriftRAG.AMBER
    return DriftRAG.GREEN


def _build_drift_explanation(
    project_name: str, benefits: list[Benefit],
    total_expected: float, adjusted: float, drift_pct: float, ref: date,
) -> str:
    """CXO-readable drift explanation."""
    if total_expected == 0:
        return f"{project_name} has no quantified financial benefits."

    if drift_pct <= 0.05:
        return (
            f"{project_name} benefits are on track — "
            f"£{adjusted:,.0f} of £{total_expected:,.0f} expected to realise."
        )

    # Find the biggest contributors to drift
    drift_causes: list[str] = []
    at_risk = [b for b in benefits if b.is_at_risk]
    cancelled = [b for b in benefits if b.status == BenefitStatus.CANCELLED]
    overdue = [b for b in benefits if b.target_date and b.target_date < ref and b.status != BenefitStatus.REALISED]

    if cancelled:
        val = sum(b.expected_value for b in cancelled)
        drift_causes.append(f"£{val:,.0f} written off (cancelled)")
    if at_risk:
        val = sum(b.unrealised_value for b in at_risk)
        drift_causes.append(f"£{val:,.0f} at risk due to delivery issues")
    if overdue:
        drift_causes.append(f"{len(overdue)} benefit{'s' if len(overdue) > 1 else ''} overdue")

    causes_text = "; ".join(drift_causes) if drift_causes else "reduced delivery confidence"

    return (
        f"{project_name} was forecast to deliver £{total_expected:,.0f}. "
        f"Adjusted estimate is £{adjusted:,.0f} — "
        f"a {drift_pct:.0%} drift. "
        f"Drivers: {causes_text}."
    )


# ──────────────────────────────────────────────
# Recommendations
# ──────────────────────────────────────────────

def _generate_recommendations(
    summaries: list[ProjectBenefitSummary],
    total_expected: float, total_at_risk: float, drift_pct: float,
) -> list[str]:
    recs: list[str] = []

    # Red drift projects
    red_drift = [s for s in summaries if s.drift_rag == DriftRAG.RED]
    if red_drift:
        names = ", ".join(s.project_name for s in red_drift[:3])
        recs.append(
            f"Escalate benefits review for {names} — drift exceeds 30%. "
            f"Decide whether to protect the benefit case (inject resource/budget) "
            f"or formally write down expected value."
        )

    # High at-risk value
    if total_at_risk > 0 and total_expected > 0:
        pct = total_at_risk / total_expected
        if pct > 0.2:
            recs.append(
                f"£{total_at_risk:,.0f} of portfolio benefits are at risk "
                f"({pct:.0%} of total expected value). "
                f"Conduct a benefits protection review — identify which benefits "
                f"can be recovered and which should be written down."
            )

    # Projects with no realisation yet
    zero_realisation = [s for s in summaries if s.total_realised == 0 and s.total_expected > 0]
    if zero_realisation:
        names = ", ".join(s.project_name for s in zero_realisation[:3])
        recs.append(
            f"No benefits have been realised yet for {names}. "
            f"Confirm benefit tracking is in place and validate "
            f"that delivery milestones still support the benefit case."
        )

    if not recs:
        recs.append(
            "Benefits realisation is broadly on track. "
            "Continue regular tracking and flag any emerging drift early."
        )

    return recs
