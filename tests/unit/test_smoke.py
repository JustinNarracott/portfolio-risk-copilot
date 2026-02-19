"""Smoke tests to validate project structure and imports."""

from pathlib import Path


def test_sample_data_exists():
    """Verify sample data files are present."""
    sample_dir = Path(__file__).parent.parent.parent / "sample-data"
    assert (sample_dir / "jira-export-sample.csv").exists()
    assert (sample_dir / "benefit-tracker-sample.csv").exists()


def test_imports():
    """Verify all source modules can be imported."""
    from src.ingestion.parser import Project, Task, parse_file
    from src.ingestion.validators import validate_file
    from src.risk_engine.engine import Risk, RiskCategory, RiskSeverity, analyse_portfolio
    from src.risk_engine.blocked import detect_blocked_work
    from src.risk_engine.carryover import detect_carryover
    from src.risk_engine.burnrate import detect_burn_rate
    from src.risk_engine.dependencies import detect_dependencies

    # Just verify they exist — implementation tests come in Week 1-3
    assert Project is not None
    assert Task is not None
    assert Risk is not None


def test_sample_csv_has_expected_projects():
    """Verify sample CSV contains the 6 expected projects."""
    import csv

    sample_file = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
    with open(sample_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        projects = {row["Project"] for row in reader}

    expected = {"Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"}
    assert projects == expected
