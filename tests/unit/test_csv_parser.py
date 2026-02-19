"""Unit tests for the CSV parser (Issue #2)."""

import csv
import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import (
    Project,
    Task,
    _build_column_map,
    _parse_csv,
    _parse_date,
    _parse_float,
    _parse_sprint_history,
    parse_file,
)

# Path to sample data
SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample-data"
SAMPLE_CSV = SAMPLE_DIR / "jira-export-sample.csv"


# ──────────────────────────────────────────────
# parse_file dispatcher tests
# ──────────────────────────────────────────────


class TestParseFileDispatcher:
    """Tests for the parse_file() entry point."""

    def test_parse_csv_file(self):
        """parse_file routes .csv to CSV parser."""
        projects = parse_file(SAMPLE_CSV)
        assert len(projects) == 6

    def test_file_not_found(self):
        """Raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            parse_file("/nonexistent/file.csv")

    def test_unsupported_format(self, tmp_path):
        """Raises ValueError for unsupported file extensions."""
        bad_file = tmp_path / "data.pdf"
        bad_file.write_text("not a csv")
        with pytest.raises(ValueError, match="Unsupported file format"):
            parse_file(bad_file)

    def test_json_parses_successfully(self, tmp_path):
        """JSON parser works via parse_file dispatcher."""
        json_file = tmp_path / "data.json"
        json_file.write_text('[{"Project": "A", "Task Name": "T1", "Task Status": "Done"}]')
        projects = parse_file(json_file)
        assert len(projects) == 1

    def test_xlsx_parses_successfully(self, tmp_path):
        """XLSX parser works via parse_file dispatcher."""
        import openpyxl
        xlsx_file = tmp_path / "data.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Project", "Task Name", "Task Status"])
        ws.append(["A", "T1", "Done"])
        wb.save(xlsx_file)
        wb.close()
        projects = parse_file(xlsx_file)
        assert len(projects) == 1


# ──────────────────────────────────────────────
# CSV parser tests — sample data
# ──────────────────────────────────────────────


class TestCSVParserSampleData:
    """Tests using the real sample Jira export."""

    @pytest.fixture()
    def projects(self) -> list[Project]:
        return parse_file(SAMPLE_CSV)

    def test_returns_six_projects(self, projects):
        """Sample data contains 6 projects."""
        assert len(projects) == 6

    def test_projects_sorted_by_name(self, projects):
        """Projects are returned sorted alphabetically."""
        names = [p.name for p in projects]
        assert names == ["Alpha", "Beta", "Delta", "Epsilon", "Gamma", "Zeta"]

    def test_alpha_project_metadata(self, projects):
        """Alpha project has correct metadata."""
        alpha = next(p for p in projects if p.name == "Alpha")
        assert alpha.status == "In Progress"
        assert alpha.start_date == date(2026, 1, 6)
        assert alpha.end_date == date(2026, 6, 30)
        assert alpha.budget == 100_000.0
        assert alpha.actual_spend == 45_000.0

    def test_alpha_task_count(self, projects):
        """Alpha has 10 tasks."""
        alpha = next(p for p in projects if p.name == "Alpha")
        assert len(alpha.tasks) == 10

    def test_gamma_project_metadata(self, projects):
        """Gamma project has correct high-spend metadata."""
        gamma = next(p for p in projects if p.name == "Gamma")
        assert gamma.status == "At Risk"
        assert gamma.budget == 200_000.0
        assert gamma.actual_spend == 185_000.0

    def test_epsilon_project_metadata(self, projects):
        """Epsilon project has correct near-exhausted budget."""
        epsilon = next(p for p in projects if p.name == "Epsilon")
        assert epsilon.budget == 60_000.0
        assert epsilon.actual_spend == 58_000.0

    def test_task_fields_populated(self, projects):
        """Tasks have all expected fields populated."""
        alpha = next(p for p in projects if p.name == "Alpha")
        blocked_task = next(t for t in alpha.tasks if t.name == "Implement payment gateway")

        assert blocked_task.status == "Blocked"
        assert blocked_task.priority == "Critical"
        assert blocked_task.assignee == "Charlie Kim"
        assert blocked_task.sprint == "Sprint 5"
        assert "Blocked by third-party" in blocked_task.comments

    def test_previous_sprints_parsed(self, projects):
        """Previous sprints are parsed from semicolon-separated string."""
        gamma = next(p for p in projects if p.name == "Gamma")
        migration_task = next(t for t in gamma.tasks if t.name == "Core platform migration")

        assert migration_task.previous_sprints == ["Sprint 4", "Sprint 5", "Sprint 6", "Sprint 7"]

    def test_empty_previous_sprints(self, projects):
        """Tasks with no sprint history have empty list."""
        alpha = next(p for p in projects if p.name == "Alpha")
        design_task = next(t for t in alpha.tasks if t.name == "Design system architecture")

        assert design_task.previous_sprints == []

    def test_all_projects_have_tasks(self, projects):
        """Every project has at least one task."""
        for project in projects:
            assert len(project.tasks) > 0, f"{project.name} has no tasks"


# ──────────────────────────────────────────────
# CSV parser tests — edge cases
# ──────────────────────────────────────────────


class TestCSVParserEdgeCases:
    """Tests for edge cases and error handling."""

    def _write_csv(self, tmp_path: Path, headers: list[str], rows: list[list[str]]) -> Path:
        """Helper to write a test CSV file."""
        filepath = tmp_path / "test.csv"
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
        return filepath

    def test_empty_file(self, tmp_path):
        """Empty file raises ValueError."""
        filepath = tmp_path / "empty.csv"
        filepath.write_text("")
        with pytest.raises(ValueError, match="empty"):
            parse_file(filepath)

    def test_header_only_no_rows(self, tmp_path):
        """File with headers but no data rows returns empty list."""
        filepath = self._write_csv(
            tmp_path,
            ["Project", "Task Name", "Task Status"],
            [],
        )
        projects = parse_file(filepath)
        assert projects == []

    def test_missing_required_columns(self, tmp_path):
        """File missing required columns raises ValueError."""
        filepath = self._write_csv(
            tmp_path,
            ["Project", "Budget"],  # Missing Task Name and Task Status
            [["Alpha", "100000"]],
        )
        with pytest.raises(ValueError, match="Missing required columns"):
            parse_file(filepath)

    def test_minimal_columns(self, tmp_path):
        """File with only required columns parses successfully."""
        filepath = self._write_csv(
            tmp_path,
            ["Project", "Task Name", "Task Status"],
            [
                ["Alpha", "Build API", "In Progress"],
                ["Alpha", "Write tests", "To Do"],
                ["Beta", "Design", "Done"],
            ],
        )
        projects = parse_file(filepath)
        assert len(projects) == 2
        alpha = next(p for p in projects if p.name == "Alpha")
        assert len(alpha.tasks) == 2
        assert alpha.status == "Unknown"  # No project status column
        assert alpha.budget == 0.0  # No budget column

    def test_alternative_column_names(self, tmp_path):
        """Parser handles alternative column names (Azure DevOps style)."""
        filepath = self._write_csv(
            tmp_path,
            ["Project Name", "Summary", "State", "Assigned To", "Iteration"],
            [
                ["Alpha", "Build API", "Active", "Bob", "Sprint 5"],
            ],
        )
        projects = parse_file(filepath)
        assert len(projects) == 1
        task = projects[0].tasks[0]
        assert task.name == "Build API"
        assert task.status == "Active"
        assert task.assignee == "Bob"
        assert task.sprint == "Sprint 5"

    def test_whitespace_in_headers(self, tmp_path):
        """Parser handles whitespace in column headers."""
        filepath = self._write_csv(
            tmp_path,
            ["  Project  ", " Task Name ", " Task Status "],
            [["Alpha", "Build API", "Done"]],
        )
        projects = parse_file(filepath)
        assert len(projects) == 1

    def test_empty_task_name_rows_skipped(self, tmp_path):
        """Rows with empty task names are skipped."""
        filepath = self._write_csv(
            tmp_path,
            ["Project", "Task Name", "Task Status"],
            [
                ["Alpha", "Build API", "Done"],
                ["Alpha", "", "To Do"],  # Should be skipped
                ["Alpha", "Write tests", "To Do"],
            ],
        )
        projects = parse_file(filepath)
        alpha = projects[0]
        assert len(alpha.tasks) == 2

    def test_empty_project_name_rows_skipped(self, tmp_path):
        """Rows with empty project names are skipped."""
        filepath = self._write_csv(
            tmp_path,
            ["Project", "Task Name", "Task Status"],
            [
                ["Alpha", "Build API", "Done"],
                ["", "Orphan task", "To Do"],  # Should be skipped
            ],
        )
        projects = parse_file(filepath)
        assert len(projects) == 1

    def test_utf8_bom_handling(self, tmp_path):
        """Parser handles UTF-8 BOM (common in Excel CSV exports)."""
        filepath = tmp_path / "bom.csv"
        with open(filepath, "w", encoding="utf-8-sig") as f:
            f.write("Project,Task Name,Task Status\n")
            f.write("Alpha,Build API,Done\n")
        projects = parse_file(filepath)
        assert len(projects) == 1
        assert projects[0].name == "Alpha"

    def test_currency_in_budget(self, tmp_path):
        """Parser handles currency symbols and commas in budget fields."""
        filepath = self._write_csv(
            tmp_path,
            ["Project", "Task Name", "Task Status", "Budget", "Actual Spend"],
            [["Alpha", "Build API", "Done", "\u00a3100,000", "$45,000.50"]],
        )
        projects = parse_file(filepath)
        assert projects[0].budget == 100_000.0
        assert projects[0].actual_spend == 45_000.50


# ──────────────────────────────────────────────
# Date parser tests
# ──────────────────────────────────────────────


class TestDateParser:
    """Tests for _parse_date()."""

    def test_iso_format(self):
        assert _parse_date("2026-01-15") == date(2026, 1, 15)

    def test_uk_format(self):
        assert _parse_date("15/01/2026") == date(2026, 1, 15)

    def test_us_format(self):
        # 01/15/2026 — ambiguous, but parser tries UK first then US
        # 15 > 12, so 15/01/2026 is UK. 01/15/2026 should parse as US.
        assert _parse_date("01/15/2026") == date(2026, 1, 15)

    def test_dashes_dmy(self):
        assert _parse_date("15-01-2026") == date(2026, 1, 15)

    def test_long_month_name(self):
        assert _parse_date("15 January 2026") == date(2026, 1, 15)

    def test_short_month_name(self):
        assert _parse_date("15 Jan 2026") == date(2026, 1, 15)

    def test_us_long_format(self):
        assert _parse_date("January 15, 2026") == date(2026, 1, 15)

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_none_like(self):
        assert _parse_date("   ") is None

    def test_unparseable(self):
        assert _parse_date("not a date") is None

    def test_whitespace_stripped(self):
        assert _parse_date("  2026-01-15  ") == date(2026, 1, 15)


# ──────────────────────────────────────────────
# Float parser tests
# ──────────────────────────────────────────────


class TestFloatParser:
    """Tests for _parse_float()."""

    def test_plain_number(self):
        assert _parse_float("100000") == 100_000.0

    def test_with_commas(self):
        assert _parse_float("100,000") == 100_000.0

    def test_with_pound_sign(self):
        assert _parse_float("\u00a3100,000") == 100_000.0

    def test_with_dollar_sign(self):
        assert _parse_float("$45,000.50") == 45_000.50

    def test_with_euro_sign(self):
        assert _parse_float("\u20ac200,000") == 200_000.0

    def test_empty_string(self):
        assert _parse_float("") == 0.0

    def test_whitespace_only(self):
        assert _parse_float("   ") == 0.0

    def test_non_numeric(self):
        assert _parse_float("not a number") == 0.0

    def test_decimal(self):
        assert _parse_float("1500.75") == 1500.75


# ──────────────────────────────────────────────
# Sprint history parser tests
# ──────────────────────────────────────────────


class TestSprintHistoryParser:
    """Tests for _parse_sprint_history()."""

    def test_multiple_sprints(self):
        assert _parse_sprint_history("Sprint 3;Sprint 4;Sprint 5") == [
            "Sprint 3", "Sprint 4", "Sprint 5"
        ]

    def test_single_sprint(self):
        assert _parse_sprint_history("Sprint 4") == ["Sprint 4"]

    def test_empty_string(self):
        assert _parse_sprint_history("") == []

    def test_whitespace_only(self):
        assert _parse_sprint_history("   ") == []

    def test_trailing_semicolons(self):
        assert _parse_sprint_history("Sprint 3;Sprint 4;") == ["Sprint 3", "Sprint 4"]

    def test_whitespace_around_values(self):
        assert _parse_sprint_history(" Sprint 3 ; Sprint 4 ") == ["Sprint 3", "Sprint 4"]


# ──────────────────────────────────────────────
# Column mapping tests
# ──────────────────────────────────────────────


class TestColumnMapping:
    """Tests for _build_column_map()."""

    def test_standard_jira_headers(self):
        headers = ["Project", "Task Name", "Task Status", "Priority", "Assignee"]
        col_map = _build_column_map(headers)
        assert col_map["Project"] == "project"
        assert col_map["Task Name"] == "task_name"
        assert col_map["Task Status"] == "task_status"

    def test_devops_style_headers(self):
        headers = ["Project Name", "Summary", "State", "Assigned To"]
        col_map = _build_column_map(headers)
        assert col_map["Project Name"] == "project"
        assert col_map["Summary"] == "task_name"
        assert col_map["State"] == "task_status"
        assert col_map["Assigned To"] == "assignee"

    def test_unrecognised_headers_ignored(self):
        headers = ["Project", "Task Name", "Task Status", "Random Column", "Foo Bar"]
        col_map = _build_column_map(headers)
        assert "Random Column" not in col_map
        assert "Foo Bar" not in col_map

    def test_case_insensitive(self):
        headers = ["PROJECT", "task name", "TASK STATUS"]
        col_map = _build_column_map(headers)
        assert len(col_map) == 3
