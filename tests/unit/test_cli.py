"""Unit tests for CLI entry point (Issue #24)."""

from datetime import date
from pathlib import Path

import pytest

from src.cli import main, _session, Session

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample-data"


@pytest.fixture(autouse=True)
def reset_session():
    """Reset session state before each test."""
    _session.projects = []
    _session.report = None
    _session.graph = None
    _session.brand.__init__()
    _session.reference_date = date(2026, 2, 19)
    yield


class TestCLIHelp:

    def test_no_args_shows_help(self, capsys):
        result = main([])
        assert result == 0

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0


class TestIngestCommand:

    def test_ingest_sample_data(self, capsys):
        result = main(["ingest", str(SAMPLE_DIR)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Ingested" in captured.out
        assert _session.is_loaded

    def test_ingest_invalid_folder(self, capsys):
        result = main(["ingest", "/nonexistent/folder"])
        assert result == 1

    def test_ingest_empty_folder(self, tmp_path, capsys):
        result = main(["ingest", str(tmp_path)])
        assert result == 1

    def test_ingest_sets_session_state(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        assert len(_session.projects) >= 6
        assert _session.report is not None
        assert _session.graph is not None


class TestRisksCommand:

    def test_risks_without_ingest_fails(self, capsys):
        result = main(["risks"])
        assert result == 1
        assert "No data loaded" in capsys.readouterr().err

    def test_risks_after_ingest(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["risks"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Portfolio Risk Report" in captured.out
        assert "Red" in captured.out or "Amber" in captured.out

    def test_risks_json_output(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        capsys.readouterr()  # Clear ingest output
        result = main(["risks", "--json"])
        assert result == 0
        import json
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "portfolio_rag" in parsed

    def test_risks_custom_top_n(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["risks", "--top", "3"])
        assert result == 0


class TestScenarioCommand:

    def test_scenario_without_ingest_fails(self, capsys):
        result = main(["scenario", "cut Beta scope by 30%"])
        assert result == 1

    def test_scenario_scope_cut(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["scenario", "cut Beta scope by 30%"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Scenario" in captured.out or "Impact" in captured.out

    def test_scenario_budget_increase(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["scenario", "increase Gamma budget by 50%"])
        assert result == 0

    def test_scenario_delay(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["scenario", "delay Alpha by 1 quarter"])
        assert result == 0

    def test_scenario_remove(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["scenario", "remove Delta"])
        assert result == 0

    def test_scenario_unparseable(self, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["scenario", "do something weird"])
        assert result == 1


class TestBriefCommand:

    def test_brief_without_ingest_fails(self, capsys):
        result = main(["brief", "board"])
        assert result == 1

    def test_brief_board(self, tmp_path, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["brief", "board", "--output-dir", str(tmp_path)])
        assert result == 0
        assert (tmp_path / "board-briefing.docx").exists()
        assert (tmp_path / "board-briefing.pptx").exists()

    def test_brief_steering(self, tmp_path, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["brief", "steering", "--output-dir", str(tmp_path)])
        assert result == 0
        assert (tmp_path / "steering-committee-pack.docx").exists()

    def test_brief_project(self, tmp_path, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["brief", "project", "--output-dir", str(tmp_path)])
        assert result == 0
        assert (tmp_path / "project-status-pack.docx").exists()

    def test_brief_all(self, tmp_path, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["brief", "all", "--output-dir", str(tmp_path)])
        assert result == 0
        assert (tmp_path / "board-briefing.docx").exists()
        assert (tmp_path / "board-briefing.pptx").exists()
        assert (tmp_path / "steering-committee-pack.docx").exists()
        assert (tmp_path / "project-status-pack.docx").exists()

    def test_brief_with_custom_colour(self, tmp_path, capsys):
        main(["ingest", str(SAMPLE_DIR)])
        result = main(["brief", "board", "--output-dir", str(tmp_path), "--colour", "990000"])
        assert result == 0
