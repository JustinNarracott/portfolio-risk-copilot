"""
Risk aggregation and ranking engine.

Combines all risk detectors (blocked, carry-over, burn rate, dependencies)
and produces a ranked list of top N risks per project.

Sprint 1 — Week 3 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class Risk:
    """A single identified risk."""

    project_name: str
    category: RiskCategory
    severity: RiskSeverity
    title: str
    explanation: str
    suggested_mitigation: str = ""


def analyse_portfolio(projects: list[Project], top_n: int = 5) -> dict[str, list[Risk]]:
    """Run all risk detectors and return top N risks per project.

    Args:
        projects: List of parsed Project objects.
        top_n: Number of top risks to return per project.

    Returns:
        Dict mapping project name to list of Risk objects, sorted by severity.
    """
    # TODO: Implement in Sprint 1, Week 3
    raise NotImplementedError("Risk engine not yet implemented")
