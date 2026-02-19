"""
Dependency keyword scanner.

Scans task comments for dependency indicators and flags tasks
with unresolved dependency chains. Extracts the dependency target
where possible for clearer reporting.

Sprint 1 — Week 3 deliverable.
"""

from __future__ import annotations

import re

from src.ingestion.parser import Project, Task
from src.risk_engine.engine import Risk, RiskCategory, RiskSeverity

# Keywords that indicate a dependency relationship
DEPENDENCY_KEYWORDS = [
    "depends on",
    "dependent on",
    "blocked by",
    "waiting for",
    "waiting on",
    "prerequisite",
    "requires",
    "contingent on",
    "cannot proceed until",
    "needs",
]

# Statuses that indicate the task is still active (dependency matters)
ACTIVE_STATUSES = {
    "to do", "todo", "in progress", "in-progress", "open", "new",
    "blocked", "waiting", "on hold", "on_hold", "on-hold",
}

# Priority mapping
PRIORITY_SEVERITY: dict[str, RiskSeverity] = {
    "critical": RiskSeverity.CRITICAL,
    "high": RiskSeverity.HIGH,
    "medium": RiskSeverity.MEDIUM,
    "low": RiskSeverity.LOW,
}


def detect_dependencies(project: Project) -> list[Risk]:
    """Detect tasks with unresolved dependency chains in comments.

    Only flags tasks that are still active (not Done/Complete). Extracts
    the dependency target from the comment where possible.

    Args:
        project: A parsed Project object.

    Returns:
        List of Risk objects for dependency risks, sorted by severity.
    """
    risks: list[Risk] = []

    for task in project.tasks:
        # Skip completed tasks
        if not _is_active(task):
            continue

        # Find dependency keywords in comments
        matches = _find_dependency_matches(task)
        if not matches:
            continue

        # Count dependencies — more = higher risk
        dep_count = len(matches)
        severity = _calculate_severity(task, dep_count)

        # Build dependency summary
        dep_descriptions = [m["context"] for m in matches]
        dep_summary = "; ".join(dep_descriptions[:3])

        explanation = (
            f"'{task.name}' ({task.assignee or 'unassigned'}) is tangled in "
            f"{dep_count} {'dependencies' if dep_count > 1 else 'dependency'}: "
            f"{dep_summary}. "
            f"{'Multiple dependencies compound the risk — if any one slips, this task stalls.' if dep_count > 1 else 'If this dependency slips, the task stalls.'}"
        )

        mitigation = _build_mitigation(task, matches, dep_count)

        title = (
            f"'{task.name}': {dep_count} "
            f"{'dependencies' if dep_count > 1 else 'dependency'} — delivery at risk"
        )

        risks.append(Risk(
            project_name=project.name,
            category=RiskCategory.DEPENDENCY,
            severity=severity,
            title=title,
            explanation=explanation,
            suggested_mitigation=mitigation,
        ))

    # Sort by severity
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


def _is_active(task: Task) -> bool:
    """Check if task is still in an active state."""
    return task.status.strip().lower() in ACTIVE_STATUSES


def _find_dependency_matches(task: Task) -> list[dict[str, str]]:
    """Find dependency keywords in task comments and extract context.

    Returns:
        List of dicts with 'keyword' and 'context' (surrounding text).
    """
    if not task.comments:
        return []

    comments_lower = task.comments.lower()
    matches: list[dict[str, str]] = []
    seen_positions: set[int] = set()  # Avoid duplicate matches at same position

    for keyword in DEPENDENCY_KEYWORDS:
        pos = 0
        while True:
            pos = comments_lower.find(keyword, pos)
            if pos == -1:
                break

            # Skip if we've already matched at this position (overlapping keywords)
            if pos in seen_positions:
                pos += 1
                continue

            seen_positions.add(pos)

            # Extract context: the rest of the sentence after the keyword
            context = _extract_context(task.comments, pos, keyword)

            matches.append({
                "keyword": keyword,
                "context": context,
            })

            pos += len(keyword)

    return matches


def _extract_context(text: str, keyword_pos: int, keyword: str) -> str:
    """Extract the dependency target/context after the keyword.

    E.g., "Depends on API completion from Bob" → "API completion from Bob"
    """
    after_keyword = text[keyword_pos + len(keyword):].strip()

    # Take up to the next sentence boundary or 80 chars
    end_markers = [". ", ".\n", "\n", ";", ","]
    end_pos = len(after_keyword)

    for marker in end_markers:
        idx = after_keyword.find(marker)
        if idx != -1 and idx < end_pos:
            end_pos = idx

    context = after_keyword[:min(end_pos, 80)].strip()

    # Clean up leading punctuation/whitespace
    context = context.lstrip(":- ")

    return context if context else keyword


# ──────────────────────────────────────────────
# Severity and mitigation
# ──────────────────────────────────────────────


def _calculate_severity(task: Task, dep_count: int) -> RiskSeverity:
    """Calculate severity from task priority and dependency count."""
    base = PRIORITY_SEVERITY.get(task.priority.strip().lower(), RiskSeverity.MEDIUM)

    # Elevate if multiple dependencies
    if dep_count >= 3:
        elevation = {
            RiskSeverity.LOW: RiskSeverity.HIGH,
            RiskSeverity.MEDIUM: RiskSeverity.HIGH,
            RiskSeverity.HIGH: RiskSeverity.CRITICAL,
            RiskSeverity.CRITICAL: RiskSeverity.CRITICAL,
        }
        return elevation[base]
    elif dep_count >= 2:
        elevation = {
            RiskSeverity.LOW: RiskSeverity.MEDIUM,
            RiskSeverity.MEDIUM: RiskSeverity.HIGH,
            RiskSeverity.HIGH: RiskSeverity.CRITICAL,
            RiskSeverity.CRITICAL: RiskSeverity.CRITICAL,
        }
        return elevation[base]

    return base


def _build_mitigation(task: Task, matches: list[dict[str, str]], dep_count: int) -> str:
    """Build mitigation suggestion."""
    parts: list[str] = []

    if dep_count == 1:
        parts.append(
            f"Confirm the dependency status for '{task.name}': {matches[0]['context']}. "
            f"Identify the owner and agree a resolution date."
        )
    else:
        parts.append(
            f"Task '{task.name}' has {dep_count} dependencies — review whether "
            f"all are genuine blockers or if any can be decoupled. "
            f"Assign an owner to each dependency for resolution tracking."
        )

    if task.priority.lower() in ("critical", "high"):
        parts.append(
            f"As a {task.priority.lower()}-priority item, unresolved dependencies "
            f"should be escalated to the project lead."
        )

    return " ".join(parts)
