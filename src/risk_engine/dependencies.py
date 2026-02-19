"""
Dependency keyword scanner.

Scans task comments for dependency indicators and builds
a dependency list per project.

Sprint 1 — Week 3 deliverable.
"""

from __future__ import annotations

from src.ingestion.parser import Project
from src.risk_engine.engine import Risk

DEPENDENCY_KEYWORDS = [
    "depends on",
    "dependent on",
    "blocked by",
    "waiting for",
    "prerequisite",
    "requires",
    "contingent on",
]


def detect_dependencies(project: Project) -> list[Risk]:
    """Detect tasks with unresolved dependency chains.

    Args:
        project: A parsed Project object.

    Returns:
        List of Risk objects for dependency risks found.
    """
    # TODO: Implement in Sprint 1, Week 3
    raise NotImplementedError
