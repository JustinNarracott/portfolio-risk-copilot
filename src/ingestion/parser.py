"""
Core data parser for PMO project exports.

Handles CSV, JSON, and Excel (XLSX) files from Jira, Azure DevOps,
Smartsheet, MS Project, and generic exports.

Sprint 1 — Week 1 deliverable.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass
class Task:
    """Represents a single task/issue from a project export."""

    name: str
    status: str
    priority: str = "Medium"
    assignee: str = ""
    sprint: str = ""
    previous_sprints: list[str] = field(default_factory=list)
    comments: str = ""


@dataclass
class Project:
    """Represents a project with its metadata and tasks."""

    name: str
    status: str
    start_date: date | None = None
    end_date: date | None = None
    budget: float = 0.0
    actual_spend: float = 0.0
    tasks: list[Task] = field(default_factory=list)


def parse_file(filepath: str | Path) -> list[Project]:
    """Parse a project export file and return a list of Project objects.

    Supports CSV, JSON, and XLSX formats.

    Args:
        filepath: Path to the export file.

    Returns:
        List of Project objects with populated tasks.

    Raises:
        ValueError: If file format is unsupported or file is malformed.
        FileNotFoundError: If file does not exist.
    """
    # TODO: Implement in Sprint 1, Week 1
    raise NotImplementedError("Parser not yet implemented")


def _parse_csv(filepath: Path) -> list[Project]:
    """Parse a CSV export file."""
    # TODO: Implement
    raise NotImplementedError


def _parse_json(filepath: Path) -> list[Project]:
    """Parse a JSON export file."""
    # TODO: Implement
    raise NotImplementedError


def _parse_xlsx(filepath: Path) -> list[Project]:
    """Parse an Excel export file."""
    # TODO: Implement
    raise NotImplementedError


def _parse_date(value: str) -> date | None:
    """Parse a date string in common formats (YYYY-MM-DD, DD/MM/YYYY, etc.)."""
    # TODO: Implement
    raise NotImplementedError
