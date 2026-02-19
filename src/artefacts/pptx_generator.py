"""
PPTX slide generator.

Generates PowerPoint briefing slides from portfolio risk analysis data.
Board briefing (1-2 slides) and steering overview (3-5 slides).

Sprint 3 — Week 8 deliverable.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from src.artefacts.docx_generator import BrandConfig
from src.risk_engine.engine import (
    PortfolioRiskReport,
    Risk,
    RiskSeverity,
)


RAG_COLOURS_PPTX = {
    "Red": RGBColor(0xC0, 0x00, 0x00),
    "Amber": RGBColor(0xED, 0x7D, 0x31),
    "Green": RGBColor(0x00, 0x80, 0x00),
}

SEVERITY_COLOURS_PPTX = {
    RiskSeverity.CRITICAL: RGBColor(0xC0, 0x00, 0x00),
    RiskSeverity.HIGH: RGBColor(0xED, 0x7D, 0x31),
    RiskSeverity.MEDIUM: RGBColor(0xBF, 0x8F, 0x00),
    RiskSeverity.LOW: RGBColor(0x00, 0x80, 0x00),
}


def generate_board_slides(
    report: PortfolioRiskReport,
    brand: BrandConfig | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Generate 1-2 slide board briefing PPTX."""
    if brand is None:
        brand = BrandConfig()

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    primary = RGBColor.from_string(brand.primary_colour)
    accent = RGBColor.from_string(brand.accent_colour)

    # Slide 1: Portfolio Overview
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = primary

    # Title
    _add_text(slide, "Portfolio Health — Board Briefing",
              Inches(0.7), Inches(0.4), Inches(12), Inches(0.8),
              font_size=Pt(28), bold=True, colour=RGBColor(0xFF, 0xFF, 0xFF),
              font_name=brand.heading_font)

    # RAG badge
    rag = report.portfolio_rag
    _add_text(slide, f"Portfolio Status: {rag}",
              Inches(0.7), Inches(1.4), Inches(4), Inches(0.6),
              font_size=Pt(18), bold=True,
              colour=RAG_COLOURS_PPTX.get(rag, RGBColor(0xFF, 0xFF, 0xFF)),
              font_name=brand.heading_font)

    # Summary stats
    stats_text = (
        f"{len(report.project_summaries)} projects  |  "
        f"{report.projects_at_risk} at risk  |  "
        f"{report.total_risks} risks identified"
    )
    _add_text(slide, stats_text,
              Inches(0.7), Inches(2.1), Inches(6), Inches(0.5),
              font_size=Pt(14), colour=RGBColor(0xCA, 0xDC, 0xFC),
              font_name=brand.body_font)

    # Project cards
    card_y = Inches(3.0)
    card_w = Inches(1.8)
    card_h = Inches(1.2)
    gap = Inches(0.2)
    start_x = Inches(0.7)

    for i, summary in enumerate(report.project_summaries):
        x = start_x + i * (card_w + gap)
        if x + card_w > Inches(12.8):
            break

        rag_col = RAG_COLOURS_PPTX.get(summary.rag_status, RGBColor(0x80, 0x80, 0x80))

        # Card background
        shape = slide.shapes.add_shape(
            1, x, card_y, card_w, card_h  # MSO_SHAPE.RECTANGLE = 1
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shape.line.fill.background()

        # Project name
        _add_text(slide, summary.project_name,
                  x + Inches(0.1), card_y + Inches(0.1), card_w - Inches(0.2), Inches(0.4),
                  font_size=Pt(11), bold=True, colour=primary, font_name=brand.heading_font)

        # RAG indicator
        _add_text(slide, summary.rag_status,
                  x + Inches(0.1), card_y + Inches(0.5), card_w - Inches(0.2), Inches(0.3),
                  font_size=Pt(14), bold=True, colour=rag_col, font_name=brand.body_font)

        # Risk count
        _add_text(slide, f"{summary.risk_count} risks",
                  x + Inches(0.1), card_y + Inches(0.85), card_w - Inches(0.2), Inches(0.25),
                  font_size=Pt(9), colour=RGBColor(0x60, 0x60, 0x60), font_name=brand.body_font)

    # Slide 2: Top Risks
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])
    slide2.background.fill.solid()
    slide2.background.fill.fore_color.rgb = RGBColor(0xF5, 0xF5, 0xF5)

    _add_text(slide2, "Top Portfolio Risks",
              Inches(0.7), Inches(0.4), Inches(12), Inches(0.7),
              font_size=Pt(24), bold=True, colour=primary, font_name=brand.heading_font)

    # Get top 3 risks
    all_risks = []
    for s in report.project_summaries:
        all_risks.extend(s.risks)
    severity_order = {RiskSeverity.CRITICAL: 0, RiskSeverity.HIGH: 1, RiskSeverity.MEDIUM: 2, RiskSeverity.LOW: 3}
    all_risks.sort(key=lambda r: severity_order.get(r.severity, 99))
    top_risks = all_risks[:3]

    risk_y = Inches(1.4)
    for risk in top_risks:
        sev_col = SEVERITY_COLOURS_PPTX.get(risk.severity, RGBColor(0, 0, 0))

        # Severity badge
        _add_text(slide2, f"[{risk.severity.value}]",
                  Inches(0.7), risk_y, Inches(1.2), Inches(0.35),
                  font_size=Pt(11), bold=True, colour=sev_col, font_name=brand.body_font)

        # Risk title
        _add_text(slide2, f"{risk.project_name}: {risk.title}",
                  Inches(2.0), risk_y, Inches(10), Inches(0.35),
                  font_size=Pt(12), bold=True, colour=RGBColor(0x33, 0x33, 0x33),
                  font_name=brand.body_font)

        # Explanation (truncated for slide)
        explanation = risk.explanation[:200] + "..." if len(risk.explanation) > 200 else risk.explanation
        _add_text(slide2, explanation,
                  Inches(2.0), risk_y + Inches(0.4), Inches(10), Inches(0.6),
                  font_size=Pt(10), colour=RGBColor(0x60, 0x60, 0x60), font_name=brand.body_font)

        risk_y += Inches(1.3)

    # Save
    if output_path is None:
        output_path = Path("board-briefing.pptx")
    else:
        output_path = Path(output_path)

    prs.save(str(output_path))
    return output_path


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _add_text(
    slide,
    text: str,
    left, top, width, height,
    font_size=Pt(12),
    bold=False,
    italic=False,
    colour=None,
    font_name="Calibri",
    align=PP_ALIGN.LEFT,
) -> None:
    """Add a text box to a slide."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = font_size
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font_name
    if colour:
        run.font.color.rgb = colour
