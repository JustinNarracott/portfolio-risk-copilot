"""
Blocked work detection.

Scans task statuses and comments for blocked/waiting indicators.
Flags tasks blocked for >2 weeks as high severity.

Sprint 1 — Week 2 deliverable.
"""

from __future__ import annotations

from src.ingestion.parser import Project
from src.risk_engine.engine import Risk

BLOCKED_STATUSES = {"blocked", "waiting", "on hold", "on_hold"}
BLOCKER_KEYWORDS = ["blocked by", "waiting for", "waiting on", "on hold pending"]


def detect_blocked_work(project: Project) -> list[Risk]:
    """Detect tasks with blocked status or blocker keywords in comments.

    Args:
        project: A parsed Project object.

    Returns:
        List of Risk objects for blocked work found.
    """
    # TODO: Implement in Sprint 1, Week 2
    raise NotImplementedError
