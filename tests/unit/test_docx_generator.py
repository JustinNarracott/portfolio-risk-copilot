"""Unit tests for DOCX generator (Issues #18-#22) — upgraded design."""

from datetime import date
from pathlib import Path

import pytest
from docx import Document

from src.ingestion.parser import parse_file
from src.risk_engine.engine import PortfolioRiskReport, analyse_portfolio
from src.artefacts.docx_generator import (
    BrandConfig, generate_board_briefing, generate_steering_pack, generate_project_status_pack,
)

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
REF_DATE = date(2026, 2, 19)


@pytest.fixture()
def report() -> PortfolioRiskReport:
    projects = parse_file(SAMPLE_CSV)
    return analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)


def _full_text(doc: Document) -> str:
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


class TestBoardBriefing:
    def test_generates_valid_docx(self, report, tmp_path):
        result = generate_board_briefing(report, output_path=tmp_path / "b.docx")
        assert result.exists()
        assert len(Document(str(result)).paragraphs) > 0

    def test_contains_portfolio_and_rag(self, report, tmp_path):
        generate_board_briefing(report, output_path=tmp_path / "b.docx")
        text = _full_text(Document(str(tmp_path / "b.docx")))
        assert "Portfolio" in text
        assert report.portfolio_rag in text

    def test_contains_risks_and_decisions(self, report, tmp_path):
        generate_board_briefing(report, output_path=tmp_path / "b.docx")
        text = _full_text(Document(str(tmp_path / "b.docx")))
        assert "Risk" in text
        assert any(w in text for w in ("Recommended", "Decision", "decision", "URGENT"))

    def test_has_dashboard_and_rag_tables(self, report, tmp_path):
        generate_board_briefing(report, output_path=tmp_path / "b.docx")
        doc = Document(str(tmp_path / "b.docx"))
        assert len(doc.tables) >= 3  # header bar + dashboard + RAG table

    def test_all_projects_in_table(self, report, tmp_path):
        generate_board_briefing(report, output_path=tmp_path / "b.docx")
        text = _full_text(Document(str(tmp_path / "b.docx")))
        for s in report.project_summaries:
            assert s.project_name in text

    def test_default_output_path(self, report, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert generate_board_briefing(report).name == "board-briefing.docx"


class TestSteeringPack:
    def test_generates_valid_docx(self, report, tmp_path):
        result = generate_steering_pack(report, output_path=tmp_path / "s.docx")
        assert result.exists()
        assert len(Document(str(result)).paragraphs) > 10

    def test_contains_exec_summary(self, report, tmp_path):
        generate_steering_pack(report, output_path=tmp_path / "s.docx")
        text = _full_text(Document(str(tmp_path / "s.docx")))
        assert "Executive Summary" in text

    def test_contains_severity_badges(self, report, tmp_path):
        generate_steering_pack(report, output_path=tmp_path / "s.docx")
        text = _full_text(Document(str(tmp_path / "s.docx")))
        assert "CRITICAL" in text or "HIGH" in text

    def test_contains_talking_points(self, report, tmp_path):
        generate_steering_pack(report, output_path=tmp_path / "s.docx")
        text = _full_text(Document(str(tmp_path / "s.docx")))
        assert "Talking" in text

    def test_has_risk_distribution(self, report, tmp_path):
        generate_steering_pack(report, output_path=tmp_path / "s.docx")
        text = _full_text(Document(str(tmp_path / "s.docx")))
        assert "Risk Distribution" in text

    def test_more_content_than_board(self, report, tmp_path):
        generate_board_briefing(report, output_path=tmp_path / "b.docx")
        generate_steering_pack(report, output_path=tmp_path / "s.docx")
        assert len(Document(str(tmp_path / "s.docx")).paragraphs) > len(Document(str(tmp_path / "b.docx")).paragraphs)


class TestProjectStatusPack:
    def test_generates_valid_docx(self, report, tmp_path):
        assert generate_project_status_pack(report, output_path=tmp_path / "p.docx").exists()

    def test_contains_all_projects(self, report, tmp_path):
        generate_project_status_pack(report, output_path=tmp_path / "p.docx")
        text = _full_text(Document(str(tmp_path / "p.docx")))
        for s in report.project_summaries:
            assert s.project_name in text

    def test_contains_rag_values(self, report, tmp_path):
        generate_project_status_pack(report, output_path=tmp_path / "p.docx")
        text = _full_text(Document(str(tmp_path / "p.docx")))
        for rag in {s.rag_status for s in report.project_summaries}:
            assert rag in text

    def test_contains_actions(self, report, tmp_path):
        generate_project_status_pack(report, output_path=tmp_path / "p.docx")
        text = _full_text(Document(str(tmp_path / "p.docx")))
        assert "Action" in text


class TestBrandCustomisation:
    def test_custom_colours(self, report, tmp_path):
        brand = BrandConfig(primary_colour="990000", accent_colour="CC3333")
        assert generate_board_briefing(report, brand=brand, output_path=tmp_path / "c.docx").exists()

    def test_custom_headings_board(self, report, tmp_path):
        brand = BrandConfig(custom_headings={"board_title": "Monthly Portfolio Update", "top_risks": "Key Risk Areas"})
        generate_board_briefing(report, brand=brand, output_path=tmp_path / "c.docx")
        text = _full_text(Document(str(tmp_path / "c.docx")))
        assert "Monthly Portfolio Update" in text
        assert "Key Risk Areas" in text

    def test_custom_headings_steering(self, report, tmp_path):
        brand = BrandConfig(custom_headings={"steering_title": "Custom Steering Title"})
        generate_steering_pack(report, brand=brand, output_path=tmp_path / "s.docx")
        text = _full_text(Document(str(tmp_path / "s.docx")))
        assert "Custom Steering Title" in text

    def test_logo_valid(self, report, tmp_path):
        logo = tmp_path / "logo.png"
        _create_tiny_png(logo)
        brand = BrandConfig(logo_path=str(logo))
        assert generate_board_briefing(report, brand=brand, output_path=tmp_path / "l.docx").exists()

    def test_logo_invalid_ignored(self, report, tmp_path):
        brand = BrandConfig(logo_path="/nonexistent/logo.png")
        assert generate_board_briefing(report, brand=brand, output_path=tmp_path / "n.docx").exists()

    def test_custom_font(self, report, tmp_path):
        brand = BrandConfig(heading_font="Arial", body_font="Arial")
        assert generate_board_briefing(report, brand=brand, output_path=tmp_path / "f.docx").exists()


def _create_tiny_png(path: Path) -> None:
    import struct, zlib
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    raw = zlib.compress(b"\x00\xFF\x00\x00")
    idat_crc = zlib.crc32(b"IDAT" + raw) & 0xFFFFFFFF
    idat = struct.pack(">I", len(raw)) + b"IDAT" + raw + struct.pack(">I", idat_crc)
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    path.write_bytes(sig + ihdr + idat + iend)
