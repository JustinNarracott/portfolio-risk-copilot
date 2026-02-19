"""
File format validation for project exports.

Validates structure, required columns, and data types before parsing.

Sprint 1 — Week 1 deliverable.
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx", ".xls"}

REQUIRED_COLUMNS = {
    "project",
    "task_name",
    "task_status",
}

OPTIONAL_COLUMNS = {
    "project_status",
    "start_date",
    "end_date",
    "budget",
    "actual_spend",
    "priority",
    "assignee",
    "sprint",
    "previous_sprints",
    "comments",
}


def validate_file(filepath: str | Path) -> dict:
    """Validate a file before parsing.

    Returns:
        Dict with 'valid' (bool), 'errors' (list[str]), 'warnings' (list[str]).
    """
    # TODO: Implement in Sprint 1, Week 1
    raise NotImplementedError("Validator not yet implemented")
