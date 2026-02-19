"""
Burn rate alert detection.

Calculates budget consumption vs time elapsed.
Flags projects where actual spend >90% of budget with >10% time remaining.
Also detects overspend (actual > budget).

Sprint 1 — Week 3 deliverable.
"""

from __future__ import annotations

from datetime import date

from src.ingestion.parser import Project
from src.risk_engine.engine import Risk, RiskCategory, RiskSeverity

# Thresholds
SPEND_THRESHOLD = 0.90       # Flag if >90% budget spent
TIME_REMAINING_THRESHOLD = 0.10  # ...with >10% time remaining


def detect_burn_rate(project: Project, reference_date: date | None = None) -> list[Risk]:
    """Detect projects with dangerous burn rate patterns.

    Detection rules:
    1. **Overspend**: actual_spend > budget → Critical.
    2. **Burn rate alert**: spend >90% AND time remaining >10% → severity based on gap.
    3. Skipped if budget is 0 or dates are missing (insufficient data).

    Args:
        project: A parsed Project object.
        reference_date: Date to calculate against (defaults to today).

    Returns:
        List of Risk objects for burn rate alerts (0 or 1 per project).
    """
    if reference_date is None:
        reference_date = date.today()

    # Skip if no budget data
    if project.budget <= 0:
        return []

    # Calculate spend percentage
    spend_pct = project.actual_spend / project.budget

    # Check for overspend first (actual > budget)
    if spend_pct > 1.0:
        return [_build_overspend_risk(project, spend_pct)]

    # Need dates to calculate time remaining
    if project.start_date is None or project.end_date is None:
        # Can still flag if spend is very high even without dates
        if spend_pct >= SPEND_THRESHOLD:
            return [_build_high_spend_no_dates_risk(project, spend_pct)]
        return []

    # Calculate time elapsed and remaining
    total_duration = (project.end_date - project.start_date).days
    if total_duration <= 0:
        return []

    elapsed = (reference_date - project.start_date).days
    time_elapsed_pct = max(0.0, min(1.0, elapsed / total_duration))
    time_remaining_pct = 1.0 - time_elapsed_pct

    # Burn rate alert: high spend with significant time remaining
    if spend_pct >= SPEND_THRESHOLD and time_remaining_pct > TIME_REMAINING_THRESHOLD:
        return [_build_burn_rate_risk(project, spend_pct, time_elapsed_pct, time_remaining_pct)]

    return []


# ──────────────────────────────────────────────
# Risk builders
# ──────────────────────────────────────────────


def _build_overspend_risk(project: Project, spend_pct: float) -> Risk:
    """Build risk for project that has exceeded its budget."""
    overspend_amount = project.actual_spend - project.budget

    return Risk(
        project_name=project.name,
        category=RiskCategory.BURN_RATE,
        severity=RiskSeverity.CRITICAL,
        title=f"Project '{project.name}' has exceeded budget by {_fmt_currency(overspend_amount)}",
        explanation=(
            f"Project {project.name} has spent {_fmt_currency(project.actual_spend)} "
            f"against a budget of {_fmt_currency(project.budget)} "
            f"({_fmt_pct(spend_pct)} of budget consumed). "
            f"The project is over budget by {_fmt_currency(overspend_amount)}."
        ),
        suggested_mitigation=(
            f"Immediately review spending on {project.name}. "
            f"Consider requesting additional budget, reducing scope, "
            f"or pausing non-critical work streams to contain costs."
        ),
    )


def _build_burn_rate_risk(
    project: Project,
    spend_pct: float,
    time_elapsed_pct: float,
    time_remaining_pct: float,
) -> Risk:
    """Build risk for project burning budget faster than time elapsed."""
    severity = _burn_rate_severity(spend_pct, time_remaining_pct)

    return Risk(
        project_name=project.name,
        category=RiskCategory.BURN_RATE,
        severity=severity,
        title=(
            f"Project '{project.name}' has consumed {_fmt_pct(spend_pct)} of budget "
            f"with {_fmt_pct(time_remaining_pct)} of time remaining"
        ),
        explanation=(
            f"Project {project.name} has spent {_fmt_currency(project.actual_spend)} "
            f"of its {_fmt_currency(project.budget)} budget "
            f"({_fmt_pct(spend_pct)} consumed). "
            f"However, {_fmt_pct(time_remaining_pct)} of the project timeline remains "
            f"({project.end_date.isoformat() if project.end_date else 'unknown'} end date). "
            f"At the current burn rate, the project will exhaust its budget "
            f"before completion."
        ),
        suggested_mitigation=(
            f"Review spending trajectory on {project.name}. "
            f"Identify the largest cost drivers and assess whether "
            f"scope reduction, timeline extension, or additional funding is needed. "
            f"Flag to steering committee for decision."
        ),
    )


def _build_high_spend_no_dates_risk(project: Project, spend_pct: float) -> Risk:
    """Build risk for high spend without date information to calculate timeline."""
    return Risk(
        project_name=project.name,
        category=RiskCategory.BURN_RATE,
        severity=RiskSeverity.HIGH,
        title=f"Project '{project.name}' has consumed {_fmt_pct(spend_pct)} of budget",
        explanation=(
            f"Project {project.name} has spent {_fmt_currency(project.actual_spend)} "
            f"of its {_fmt_currency(project.budget)} budget "
            f"({_fmt_pct(spend_pct)} consumed). "
            f"Timeline data is unavailable, so remaining duration cannot be assessed. "
            f"The high spend level warrants review."
        ),
        suggested_mitigation=(
            f"Confirm project timeline for {project.name} and assess "
            f"whether remaining budget is sufficient for completion."
        ),
    )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _burn_rate_severity(spend_pct: float, time_remaining_pct: float) -> RiskSeverity:
    """Determine severity based on spend/time gap.

    The wider the gap between spend % and time elapsed %, the worse the risk.
    """
    if spend_pct >= 0.95:
        return RiskSeverity.CRITICAL
    elif spend_pct >= 0.90 and time_remaining_pct >= 0.20:
        return RiskSeverity.CRITICAL  # 90%+ spent with 20%+ time left
    elif spend_pct >= 0.90:
        return RiskSeverity.HIGH
    else:
        return RiskSeverity.MEDIUM


def _fmt_pct(value: float) -> str:
    """Format a float as a percentage string."""
    return f"{value:.0%}"


def _fmt_currency(value: float) -> str:
    """Format a float as a currency string (no symbol, with commas)."""
    return f"{value:,.0f}"
