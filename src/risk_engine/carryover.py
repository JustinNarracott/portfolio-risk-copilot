"""
Chronic carry-over detection.

Identifies tasks moved between 3+ sprints/iterations, indicating
repeated delivery failure. Higher severity for critical/high priority
tasks that keep slipping.

Sprint 1 — Week 2 deliverable.
"""

from __future__ import annotations

from src.ingestion.parser import Project, Task
from src.risk_engine.engine import Risk, RiskCategory, RiskSeverity

# Default: flag tasks carried over across 3+ sprints
CARRYOVER_THRESHOLD = 3

# Priority mapping for severity calculation
PRIORITY_SEVERITY: dict[str, RiskSeverity] = {
    "critical": RiskSeverity.CRITICAL,
    "high": RiskSeverity.HIGH,
    "medium": RiskSeverity.MEDIUM,
    "low": RiskSeverity.LOW,
}


def detect_carryover(project: Project, threshold: int = CARRYOVER_THRESHOLD) -> list[Risk]:
    """Detect tasks carried over across multiple sprints.

    A task is considered carried over if it has appeared in `threshold` or more
    previous sprints (from the `previous_sprints` field) and is NOT yet complete.

    Severity is derived from:
    - Task priority (Critical/High → higher severity).
    - Number of carry-overs (more sprints → elevated severity).

    Args:
        project: A parsed Project object.
        threshold: Minimum number of previous sprints to flag (default: 3).

    Returns:
        List of Risk objects for chronic carry-over, sorted by severity.
    """
    risks: list[Risk] = []

    for task in project.tasks:
        # Skip completed tasks — carry-over is only relevant for active/pending work
        if _is_complete(task):
            continue

        sprint_count = len(task.previous_sprints)

        if sprint_count < threshold:
            continue

        # Determine severity
        severity = _calculate_severity(task, sprint_count)

        # Build sprint history string for explanation
        all_sprints = task.previous_sprints + ([task.sprint] if task.sprint else [])
        sprint_history = " → ".join(all_sprints)

        explanation = (
            f"'{task.name}' has bounced across {sprint_count} sprints "
            f"({sprint_history}) without getting done. "
            f"Assigned to {task.assignee or 'nobody'} at {task.priority.lower()} priority. "
            f"This is a delivery smell — either the task is too large, "
            f"blocked on something unstated, or consistently deprioritised."
        )

        mitigation = _build_mitigation(task, sprint_count)

        risks.append(Risk(
            project_name=project.name,
            category=RiskCategory.CHRONIC_CARRYOVER,
            severity=severity,
            title=f"'{task.name}' stuck — carried over {sprint_count} sprints",
            explanation=explanation,
            suggested_mitigation=mitigation,
        ))

    # Sort by severity (Critical first)
    severity_order = {
        RiskSeverity.CRITICAL: 0,
        RiskSeverity.HIGH: 1,
        RiskSeverity.MEDIUM: 2,
        RiskSeverity.LOW: 3,
    }
    risks.sort(key=lambda r: severity_order.get(r.severity, 99))

    return risks


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _is_complete(task: Task) -> bool:
    """Check if a task is in a completed state."""
    return task.status.strip().lower() in {"done", "complete", "completed", "closed", "resolved"}


def _calculate_severity(task: Task, sprint_count: int) -> RiskSeverity:
    """Calculate risk severity from priority and carry-over count.

    Base severity comes from task priority. Elevated if carried over 5+ sprints.
    """
    base = PRIORITY_SEVERITY.get(task.priority.strip().lower(), RiskSeverity.MEDIUM)

    # Elevate if carried over many sprints (5+)
    if sprint_count >= 5:
        elevation = {
            RiskSeverity.LOW: RiskSeverity.MEDIUM,
            RiskSeverity.MEDIUM: RiskSeverity.HIGH,
            RiskSeverity.HIGH: RiskSeverity.CRITICAL,
            RiskSeverity.CRITICAL: RiskSeverity.CRITICAL,
        }
        return elevation[base]

    return base


def _build_mitigation(task: Task, sprint_count: int) -> str:
    """Build suggested mitigation for carry-over risk."""
    parts: list[str] = []

    parts.append(
        f"Review why '{task.name}' has not been completed after {sprint_count} sprints. "
        f"Consider whether it needs to be re-scoped, broken into smaller tasks, "
        f"or escalated."
    )

    if sprint_count >= 5:
        parts.append(
            "This task has been carried over excessively — consider a dedicated "
            "spike or assigning additional resource to unblock it."
        )

    if task.priority.lower() in ("critical", "high"):
        parts.append(
            f"As a {task.priority.lower()}-priority item, continued delay "
            f"may impact project milestones."
        )

    return " ".join(parts)
