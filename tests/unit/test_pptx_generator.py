"""Unit tests for PPTX generator (Issue #21) — upgraded design."""

from datetime import date
from pathlib import Path

import pytest
from pptx import Presentation

from src.ingestion.parser import parse_file
from src.risk_engine.engine import PortfolioRiskReport, analyse_portfolio
from src.artefacts.pptx_generator import generate_board_slides
from src.artefacts.docx_generator import BrandConfig

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
REF_DATE = date(2026, 2, 19)


@pytest.fixture()
def report() -> PortfolioRiskReport:
    projects = parse_file(SAMPLE_CSV)
    return analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)


class TestBoardSlides:
    def test_generates_valid_pptx(self, report, tmp_path):
        result = generate_board_slides(report, output_path=tmp_path / "slides.pptx")
        assert result.exists()
        prs = Presentation(str(result))
        assert len(prs.slides) == 2

    def test_slide1_has_charts(self, report, tmp_path):
        generate_board_slides(report, output_path=tmp_path / "s.pptx")
        prs = Presentation(str(tmp_path / "s.pptx"))
        slide1 = prs.slides[0]
        # Should have chart shapes (pie + bar)
        chart_count = sum(1 for s in slide1.shapes if s.has_chart)
        assert chart_count >= 1

    def test_slide1_has_project_cards(self, report, tmp_path):
        generate_board_slides(report, output_path=tmp_path / "s.pptx")
        prs = Presentation(str(tmp_path / "s.pptx"))
        slide1 = prs.slides[0]
        # Should have multiple shapes (cards + text + charts)
        assert len(slide1.shapes) > 10

    def test_slide2_has_risk_cards(self, report, tmp_path):
        generate_board_slides(report, output_path=tmp_path / "s.pptx")
        prs = Presentation(str(tmp_path / "s.pptx"))
        slide2 = prs.slides[1]
        # Risk cards generate multiple shapes
        assert len(slide2.shapes) > 5

    def test_custom_brand_colours(self, report, tmp_path):
        brand = BrandConfig(primary_colour="990000")
        result = generate_board_slides(report, brand=brand, output_path=tmp_path / "c.pptx")
        assert result.exists()

    def test_default_output_path(self, report, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert generate_board_slides(report).name == "board-briefing.pptx"
