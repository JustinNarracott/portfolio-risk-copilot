"""
Risk aggregation and ranking engine.

Combines all risk detectors (blocked, carry-over, burn rate, dependencies)
and produces a ranked list of top N risks per project.

Sprint 1 — Week 3 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from src.ingestion.parser import Project


class RiskSeverity(Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RiskCategory(Enum):
    BLOCKED_WORK = "Blocked Work"
    CHRONIC_CARRYOVER = "Chronic Carry-Over"
    BURN_RATE = "Burn Rate"
    DEPENDENCY = "Dependency"


# Severity sort order (lower = worse)
SEVERITY_ORDER = {
    RiskSeverity.CRITICAL: 0,
    RiskSeverity.HIGH: 1,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.LOW: 3,
}


@dataclass
class Risk:
    """A single identified risk."""

    project_name: str
    category: RiskCategory
    severity: RiskSeverity
    title: str
    explanation: str
    suggested_mitigation: str = ""

    def to_dict(self) -> dict:
        """Serialise to plain dict (for JSON output)."""
        return {
            "project_name": self.project_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "explanation": self.explanation,
            "suggested_mitigation": self.suggested_mitigation,
        }


@dataclass
class ProjectRiskSummary:
    """Aggregated risk summary for a single project."""

    project_name: str
    project_status: str
    risk_count: int
    top_severity: RiskSeverity
    risks: list[Risk] = field(default_factory=list)

    @property
    def rag_status(self) -> str:
        """Derive RAG (Red/Amber/Green) from top severity.

        Critical → Red, High → Red, Medium → Amber, Low → Green.
        No risks → Green.
        """
        if self.risk_count == 0:
            return "Green"
        mapping = {
            RiskSeverity.CRITICAL: "Red",
            RiskSeverity.HIGH: "Red",
            RiskSeverity.MEDIUM: "Amber",
            RiskSeverity.LOW: "Green",
        }
        return mapping.get(self.top_severity, "Green")

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_status": self.project_status,
            "risk_count": self.risk_count,
            "top_severity": self.top_severity.value,
            "rag_status": self.rag_status,
            "risks": [r.to_dict() for r in self.risks],
        }


@dataclass
class PortfolioRiskReport:
    """Full portfolio risk analysis output."""

    project_summaries: list[ProjectRiskSummary] = field(default_factory=list)
    total_risks: int = 0
    projects_at_risk: int = 0
    portfolio_rag: str = "Green"

    def to_dict(self) -> dict:
        return {
            "total_risks": self.total_risks,
            "projects_at_risk": self.projects_at_risk,
            "portfolio_rag": self.portfolio_rag,
            "project_summaries": [s.to_dict() for s in self.project_summaries],
        }


def analyse_portfolio(
    projects: list[Project],
    top_n: int = 5,
    reference_date: date | None = None,
) -> PortfolioRiskReport:
    """Run all risk detectors and return top N risks per project.

    Args:
        projects: List of parsed Project objects.
        top_n: Number of top risks to return per project.
        reference_date: Date for burn rate calculation (defaults to today).

    Returns:
        PortfolioRiskReport with per-project summaries and portfolio-level metrics.
    """
    # Import detectors here to avoid circular imports
    from src.risk_engine.blocked import detect_blocked_work
    from src.risk_engine.burnrate import detect_burn_rate
    from src.risk_engine.carryover import detect_carryover
    from src.risk_engine.dependencies import detect_dependencies

    summaries: list[ProjectRiskSummary] = []
    total_risks = 0
    projects_at_risk = 0
    worst_severity = RiskSeverity.LOW

    for project in projects:
        # Run all detectors
        all_risks: list[Risk] = []
        all_risks.extend(detect_blocked_work(project))
        all_risks.extend(detect_carryover(project))
        all_risks.extend(detect_burn_rate(project, reference_date=reference_date))
        all_risks.extend(detect_dependencies(project))

        # Sort by severity and take top N
        all_risks.sort(key=lambda r: SEVERITY_ORDER.get(r.severity, 99))
        top_risks = all_risks[:top_n]

        # Determine top severity for this project
        if top_risks:
            top_severity = top_risks[0].severity
        else:
            top_severity = RiskSeverity.LOW

        summary = ProjectRiskSummary(
            project_name=project.name,
            project_status=project.status,
            risk_count=len(top_risks),
            top_severity=top_severity,
            risks=top_risks,
        )
        summaries.append(summary)

        total_risks += len(top_risks)
        if top_risks:
            projects_at_risk += 1
            if SEVERITY_ORDER[top_severity] < SEVERITY_ORDER[worst_severity]:
                worst_severity = top_severity

    # Portfolio-level RAG
    if projects_at_risk == 0:
        portfolio_rag = "Green"
    else:
        rag_map = {
            RiskSeverity.CRITICAL: "Red",
            RiskSeverity.HIGH: "Red",
            RiskSeverity.MEDIUM: "Amber",
            RiskSeverity.LOW: "Green",
        }
        portfolio_rag = rag_map.get(worst_severity, "Green")

    # Sort summaries: worst first
    summaries.sort(key=lambda s: SEVERITY_ORDER.get(s.top_severity, 99))

    return PortfolioRiskReport(
        project_summaries=summaries,
        total_risks=total_risks,
        projects_at_risk=projects_at_risk,
        portfolio_rag=portfolio_rag,
    )
