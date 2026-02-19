"""
Chronic carry-over detection.

Identifies tasks moved between 3+ sprints/iterations.
Flags high-priority tasks with repeated carry-over as critical.

Sprint 1 — Week 2 deliverable.
"""

from __future__ import annotations

from src.ingestion.parser import Project
from src.risk_engine.engine import Risk

CARRYOVER_THRESHOLD = 3  # Number of sprints before flagging


def detect_carryover(project: Project) -> list[Risk]:
    """Detect tasks carried over across multiple sprints.

    Args:
        project: A parsed Project object.

    Returns:
        List of Risk objects for chronic carry-over found.
    """
    # TODO: Implement in Sprint 1, Week 2
    raise NotImplementedError
