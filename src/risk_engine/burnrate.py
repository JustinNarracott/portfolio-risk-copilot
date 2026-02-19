"""
Burn rate alert detection.

Calculates budget consumption vs time elapsed.
Flags projects where actual spend >90% of budget with >10% time remaining.

Sprint 1 — Week 3 deliverable.
"""

from __future__ import annotations

from datetime import date

from src.ingestion.parser import Project
from src.risk_engine.engine import Risk

SPEND_THRESHOLD = 0.90  # Flag if >90% budget spent
TIME_REMAINING_THRESHOLD = 0.10  # ...with >10% time remaining


def detect_burn_rate(project: Project, reference_date: date | None = None) -> list[Risk]:
    """Detect projects with dangerous burn rate patterns.

    Args:
        project: A parsed Project object.
        reference_date: Date to calculate against (defaults to today).

    Returns:
        List of Risk objects for burn rate alerts.
    """
    # TODO: Implement in Sprint 1, Week 3
    raise NotImplementedError
