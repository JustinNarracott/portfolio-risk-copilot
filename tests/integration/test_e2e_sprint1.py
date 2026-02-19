"""End-to-end integration test for Sprint 1 (Issue #10).

Tests the complete pipeline: file upload → parse → validate → analyse → JSON output.
Acceptance criteria from PID:
  - Upload Jira CSV (100-500 rows) → receive ranked risk list in <30 seconds.
  - Risk explanations are plain-English and actionable.
  - All risk patterns working (blocked, carry-over, burn rate, dependencies).
"""

import json
import time
from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import parse_file
from src.ingestion.validators import validate_file
from src.risk_engine.engine import (
    PortfolioRiskReport,
    RiskCategory,
    RiskSeverity,
    analyse_portfolio,
)

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample-data"
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_CSV = SAMPLE_DIR / "jira-export-sample.csv"
FLAT_JSON = FIXTURE_DIR / "jira-export-flat.json"
SAMPLE_XLSX = FIXTURE_DIR / "jira-export-sample.xlsx"

REF_DATE = date(2026, 2, 19)


# ──────────────────────────────────────────────
# Full pipeline: validate → parse → analyse
# ──────────────────────────────────────────────


class TestEndToEndCSV:
    """Full pipeline with CSV input."""

    def test_completes_under_30_seconds(self):
        """PID acceptance: ranked risk list in <30 seconds."""
        start = time.time()
        validation = validate_file(SAMPLE_CSV)
        assert validation.valid
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        elapsed = time.time() - start
        assert elapsed < 30.0, f"Pipeline took {elapsed:.2f}s (limit: 30s)"

    def test_produces_valid_report(self):
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        assert isinstance(report, PortfolioRiskReport)
        assert len(report.project_summaries) == 6
        assert report.total_risks > 0

    def test_json_serialisable(self):
        """Output must be JSON-serialisable for downstream consumers."""
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        json_str = json.dumps(report.to_dict(), indent=2)
        parsed = json.loads(json_str)
        assert "project_summaries" in parsed
        assert parsed["portfolio_rag"] in ("Red", "Amber", "Green")

    def test_all_risk_categories_present(self):
        """All four risk detectors should find at least one risk."""
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=10, reference_date=REF_DATE)
        all_categories = set()
        for summary in report.project_summaries:
            for risk in summary.risks:
                all_categories.add(risk.category)
        assert RiskCategory.BLOCKED_WORK in all_categories
        assert RiskCategory.CHRONIC_CARRYOVER in all_categories
        assert RiskCategory.BURN_RATE in all_categories
        assert RiskCategory.DEPENDENCY in all_categories

    def test_explanations_are_plain_english(self):
        """PID acceptance: risk explanations are plain-English."""
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        for summary in report.project_summaries:
            for risk in summary.risks:
                # Should contain project name
                assert risk.project_name in risk.explanation or risk.project_name.lower() in risk.explanation.lower()
                # Should be readable (minimum length)
                assert len(risk.explanation) >= 40, f"Too short: {risk.explanation}"
                # Should not contain raw code/JSON
                assert "{" not in risk.explanation, f"Contains code: {risk.explanation}"

    def test_top_5_per_project(self):
        """Each project should have at most 5 risks (top_n=5)."""
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        for summary in report.project_summaries:
            assert summary.risk_count <= 5

    def test_expected_project_rag_statuses(self):
        """Validate known risk patterns in sample data."""
        projects = parse_file(SAMPLE_CSV)
        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        rag = {s.project_name: s.rag_status for s in report.project_summaries}

        # High-risk projects (baked into sample data)
        assert rag["Gamma"] == "Red"    # 92.5% budget + 4-sprint carry-over
        assert rag["Epsilon"] == "Red"   # 96.7% budget consumed
        assert rag["Alpha"] == "Red"     # Blocked + dependencies

        # Lower-risk projects
        assert rag["Delta"] in ("Green", "Amber")  # Control case


class TestEndToEndJSON:
    """Full pipeline with JSON input."""

    def test_produces_same_results_as_csv(self):
        csv_projects = parse_file(SAMPLE_CSV)
        json_projects = parse_file(FLAT_JSON)

        csv_report = analyse_portfolio(csv_projects, top_n=5, reference_date=REF_DATE)
        json_report = analyse_portfolio(json_projects, top_n=5, reference_date=REF_DATE)

        assert csv_report.total_risks == json_report.total_risks
        assert csv_report.portfolio_rag == json_report.portfolio_rag
        assert csv_report.projects_at_risk == json_report.projects_at_risk


class TestEndToEndXLSX:
    """Full pipeline with Excel input."""

    def test_produces_same_results_as_csv(self):
        csv_projects = parse_file(SAMPLE_CSV)
        xlsx_projects = parse_file(SAMPLE_XLSX)

        csv_report = analyse_portfolio(csv_projects, top_n=5, reference_date=REF_DATE)
        xlsx_report = analyse_portfolio(xlsx_projects, top_n=5, reference_date=REF_DATE)

        assert csv_report.total_risks == xlsx_report.total_risks
        assert csv_report.portfolio_rag == xlsx_report.portfolio_rag


# ──────────────────────────────────────────────
# Validation → parse → analyse pipeline
# ──────────────────────────────────────────────


class TestValidationIntegration:
    """Validate file first, then parse and analyse."""

    def test_invalid_file_caught_before_parse(self, tmp_path):
        """Invalid file should be caught by validator, not crash parser."""
        bad_file = tmp_path / "bad.csv"
        bad_file.write_text("Foo,Bar\nval1,val2\n")

        result = validate_file(bad_file)
        assert result.valid is False
        assert any("missing required" in e.lower() for e in result.errors)

    def test_valid_file_full_pipeline(self):
        result = validate_file(SAMPLE_CSV)
        assert result.valid is True
        assert result.row_count == 48

        projects = parse_file(SAMPLE_CSV)
        assert len(projects) == 6

        report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
        assert report.portfolio_rag == "Red"


# ──────────────────────────────────────────────
# Output quality checks
# ──────────────────────────────────────────────


class TestOutputQuality:
    """Ensure the output is suitable for downstream artefact generation."""

    @pytest.fixture()
    def report(self) -> PortfolioRiskReport:
        projects = parse_file(SAMPLE_CSV)
        return analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)

    def test_every_risk_has_mitigation(self, report):
        for summary in report.project_summaries:
            for risk in summary.risks:
                assert risk.suggested_mitigation, f"No mitigation: {risk.title}"

    def test_project_names_match_input(self, report):
        expected = {"Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"}
        actual = {s.project_name for s in report.project_summaries}
        assert actual == expected

    def test_report_structure_for_artefact_gen(self, report):
        """Verify the report has all fields needed for Sprint 3 briefing generation."""
        d = report.to_dict()

        # Portfolio level
        assert "total_risks" in d
        assert "projects_at_risk" in d
        assert "portfolio_rag" in d

        # Project level
        for ps in d["project_summaries"]:
            assert "project_name" in ps
            assert "rag_status" in ps
            assert "risks" in ps
            for risk in ps["risks"]:
                assert "category" in risk
                assert "severity" in risk
                assert "title" in risk
                assert "explanation" in risk
                assert "suggested_mitigation" in risk
