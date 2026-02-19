"""
Core data parser for PMO project exports.

Handles CSV, JSON, and Excel (XLSX) files from Jira, Azure DevOps,
Smartsheet, MS Project, and generic exports.

Sprint 1 — Week 1 deliverable.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
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


# ──────────────────────────────────────────────
# Column name mapping — normalise variations
# ──────────────────────────────────────────────

# Maps normalised (lowercase, stripped) column names to our internal field names.
# This handles Jira, Azure DevOps, Smartsheet, and generic export variations.
COLUMN_ALIASES: dict[str, str] = {
    # Project name
    "project": "project",
    "project name": "project",
    "project_name": "project",
    "projectname": "project",
    # Project status
    "project status": "project_status",
    "project_status": "project_status",
    "projectstatus": "project_status",
    # Start date
    "start date": "start_date",
    "start_date": "start_date",
    "startdate": "start_date",
    "created": "start_date",
    "created date": "start_date",
    # End date
    "end date": "end_date",
    "end_date": "end_date",
    "enddate": "end_date",
    "due date": "end_date",
    "due_date": "end_date",
    "duedate": "end_date",
    "target date": "end_date",
    # Budget
    "budget": "budget",
    "planned cost": "budget",
    "planned_cost": "budget",
    "estimated cost": "budget",
    # Actual spend
    "actual spend": "actual_spend",
    "actual_spend": "actual_spend",
    "actualspend": "actual_spend",
    "actual cost": "actual_spend",
    "actual_cost": "actual_spend",
    "cost": "actual_spend",
    # Task name
    "task name": "task_name",
    "task_name": "task_name",
    "taskname": "task_name",
    "summary": "task_name",
    "issue": "task_name",
    "title": "task_name",
    "work item": "task_name",
    # Task status
    "task status": "task_status",
    "task_status": "task_status",
    "taskstatus": "task_status",
    "status": "task_status",
    "state": "task_status",
    # Priority
    "priority": "priority",
    "severity": "priority",
    # Assignee
    "assignee": "assignee",
    "assigned to": "assignee",
    "assigned_to": "assignee",
    "owner": "assignee",
    # Sprint
    "sprint": "sprint",
    "iteration": "sprint",
    "iteration path": "sprint",
    # Previous sprints
    "previous sprints": "previous_sprints",
    "previous_sprints": "previous_sprints",
    "sprint history": "previous_sprints",
    # Comments
    "comments": "comments",
    "comment": "comments",
    "notes": "comments",
    "description": "comments",
}

# Minimum required columns (by internal field name)
REQUIRED_FIELDS = {"project", "task_name", "task_status"}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx", ".xls"}

# Date formats to try when parsing date strings
DATE_FORMATS = [
    "%Y-%m-%d",       # 2026-01-15
    "%d/%m/%Y",       # 15/01/2026
    "%m/%d/%Y",       # 01/15/2026
    "%d-%m-%Y",       # 15-01-2026
    "%Y/%m/%d",       # 2026/01/15
    "%d %b %Y",       # 15 Jan 2026
    "%d %B %Y",       # 15 January 2026
    "%b %d, %Y",      # Jan 15, 2026
    "%B %d, %Y",      # January 15, 2026
]


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def parse_file(filepath: str | Path) -> list[Project]:
    """Parse a project export file and return a list of Project objects.

    Supports CSV, JSON, and XLSX formats. Columns are matched flexibly
    using COLUMN_ALIASES to handle Jira, Azure DevOps, Smartsheet, and
    generic export formats.

    Args:
        filepath: Path to the export file.

    Returns:
        List of Project objects with populated tasks, sorted by project name.

    Raises:
        ValueError: If file format is unsupported or required columns are missing.
        FileNotFoundError: If file does not exist.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: '{ext}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if ext == ".csv":
        return _parse_csv(path)
    elif ext == ".json":
        return _parse_json(path)
    elif ext in (".xlsx", ".xls"):
        return _parse_xlsx(path)

    # Should never reach here given the check above, but just in case
    raise ValueError(f"Unsupported file format: '{ext}'")


# ──────────────────────────────────────────────
# CSV Parser
# ──────────────────────────────────────────────


def _parse_csv(filepath: Path) -> list[Project]:
    """Parse a CSV export file into Project objects.

    Groups rows by project name. Project-level metadata (status, dates, budget)
    is taken from the first row of each project group.

    Args:
        filepath: Path to the CSV file.

    Returns:
        List of Project objects sorted by name.

    Raises:
        ValueError: If required columns are missing or file is empty.
    """
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"CSV file is empty or has no header row: {filepath}")

        # Build column mapping from CSV headers to internal field names
        col_map = _build_column_map(reader.fieldnames)

        # Check required fields are present
        mapped_fields = set(col_map.values())
        missing = REQUIRED_FIELDS - mapped_fields
        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}. "
                f"Found columns: {', '.join(reader.fieldnames)}"
            )

        # Parse rows into project groups
        return _rows_to_projects(list(reader), col_map)


def _parse_json(filepath: Path) -> list[Project]:
    """Parse a JSON export file into Project objects.

    Accepts three structures:
    1. A list of row objects (same keys as CSV headers).
    2. A dict with a 'tasks', 'issues', or 'items' key containing a list of row objects.
    3. A dict with a 'projects' key containing a list of project objects,
       each with a 'tasks' list nested inside.

    Args:
        filepath: Path to the JSON file.

    Returns:
        List of Project objects sorted by name.

    Raises:
        ValueError: If JSON structure is unrecognised or required columns are missing.
    """
    with open(filepath, encoding="utf-8-sig") as f:
        data = json.load(f)

    # Determine structure and extract flat row list
    rows: list[dict[str, Any]]

    if isinstance(data, list):
        # Structure 1: flat list of row objects
        rows = data
    elif isinstance(data, dict):
        # Structure 2: dict with a known key containing row list
        for key in ("tasks", "issues", "items", "rows", "data"):
            if key in data and isinstance(data[key], list):
                rows = data[key]
                break
        else:
            # Structure 3: dict with 'projects' key containing nested tasks
            if "projects" in data and isinstance(data["projects"], list):
                rows = _flatten_nested_projects(data["projects"])
            else:
                raise ValueError(
                    f"Unrecognised JSON structure. Expected a list of rows, "
                    f"or a dict with 'tasks'/'issues'/'items'/'projects' key. "
                    f"Found keys: {', '.join(data.keys())}"
                )
    else:
        raise ValueError(f"Unrecognised JSON structure. Expected list or dict, got {type(data).__name__}")

    if not rows:
        return []

    # Stringify all values (JSON may have ints, floats, nulls)
    str_rows = [_stringify_row(row) for row in rows]

    # Build column map from the keys of the first row
    headers = list(str_rows[0].keys()) if str_rows else []
    col_map = _build_column_map(headers)

    # Check required fields
    mapped_fields = set(col_map.values())
    missing = REQUIRED_FIELDS - mapped_fields
    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Found keys: {', '.join(headers)}"
        )

    return _rows_to_projects(str_rows, col_map)


def _flatten_nested_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten nested project structure into flat rows.

    Converts:
        [{"name": "Alpha", "status": "Active", "tasks": [{"name": "Build API", ...}]}]
    Into:
        [{"project": "Alpha", "project_status": "Active", "task_name": "Build API", ...}]
    """
    rows: list[dict[str, Any]] = []
    for proj in projects:
        project_fields = {k: v for k, v in proj.items() if k != "tasks"}
        tasks = proj.get("tasks", [])
        if not tasks:
            continue
        for task in tasks:
            row = {**project_fields, **task}
            # Ensure project name is available under a standard key
            if "project" not in row and "name" in project_fields:
                row["project"] = project_fields["name"]
            rows.append(row)
    return rows


def _stringify_row(row: dict[str, Any]) -> dict[str, str]:
    """Convert all values in a row dict to strings for consistent processing.

    Handles None, int, float, list, and other types gracefully.
    """
    result: dict[str, str] = {}
    for key, value in row.items():
        if value is None:
            result[key] = ""
        elif isinstance(value, list):
            result[key] = ";".join(str(v) for v in value)
        else:
            result[key] = str(value)
    return result


def _parse_xlsx(filepath: Path) -> list[Project]:
    """Parse an Excel export file into Project objects.

    Reads the first sheet. Uses the first row as headers.

    Args:
        filepath: Path to the XLSX/XLS file.

    Returns:
        List of Project objects sorted by name.

    Raises:
        ValueError: If required columns are missing or sheet is empty.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl is required to parse Excel files. "
            "Install it with: pip install openpyxl"
        )

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active

    if ws is None:
        wb.close()
        raise ValueError(f"Excel file has no active sheet: {filepath}")

    # Read all rows
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not all_rows or len(all_rows) < 1:
        raise ValueError(f"Excel file is empty: {filepath}")

    # First row is headers
    raw_headers = all_rows[0]
    headers = [str(h).strip() if h is not None else "" for h in raw_headers]

    if not any(headers):
        raise ValueError(f"Excel file has no header row: {filepath}")

    # Build column map
    col_map = _build_column_map(headers)

    # Check required fields
    mapped_fields = set(col_map.values())
    missing = REQUIRED_FIELDS - mapped_fields
    if missing:
        wb_close_msg = f"Found columns: {', '.join(h for h in headers if h)}"
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}. {wb_close_msg}"
        )

    # Convert data rows to list of dicts (same format as CSV DictReader output)
    str_rows: list[dict[str, str]] = []
    for row_tuple in all_rows[1:]:
        row_dict: dict[str, str] = {}
        for i, value in enumerate(row_tuple):
            if i < len(headers) and headers[i]:
                if value is None:
                    row_dict[headers[i]] = ""
                elif isinstance(value, (int, float)):
                    # Preserve numeric precision, avoid trailing .0 for integers
                    row_dict[headers[i]] = str(int(value)) if isinstance(value, float) and value == int(value) else str(value)
                elif hasattr(value, "strftime"):
                    # Handle datetime/date objects from Excel
                    row_dict[headers[i]] = value.strftime("%Y-%m-%d")
                else:
                    row_dict[headers[i]] = str(value)
        str_rows.append(row_dict)

    if not str_rows:
        return []

    return _rows_to_projects(str_rows, col_map)


# ──────────────────────────────────────────────
# Column mapping
# ──────────────────────────────────────────────


def _build_column_map(headers: list[str]) -> dict[str, str]:
    """Build a mapping from original CSV column names to internal field names.

    Uses COLUMN_ALIASES for flexible matching. Normalises headers to lowercase
    with stripped whitespace.

    Args:
        headers: List of column header strings from the CSV.

    Returns:
        Dict mapping original header name -> internal field name.
        Only includes headers that matched an alias.
    """
    col_map: dict[str, str] = {}
    for header in headers:
        normalised = header.strip().lower()
        if normalised in COLUMN_ALIASES:
            col_map[header] = COLUMN_ALIASES[normalised]
    return col_map


# ──────────────────────────────────────────────
# Row processing
# ──────────────────────────────────────────────


def _rows_to_projects(rows: list[dict[str, str]], col_map: dict[str, str]) -> list[Project]:
    """Convert parsed rows into Project objects, grouped by project name.

    Args:
        rows: List of row dicts (keys are original column names).
        col_map: Mapping from original column name -> internal field name.

    Returns:
        List of Project objects sorted by name.
    """
    if not rows:
        return []

    # Reverse map: internal field name -> original column name
    field_to_col: dict[str, str] = {v: k for k, v in col_map.items()}

    # Group rows by project
    project_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        project_name = _get_field(row, field_to_col, "project", "").strip()
        if project_name:
            project_rows[project_name].append(row)

    # Build Project objects
    projects: list[Project] = []
    for project_name, p_rows in project_rows.items():
        first_row = p_rows[0]

        project = Project(
            name=project_name,
            status=_get_field(first_row, field_to_col, "project_status", "Unknown"),
            start_date=_parse_date(_get_field(first_row, field_to_col, "start_date", "")),
            end_date=_parse_date(_get_field(first_row, field_to_col, "end_date", "")),
            budget=_parse_float(_get_field(first_row, field_to_col, "budget", "0")),
            actual_spend=_parse_float(_get_field(first_row, field_to_col, "actual_spend", "0")),
        )

        for row in p_rows:
            task = Task(
                name=_get_field(row, field_to_col, "task_name", ""),
                status=_get_field(row, field_to_col, "task_status", ""),
                priority=_get_field(row, field_to_col, "priority", "Medium"),
                assignee=_get_field(row, field_to_col, "assignee", ""),
                sprint=_get_field(row, field_to_col, "sprint", ""),
                previous_sprints=_parse_sprint_history(
                    _get_field(row, field_to_col, "previous_sprints", "")
                ),
                comments=_get_field(row, field_to_col, "comments", ""),
            )
            if task.name:  # Skip rows with no task name
                project.tasks.append(task)

        projects.append(project)

    return sorted(projects, key=lambda p: p.name)


def _get_field(row: dict[str, str], field_to_col: dict[str, str], field_name: str, default: str) -> str:
    """Safely extract a field value from a row using the column mapping.

    Args:
        row: Dict of column_name -> value.
        field_to_col: Dict of internal_field_name -> original_column_name.
        field_name: Internal field name to look up.
        default: Default value if field not found or empty.

    Returns:
        The field value as a string, or the default.
    """
    col_name = field_to_col.get(field_name)
    if col_name is None:
        return default
    value = row.get(col_name, "").strip()
    return value if value else default


# ──────────────────────────────────────────────
# Value parsers
# ──────────────────────────────────────────────


def _parse_date(value: str) -> date | None:
    """Parse a date string in common formats.

    Tries multiple date formats (ISO, UK, US, etc.) and returns the first
    successful parse. Returns None for empty or unparseable strings.

    Args:
        value: Date string to parse.

    Returns:
        A date object, or None if parsing fails.
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _parse_float(value: str) -> float:
    """Parse a numeric string into a float, handling currency symbols and commas.

    Args:
        value: Numeric string (e.g., "100000", "100,000", "$1,500.50").

    Returns:
        Float value, or 0.0 if parsing fails.
    """
    if not value or not value.strip():
        return 0.0

    # Strip currency symbols, commas, whitespace
    cleaned = value.strip()
    for char in ("\u00a3", "$", "\u20ac", ",", " "):
        cleaned = cleaned.replace(char, "")

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _parse_sprint_history(value: str) -> list[str]:
    """Parse a sprint history string into a list of sprint names.

    Handles semicolon-separated values (e.g., "Sprint 3;Sprint 4;Sprint 5").

    Args:
        value: Sprint history string.

    Returns:
        List of sprint name strings (empty list if no history).
    """
    if not value or not value.strip():
        return []

    return [s.strip() for s in value.split(";") if s.strip()]
