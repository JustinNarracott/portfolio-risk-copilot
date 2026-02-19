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
        title=f"{project.name} is over budget by {_fmt_currency(overspend_amount)}",
        explanation=(
            f"{project.name} has spent {_fmt_currency(project.actual_spend)} "
            f"against a {_fmt_currency(project.budget)} budget — "
            f"{_fmt_pct(spend_pct)} consumed. "
            f"The project is {_fmt_currency(overspend_amount)} over budget "
            f"with no additional funding approved. "
            f"Every week of continued spend deepens the overrun."
        ),
        suggested_mitigation=(
            f"Halt non-critical spend on {project.name} immediately. "
            f"Present options to the sponsor: approve a {_fmt_currency(overspend_amount)}+ "
            f"budget top-up, or cut remaining scope to close within current allocation."
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
    remaining_budget = project.budget - project.actual_spend

    return Risk(
        project_name=project.name,
        category=RiskCategory.BURN_RATE,
        severity=severity,
        title=(
            f"{project.name}: {_fmt_pct(spend_pct)} of budget gone, "
            f"{_fmt_pct(time_remaining_pct)} of timeline left"
        ),
        explanation=(
            f"{project.name} is burning cash faster than the clock. "
            f"{_fmt_currency(project.actual_spend)} spent of {_fmt_currency(project.budget)} "
            f"({_fmt_pct(spend_pct)}), but {_fmt_pct(time_remaining_pct)} of the delivery "
            f"window remains. Only {_fmt_currency(remaining_budget)} left to cover "
            f"the remaining work. At current velocity, the budget will run out "
            f"before delivery completes."
        ),
        suggested_mitigation=(
            f"Three options for leadership: (1) Approve a budget top-up of "
            f"~{_fmt_currency(remaining_budget * 0.5)} to provide runway, "
            f"(2) Cut scope to fit remaining {_fmt_currency(remaining_budget)}, or "
            f"(3) Accelerate the timeline to reduce fixed costs. "
            f"Decision needed within 2 weeks."
        ),
    )


def _build_high_spend_no_dates_risk(project: Project, spend_pct: float) -> Risk:
    """Build risk for high spend without date information."""
    return Risk(
        project_name=project.name,
        category=RiskCategory.BURN_RATE,
        severity=RiskSeverity.HIGH,
        title=f"{project.name}: {_fmt_pct(spend_pct)} of budget consumed — no timeline data",
        explanation=(
            f"{project.name} has burned through {_fmt_pct(spend_pct)} of its "
            f"{_fmt_currency(project.budget)} budget "
            f"({_fmt_currency(project.actual_spend)} spent). "
            f"No timeline data is available, so it's unclear whether this "
            f"spend rate is on track. This is a blind spot."
        ),
        suggested_mitigation=(
            f"Urgently confirm the delivery timeline for {project.name}. "
            f"Without dates, it's impossible to assess whether the remaining "
            f"{_fmt_currency(project.budget - project.actual_spend)} is sufficient."
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
