"""
Executive action summary generator.

Produces a single high-impact paragraph summarising the 2-3 most
urgent things leadership needs to act on this cycle. This is the
paragraph a CXO reads on their phone at 7am.

Sprint 7 enhancement.
"""

from __future__ import annotations

from src.risk_engine.engine import PortfolioRiskReport, RiskCategory, RiskSeverity
from src.benefits.calculator import PortfolioBenefitReport
from src.investment import PortfolioInvestmentReport, InvestmentAction


def generate_executive_summary(
    risk_report: PortfolioRiskReport,
    benefit_report: PortfolioBenefitReport | None = None,
    investment_report: PortfolioInvestmentReport | None = None,
) -> str:
    """Generate a single punchy paragraph for the top of any exec briefing."""

    urgent_items: list[tuple[int, str]] = []  # (priority, text)

    total = len(risk_report.project_summaries)
    reds = [s for s in risk_report.project_summaries if s.rag_status == "Red"]
    ambers = [s for s in risk_report.project_summaries if s.rag_status == "Amber"]

    # 1. Budget-critical projects
    for s in risk_report.project_summaries:
        for r in s.risks:
            if r.category == RiskCategory.BURN_RATE and r.severity == RiskSeverity.CRITICAL:
                urgent_items.append((1, f"{s.project_name} will exhaust its budget before delivery completes — approve a top-up or cut scope"))
                break

    # 2. Compliance / regulatory deadlines
    for s in risk_report.project_summaries:
        name_lower = s.project_name.lower()
        if any(kw in name_lower for kw in ("compliance", "regulatory", "audit", "cyber", "security")):
            if s.rag_status in ("Red", "Amber"):
                critical_count = sum(1 for r in s.risks if r.severity == RiskSeverity.CRITICAL)
                if critical_count > 0:
                    urgent_items.append((2, f"{s.project_name} has {critical_count} critical issues and may miss its regulatory deadline"))

    # 3. Blocked cascades — projects blocking other projects
    blocked_projects = set()
    for s in risk_report.project_summaries:
        for r in s.risks:
            if r.category == RiskCategory.BLOCKED_WORK and r.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH):
                blocked_projects.add(s.project_name)
    for s in risk_report.project_summaries:
        for r in s.risks:
            if r.category == RiskCategory.DEPENDENCY:
                for bp in blocked_projects:
                    if bp.lower().split(" - ")[0] in r.explanation.lower():
                        urgent_items.append((3, f"blockers in {bp} are cascading into dependent projects"))
                        break

    # 4. Benefits drift
    if benefit_report and benefit_report.portfolio_drift_pct > 0.20:
        at_risk_value = benefit_report.total_at_risk_value
        urgent_items.append((4, f"benefits are drifting {benefit_report.portfolio_drift_pct:.0%} from plan — £{at_risk_value:,.0f} of portfolio value at risk"))

    # 5. Projects recommended for divestment
    if investment_report:
        divests = [p for p in investment_report.project_investments if p.action == InvestmentAction.DIVEST]
        if divests:
            freed = sum(p.cost_to_complete for p in divests)
            names = ", ".join(p.project_name for p in divests[:2])
            urgent_items.append((5, f"{names} showing negative ROI — recommend stopping discretionary spend, freeing £{freed:,.0f} for reallocation"))

    # 6. On-hold / stalled projects burning time
    on_hold = [s for s in risk_report.project_summaries if "hold" in s.project_status.lower() or "on hold" in s.project_status.lower()]
    if on_hold:
        names = ", ".join(s.project_name for s in on_hold[:2])
        urgent_items.append((6, f"{names} stalled — confirm go/no-go to release committed resources"))

    # Deduplicate by project name (keep highest priority)
    seen_projects: set[str] = set()
    deduped: list[tuple[int, str]] = []
    for priority, text in sorted(urgent_items, key=lambda x: x[0]):
        # Extract first project name mentioned
        key = text.split(" ")[0] if text else ""
        if key not in seen_projects or len(deduped) < 3:
            deduped.append((priority, text))
            seen_projects.add(key)

    # Build the paragraph
    if not deduped:
        return (
            f"The portfolio is tracking {total} active projects with "
            f"{len(reds)} at Red status and {len(ambers)} at Amber. "
            f"No critical escalation needed this cycle — continue standard monitoring."
        )

    top = deduped[:3]
    numbered = "; ".join(f"({i+1}) {text}" for i, (_, text) in enumerate(top))

    # Determine urgency level
    if any(p <= 2 for p, _ in top):
        urgency = "Recommended: schedule emergency portfolio review within 5 working days."
    elif any(p <= 4 for p, _ in top):
        urgency = "Recommended: address these items before the next steering cycle."
    else:
        urgency = "Recommended: review at next scheduled steering committee."

    return (
        f"Your portfolio has {len(top)} urgent issue{'s' if len(top) > 1 else ''} this cycle: "
        f"{numbered}. {urgency}"
    )
