"""
File format validation for project exports.

Validates file existence, extension, structure, required columns,
and basic data integrity before parsing. Designed to give users
clear, actionable feedback on what's wrong with their file.

Sprint 1 — Week 1 deliverable.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ingestion.parser import COLUMN_ALIASES, REQUIRED_FIELDS, SUPPORTED_EXTENSIONS


@dataclass
class ValidationResult:
    """Result of file validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_type: str = ""
    row_count: int = 0
    columns_found: list[str] = field(default_factory=list)
    columns_mapped: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to plain dict for backward compatibility."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "file_type": self.file_type,
            "row_count": self.row_count,
            "columns_found": self.columns_found,
            "columns_mapped": self.columns_mapped,
        }


# Optional columns we expect to see for full functionality
OPTIONAL_FIELDS = {
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


def validate_file(filepath: str | Path) -> ValidationResult:
    """Validate a file before parsing.

    Checks:
    1. File exists
    2. File extension is supported
    3. File is not empty
    4. Required columns are present (using alias matching)
    5. Warns about missing optional columns
    6. Reports row count

    Args:
        filepath: Path to the file to validate.

    Returns:
        ValidationResult with valid flag, errors, warnings, and metadata.
    """
    path = Path(filepath)
    result = ValidationResult(valid=True)

    # 1. File exists
    if not path.exists():
        result.valid = False
        result.errors.append(f"File not found: {path}")
        return result

    # 2. File extension
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        result.valid = False
        result.errors.append(
            f"Unsupported file format: '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
        return result

    result.file_type = ext

    # 3. File not empty
    if path.stat().st_size == 0:
        result.valid = False
        result.errors.append("File is empty (0 bytes).")
        return result

    # 4-6. Format-specific validation
    if ext == ".csv":
        _validate_csv(path, result)
    elif ext == ".json":
        _validate_json(path, result)
    elif ext in (".xlsx", ".xls"):
        _validate_xlsx(path, result)

    return result


def _validate_csv(filepath: Path, result: ValidationResult) -> None:
    """Validate a CSV file's structure and columns."""
    try:
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                result.valid = False
                result.errors.append("CSV file has no header row.")
                return

            headers = list(reader.fieldnames)
            result.columns_found = headers

            # Map columns
            col_map = _map_columns(headers)
            result.columns_mapped = col_map

            # Check required
            _check_required(col_map, result)

            # Check optional
            _check_optional(col_map, result)

            # Count rows
            rows = list(reader)
            result.row_count = len(rows)

            if result.row_count == 0:
                result.warnings.append("File has headers but no data rows.")

    except UnicodeDecodeError:
        result.valid = False
        result.errors.append("File encoding error. Expected UTF-8 encoded CSV.")
    except csv.Error as e:
        result.valid = False
        result.errors.append(f"CSV parsing error: {e}")


def _validate_json(filepath: Path, result: ValidationResult) -> None:
    """Validate a JSON file's structure and columns."""
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.valid = False
        result.errors.append(f"Invalid JSON: {e}")
        return

    # Determine structure and extract rows
    rows: list[dict[str, Any]] = []

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("tasks", "issues", "items", "rows", "data"):
            if key in data and isinstance(data[key], list):
                rows = data[key]
                break
        else:
            if "projects" in data and isinstance(data["projects"], list):
                # Nested — validate the nested keys instead
                projects = data["projects"]
                if projects:
                    first = projects[0]
                    headers = list(first.keys())
                    task_keys = []
                    if "tasks" in first and isinstance(first["tasks"], list) and first["tasks"]:
                        task_keys = list(first["tasks"][0].keys())
                    all_keys = headers + task_keys
                    result.columns_found = all_keys
                    col_map = _map_columns(all_keys)
                    # In nested structure, project-level 'name' maps to 'project'
                    if "project" not in col_map and "name" in [h.strip().lower() for h in headers]:
                        col_map["project"] = "name"
                    result.columns_mapped = col_map
                    _check_required(col_map, result)
                    _check_optional(col_map, result)
                    result.row_count = sum(len(p.get("tasks", [])) for p in projects)
                return
            else:
                result.valid = False
                result.errors.append(
                    "Unrecognised JSON structure. Expected a list of rows "
                    "or a dict with 'tasks'/'issues'/'items'/'projects' key."
                )
                return
    else:
        result.valid = False
        result.errors.append(f"Expected JSON list or object, got {type(data).__name__}.")
        return

    result.row_count = len(rows)

    if not rows:
        result.warnings.append("JSON contains no data rows.")
        return

    # Use first row's keys as headers
    headers = list(rows[0].keys())
    result.columns_found = headers
    col_map = _map_columns(headers)
    result.columns_mapped = col_map
    _check_required(col_map, result)
    _check_optional(col_map, result)


def _validate_xlsx(filepath: Path, result: ValidationResult) -> None:
    """Validate an Excel file's structure and columns."""
    try:
        import openpyxl
    except ImportError:
        result.valid = False
        result.errors.append("openpyxl is required to validate Excel files. pip install openpyxl")
        return

    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    except Exception as e:
        result.valid = False
        result.errors.append(f"Cannot open Excel file: {e}")
        return

    ws = wb.active
    if ws is None:
        wb.close()
        result.valid = False
        result.errors.append("Excel file has no active sheet.")
        return

    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not all_rows:
        result.valid = False
        result.errors.append("Excel file has no rows.")
        return

    # First row is headers
    headers = [str(h).strip() if h is not None else "" for h in all_rows[0]]
    headers = [h for h in headers if h]  # Remove empty headers
    result.columns_found = headers

    if not headers:
        result.valid = False
        result.errors.append("Excel file has no column headers in the first row.")
        return

    col_map = _map_columns(headers)
    result.columns_mapped = col_map
    _check_required(col_map, result)
    _check_optional(col_map, result)

    result.row_count = len(all_rows) - 1  # Exclude header row

    if result.row_count == 0:
        result.warnings.append("Excel file has headers but no data rows.")


# ──────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────


def _map_columns(headers: list[str]) -> dict[str, str]:
    """Map raw headers to internal field names using COLUMN_ALIASES.

    Returns:
        Dict mapping internal field name -> original header name.
    """
    mapped: dict[str, str] = {}
    for header in headers:
        normalised = header.strip().lower()
        if normalised in COLUMN_ALIASES:
            internal = COLUMN_ALIASES[normalised]
            if internal not in mapped:  # First match wins
                mapped[internal] = header
    return mapped


def _check_required(col_map: dict[str, str], result: ValidationResult) -> None:
    """Check that all required fields are present in the column map."""
    missing = REQUIRED_FIELDS - set(col_map.keys())
    if missing:
        result.valid = False
        result.errors.append(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Required: project name, task name, task status."
        )


def _check_optional(col_map: dict[str, str], result: ValidationResult) -> None:
    """Warn about missing optional fields that enhance analysis."""
    mapped_fields = set(col_map.keys())
    missing_optional = OPTIONAL_FIELDS - mapped_fields

    # Group warnings by importance
    high_value = {"budget", "actual_spend", "start_date", "end_date"}
    medium_value = {"priority", "sprint", "previous_sprints", "comments"}
    low_value = {"project_status", "assignee"}

    missing_high = missing_optional & high_value
    missing_medium = missing_optional & medium_value

    if missing_high:
        result.warnings.append(
            f"Missing columns for full analysis: {', '.join(sorted(missing_high))}. "
            f"Burn rate and timeline analysis will be limited."
        )

    if missing_medium:
        result.warnings.append(
            f"Missing columns: {', '.join(sorted(missing_medium))}. "
            f"Risk detection (blocked work, carry-over) may be limited."
        )
