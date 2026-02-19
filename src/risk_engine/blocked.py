"""
Blocked work detection.

Scans task statuses and comments for blocked/waiting indicators.
Severity is determined by task priority and whether a blocker keyword
is present in comments (indicating an external dependency).

Sprint 1 — Week 2 deliverable.
"""

from __future__ import annotations

from src.ingestion.parser import Project, Task
from src.risk_engine.engine import Risk, RiskCategory, RiskSeverity

# Statuses that indicate a task is blocked (normalised to lowercase)
BLOCKED_STATUSES = {"blocked", "waiting", "on hold", "on_hold", "on-hold", "suspended"}

# Keywords in comments that indicate an external blocker
BLOCKER_KEYWORDS = [
    "blocked by",
    "waiting for",
    "waiting on",
    "on hold pending",
    "on hold until",
    "held up by",
    "stalled",
]

# Priority mapping for severity calculation
PRIORITY_SEVERITY: dict[str, RiskSeverity] = {
    "critical": RiskSeverity.CRITICAL,
    "high": RiskSeverity.HIGH,
    "medium": RiskSeverity.MEDIUM,
    "low": RiskSeverity.LOW,
}


def detect_blocked_work(project: Project) -> list[Risk]:
    """Detect tasks with blocked status or blocker keywords in comments.

    Detection logic:
    1. Task status matches a blocked status (e.g., "Blocked", "On Hold").
    2. Task comments contain a blocker keyword (e.g., "blocked by", "waiting for").

    Severity is derived from task priority:
    - Critical/High priority blocked task → Critical/High severity risk.
    - Medium/Low priority → Medium/Low severity.
    - If both status AND comment indicate blocking, severity is elevated by one level.

    Args:
        project: A parsed Project object.

    Returns:
        List of Risk objects for blocked work found, sorted by severity (worst first).
    """
    risks: list[Risk] = []

    for task in project.tasks:
        status_blocked = _is_status_blocked(task)
        comment_blocked, blocker_detail = _has_blocker_keyword(task)

        if not status_blocked and not comment_blocked:
            continue

        # Determine base severity from task priority
        base_severity = _severity_from_priority(task.priority)

        # Elevate severity if both status AND comment indicate blocking
        if status_blocked and comment_blocked:
            severity = _elevate_severity(base_severity)
        else:
            severity = base_severity

        # Build explanation
        explanation = _build_explanation(project.name, task, status_blocked, comment_blocked, blocker_detail)

        # Build mitigation suggestion
        mitigation = _build_mitigation(task, status_blocked, comment_blocked, blocker_detail)

        # Build title
        if status_blocked:
            title = f"Task '{task.name}' is {task.status.lower()}"
        else:
            title = f"Task '{task.name}' has blocker in comments"

        risks.append(Risk(
            project_name=project.name,
            category=RiskCategory.BLOCKED_WORK,
            severity=severity,
            title=title,
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
# Detection helpers
# ──────────────────────────────────────────────


def _is_status_blocked(task: Task) -> bool:
    """Check if task status indicates it's blocked."""
    return task.status.strip().lower() in BLOCKED_STATUSES


def _has_blocker_keyword(task: Task) -> tuple[bool, str]:
    """Check if task comments contain a blocker keyword.

    Returns:
        Tuple of (is_blocked, matched_keyword_context).
        The context is the surrounding text of the first match for use in explanations.
    """
    if not task.comments:
        return False, ""

    comments_lower = task.comments.lower()
    for keyword in BLOCKER_KEYWORDS:
        pos = comments_lower.find(keyword)
        if pos != -1:
            # Extract context: up to 80 chars around the keyword
            start = max(0, pos - 20)
            end = min(len(task.comments), pos + len(keyword) + 60)
            context = task.comments[start:end].strip()
            if start > 0:
                context = "..." + context
            if end < len(task.comments):
                context = context + "..."
            return True, context

    return False, ""


# ──────────────────────────────────────────────
# Severity helpers
# ──────────────────────────────────────────────


def _severity_from_priority(priority: str) -> RiskSeverity:
    """Map task priority to risk severity."""
    return PRIORITY_SEVERITY.get(priority.strip().lower(), RiskSeverity.MEDIUM)


def _elevate_severity(severity: RiskSeverity) -> RiskSeverity:
    """Elevate severity by one level (e.g., High → Critical)."""
    elevation = {
        RiskSeverity.LOW: RiskSeverity.MEDIUM,
        RiskSeverity.MEDIUM: RiskSeverity.HIGH,
        RiskSeverity.HIGH: RiskSeverity.CRITICAL,
        RiskSeverity.CRITICAL: RiskSeverity.CRITICAL,  # Can't go higher
    }
    return elevation[severity]


# ──────────────────────────────────────────────
# Explanation and mitigation builders
# ──────────────────────────────────────────────


def _build_explanation(
    project_name: str,
    task: Task,
    status_blocked: bool,
    comment_blocked: bool,
    blocker_detail: str,
) -> str:
    """Build a plain-English risk explanation."""
    parts: list[str] = []

    parts.append(
        f"In project {project_name}, the {task.priority.lower()}-priority task "
        f"'{task.name}' (assigned to {task.assignee or 'unassigned'})"
    )

    if status_blocked and comment_blocked:
        parts.append(
            f" has status '{task.status}' and comments indicate a blocker: "
            f'"{blocker_detail}".'
        )
    elif status_blocked:
        parts.append(f" has status '{task.status}'.")
        if task.comments:
            parts.append(f' Comments: "{task.comments[:120]}{"..." if len(task.comments) > 120 else ""}".')
    else:
        parts.append(
            f" has a blocker indicated in comments: "
            f'"{blocker_detail}".'
        )

    return "".join(parts)


def _build_mitigation(
    task: Task,
    status_blocked: bool,
    comment_blocked: bool,
    blocker_detail: str,
) -> str:
    """Build a suggested mitigation action."""
    mitigations: list[str] = []

    if status_blocked:
        mitigations.append(
            f"Escalate the blocker on '{task.name}' — identify the blocking party "
            f"and set a resolution deadline."
        )

    if comment_blocked:
        mitigations.append(
            f"Review the dependency: {blocker_detail[:80]}. "
            f"Assign an owner to chase resolution."
        )

    if task.priority.lower() in ("critical", "high"):
        mitigations.append(
            f"Consider this a priority escalation — {task.priority.lower()}-priority "
            f"work is stalled."
        )

    return " ".join(mitigations) if mitigations else "Investigate and resolve the blocker."
