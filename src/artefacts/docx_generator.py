"""
DOCX document generator.

Generates exec-ready Word briefings from portfolio risk analysis data.
Supports three templates: board briefing, steering committee pack,
and project status pack.

Sprint 3 — Weeks 7-8 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

from src.risk_engine.engine import (
    PortfolioRiskReport,
    ProjectRiskSummary,
    Risk,
    RiskSeverity,
)


@dataclass
class BrandConfig:
    """User-customisable branding for generated documents."""

    logo_path: str | None = None
    primary_colour: str = "1F4E79"   # Dark blue
    accent_colour: str = "2E75B6"    # Medium blue
    heading_font: str = "Calibri"
    body_font: str = "Calibri"
    company_name: str = ""
    # Custom section headings (optional overrides)
    custom_headings: dict[str, str] = field(default_factory=dict)


# ──────────────────────────────────────────────
# RAG colour mapping
# ──────────────────────────────────────────────

RAG_COLOURS = {
    "Red": RGBColor(0xC0, 0x00, 0x00),
    "Amber": RGBColor(0xED, 0x7D, 0x31),
    "Green": RGBColor(0x00, 0x80, 0x00),
}

RAG_BG_COLOURS = {
    "Red": "F2DCDB",
    "Amber": "FDE9D9",
    "Green": "D8E4BC",
}

SEVERITY_COLOURS = {
    RiskSeverity.CRITICAL: RGBColor(0xC0, 0x00, 0x00),
    RiskSeverity.HIGH: RGBColor(0xED, 0x7D, 0x31),
    RiskSeverity.MEDIUM: RGBColor(0xBF, 0x8F, 0x00),
    RiskSeverity.LOW: RGBColor(0x00, 0x80, 0x00),
}


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def generate_board_briefing(
    report: PortfolioRiskReport,
    brand: BrandConfig | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Generate a 1-page board briefing DOCX.

    Content: Portfolio health RAG, top 3 risks, 3 recommended decisions,
    project-level RAG table.
    """
    if brand is None:
        brand = BrandConfig()

    doc = Document()
    _apply_styles(doc, brand)

    # Title
    _add_title(doc, brand, _heading(brand, "board_title", "Portfolio Health — Board Briefing"))

    # Logo
    if brand.logo_path and Path(brand.logo_path).exists():
        doc.add_picture(brand.logo_path, width=Inches(1.5))

    # Portfolio RAG summary
    _add_heading(doc, brand, _heading(brand, "rag_summary", "Portfolio Status"), level=1)
    _add_rag_summary_paragraph(doc, report)

    # Project RAG table
    _add_heading(doc, brand, _heading(brand, "project_table", "Project Overview"), level=1)
    _add_project_rag_table(doc, report, brand)

    # Top 3 risks
    _add_heading(doc, brand, _heading(brand, "top_risks", "Top Risks"), level=1)
    top_risks = _get_top_n_risks(report, n=3)
    for i, risk in enumerate(top_risks, 1):
        _add_risk_paragraph(doc, risk, index=i)

    # Recommended decisions
    _add_heading(doc, brand, _heading(brand, "decisions", "Recommended Decisions"), level=1)
    decisions = _generate_decisions(report, n=3)
    for i, decision in enumerate(decisions, 1):
        p = doc.add_paragraph()
        run = p.add_run(f"{i}. {decision}")
        run.font.size = Pt(10)

    # Save
    if output_path is None:
        output_path = Path("board-briefing.docx")
    else:
        output_path = Path(output_path)

    doc.save(str(output_path))
    return output_path


def generate_steering_pack(
    report: PortfolioRiskReport,
    brand: BrandConfig | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Generate a 2-3 page steering committee pack DOCX.

    Content: Exec summary, top 5 risks with explanations and mitigations,
    3 recommended decisions, project-level RAG table with status and forecast,
    key trade-offs and talking points.
    """
    if brand is None:
        brand = BrandConfig()

    doc = Document()
    _apply_styles(doc, brand)

    # Title
    _add_title(doc, brand, _heading(brand, "steering_title", "Portfolio Risk & Value Briefing — Steering Committee"))

    if brand.logo_path and Path(brand.logo_path).exists():
        doc.add_picture(brand.logo_path, width=Inches(1.5))

    # Exec summary
    _add_heading(doc, brand, _heading(brand, "exec_summary", "Executive Summary"), level=1)
    _add_exec_summary(doc, report)

    # Project RAG table
    _add_heading(doc, brand, _heading(brand, "project_table", "Project Overview"), level=1)
    _add_project_rag_table(doc, report, brand, detailed=True)

    # Top 5 risks
    _add_heading(doc, brand, _heading(brand, "top_risks", "Top Portfolio Risks"), level=1)
    top_risks = _get_top_n_risks(report, n=5)
    for i, risk in enumerate(top_risks, 1):
        _add_risk_paragraph(doc, risk, index=i, include_mitigation=True)

    # Recommended decisions
    _add_heading(doc, brand, _heading(brand, "decisions", "Recommended Decisions"), level=1)
    decisions = _generate_decisions(report, n=3)
    for i, decision in enumerate(decisions, 1):
        p = doc.add_paragraph()
        run = p.add_run(f"{i}. {decision}")
        run.font.size = Pt(10)

    # Talking points
    _add_heading(doc, brand, _heading(brand, "talking_points", "Key Talking Points"), level=1)
    talking_points = _generate_talking_points(report)
    for point in talking_points:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(point)
        run.font.size = Pt(10)

    # Save
    if output_path is None:
        output_path = Path("steering-committee-pack.docx")
    else:
        output_path = Path(output_path)

    doc.save(str(output_path))
    return output_path


def generate_project_status_pack(
    report: PortfolioRiskReport,
    brand: BrandConfig | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Generate per-project status pack DOCX (1-2 pages per project).

    Content per project: RAG status with explanation, risk list with severities,
    forecast delta (budget, timeline), action items.
    """
    if brand is None:
        brand = BrandConfig()

    doc = Document()
    _apply_styles(doc, brand)

    _add_title(doc, brand, _heading(brand, "status_title", "Project Status Pack"))

    if brand.logo_path and Path(brand.logo_path).exists():
        doc.add_picture(brand.logo_path, width=Inches(1.5))

    for idx, summary in enumerate(report.project_summaries):
        if idx > 0:
            doc.add_page_break()

        # Project header
        _add_heading(doc, brand, f"Project: {summary.project_name}", level=1)

        # RAG status
        p = doc.add_paragraph()
        p.add_run("Status: ").bold = True
        rag_run = p.add_run(summary.rag_status)
        rag_run.font.color.rgb = RAG_COLOURS.get(summary.rag_status, RGBColor(0, 0, 0))
        rag_run.bold = True
        p.add_run(f"  ({summary.project_status})")

        # Risk list
        if summary.risks:
            _add_heading(doc, brand, "Risks", level=2)
            for risk in summary.risks:
                _add_risk_paragraph(doc, risk, include_mitigation=True)
        else:
            p = doc.add_paragraph()
            p.add_run("No significant risks identified.").italic = True

        # Action items
        _add_heading(doc, brand, "Action Items", level=2)
        actions = _generate_project_actions(summary)
        if actions:
            for action in actions:
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(action)
                run.font.size = Pt(10)
        else:
            p = doc.add_paragraph()
            p.add_run("No immediate actions required.").italic = True

    # Save
    if output_path is None:
        output_path = Path("project-status-pack.docx")
    else:
        output_path = Path(output_path)

    doc.save(str(output_path))
    return output_path


# ──────────────────────────────────────────────
# Styling helpers
# ──────────────────────────────────────────────


def _apply_styles(doc: Document, brand: BrandConfig) -> None:
    """Apply base styles to the document."""
    style = doc.styles["Normal"]
    style.font.name = brand.body_font
    style.font.size = Pt(10)
    style.paragraph_format.space_after = Pt(6)

    # Narrow margins for more content space
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)


def _add_title(doc: Document, brand: BrandConfig, text: str) -> None:
    """Add a document title."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.color.rgb = RGBColor.from_string(brand.primary_colour)
    run.font.name = brand.heading_font
    p.paragraph_format.space_after = Pt(12)


def _add_heading(doc: Document, brand: BrandConfig, text: str, level: int = 1) -> None:
    """Add a styled heading."""
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor.from_string(brand.primary_colour)
        run.font.name = brand.heading_font


def _heading(brand: BrandConfig, key: str, default: str) -> str:
    """Get a custom heading or use default."""
    return brand.custom_headings.get(key, default)


# ──────────────────────────────────────────────
# Content builders
# ──────────────────────────────────────────────


def _add_rag_summary_paragraph(doc: Document, report: PortfolioRiskReport) -> None:
    """Add portfolio-level RAG summary."""
    p = doc.add_paragraph()
    p.add_run("Overall Portfolio Status: ").bold = True
    rag_run = p.add_run(report.portfolio_rag)
    rag_run.font.color.rgb = RAG_COLOURS.get(report.portfolio_rag, RGBColor(0, 0, 0))
    rag_run.bold = True
    p.add_run(f"\n{report.projects_at_risk} of {len(report.project_summaries)} projects have active risks. "
              f"{report.total_risks} risks identified across the portfolio.")


def _add_exec_summary(doc: Document, report: PortfolioRiskReport) -> None:
    """Add executive summary for steering pack."""
    total = len(report.project_summaries)
    reds = sum(1 for s in report.project_summaries if s.rag_status == "Red")
    ambers = sum(1 for s in report.project_summaries if s.rag_status == "Amber")
    greens = sum(1 for s in report.project_summaries if s.rag_status == "Green")

    p = doc.add_paragraph()
    p.add_run(f"The portfolio comprises {total} active projects. ").font.size = Pt(10)
    p.add_run(f"{reds} are rated Red, {ambers} Amber, and {greens} Green. ").font.size = Pt(10)
    p.add_run(f"{report.total_risks} risks have been identified, "
              f"with {report.projects_at_risk} projects requiring attention. ").font.size = Pt(10)

    if reds > 0:
        red_names = [s.project_name for s in report.project_summaries if s.rag_status == "Red"]
        p.add_run(f"Projects requiring immediate attention: {', '.join(red_names)}.").font.size = Pt(10)


def _add_project_rag_table(
    doc: Document,
    report: PortfolioRiskReport,
    brand: BrandConfig,
    detailed: bool = False,
) -> None:
    """Add a project RAG status table."""
    if detailed:
        headers = ["Project", "Status", "RAG", "Risks", "Top Risk"]
        col_count = 5
    else:
        headers = ["Project", "Status", "RAG", "Risks"]
        col_count = 4

    table = doc.add_table(rows=1, cols=col_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header row
    header_row = table.rows[0]
    for i, text in enumerate(headers):
        cell = header_row.cells[i]
        cell.text = text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_bg(cell, brand.primary_colour)

    # Data rows
    for summary in report.project_summaries:
        row = table.add_row()
        row.cells[0].text = summary.project_name
        row.cells[1].text = summary.project_status
        row.cells[2].text = summary.rag_status
        row.cells[3].text = str(summary.risk_count)

        # Colour the RAG cell
        _set_cell_bg(row.cells[2], RAG_BG_COLOURS.get(summary.rag_status, "FFFFFF"))

        if detailed and summary.risks:
            row.cells[4].text = summary.risks[0].title

        # Style all cells
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)


def _add_risk_paragraph(
    doc: Document,
    risk: Risk,
    index: int | None = None,
    include_mitigation: bool = False,
) -> None:
    """Add a risk with severity badge, explanation, and optional mitigation."""
    p = doc.add_paragraph()

    # Severity indicator
    severity_run = p.add_run(f"[{risk.severity.value}] ")
    severity_run.font.color.rgb = SEVERITY_COLOURS.get(risk.severity, RGBColor(0, 0, 0))
    severity_run.font.bold = True
    severity_run.font.size = Pt(10)

    # Title
    prefix = f"{index}. " if index else ""
    title_run = p.add_run(f"{prefix}{risk.title}")
    title_run.font.bold = True
    title_run.font.size = Pt(10)

    # Explanation
    p2 = doc.add_paragraph()
    exp_run = p2.add_run(risk.explanation)
    exp_run.font.size = Pt(9)
    p2.paragraph_format.space_after = Pt(2)

    # Mitigation
    if include_mitigation and risk.suggested_mitigation:
        p3 = doc.add_paragraph()
        p3.add_run("Mitigation: ").font.size = Pt(9)
        p3.runs[0].bold = True
        mit_run = p3.add_run(risk.suggested_mitigation)
        mit_run.font.size = Pt(9)
        mit_run.font.italic = True
        p3.paragraph_format.space_after = Pt(6)


def _generate_decisions(report: PortfolioRiskReport, n: int = 3) -> list[str]:
    """Generate recommended decisions from portfolio data."""
    decisions: list[str] = []

    red_projects = [s for s in report.project_summaries if s.rag_status == "Red"]
    amber_projects = [s for s in report.project_summaries if s.rag_status == "Amber"]

    if red_projects:
        names = ", ".join(s.project_name for s in red_projects[:3])
        decisions.append(
            f"Escalate {names} to executive review — these projects have Critical/High risks "
            f"requiring immediate intervention."
        )

    # Look for burn rate risks
    burn_risks = []
    for s in report.project_summaries:
        for r in s.risks:
            if r.category.value == "Burn Rate":
                burn_risks.append(r)
    if burn_risks:
        names = ", ".join(set(r.project_name for r in burn_risks[:2]))
        decisions.append(
            f"Review budget allocation for {names} — current burn rate indicates "
            f"budget exhaustion before delivery completion."
        )

    # Blocked work decisions
    blocked_risks = []
    for s in report.project_summaries:
        for r in s.risks:
            if r.category.value == "Blocked Work":
                blocked_risks.append(r)
    if blocked_risks:
        names = ", ".join(set(r.project_name for r in blocked_risks[:2]))
        decisions.append(
            f"Unblock delivery on {names} — assign owners to resolve blockers "
            f"and set resolution deadlines within 5 working days."
        )

    if amber_projects and len(decisions) < n:
        names = ", ".join(s.project_name for s in amber_projects[:2])
        decisions.append(
            f"Monitor {names} closely — these projects show emerging risks "
            f"that could escalate without attention."
        )

    if len(decisions) < n:
        decisions.append(
            "Schedule portfolio review in 2 weeks to reassess risk posture "
            "and track resolution of identified issues."
        )

    return decisions[:n]


def _generate_talking_points(report: PortfolioRiskReport) -> list[str]:
    """Generate talking points for steering committee discussion."""
    points: list[str] = []
    total = len(report.project_summaries)
    reds = sum(1 for s in report.project_summaries if s.rag_status == "Red")

    points.append(
        f"Portfolio health: {reds} of {total} projects are Red status, "
        f"requiring leadership attention this cycle."
    )

    if report.total_risks > 0:
        categories = {}
        for s in report.project_summaries:
            for r in s.risks:
                cat = r.category.value
                categories[cat] = categories.get(cat, 0) + 1
        top_cat = max(categories, key=categories.get) if categories else "N/A"
        points.append(
            f"The most common risk category is '{top_cat}' "
            f"({categories.get(top_cat, 0)} instances across the portfolio)."
        )

    points.append(
        "Key question for the committee: Are we comfortable with the current "
        "risk exposure, or do we need to reallocate resources?"
    )

    return points


def _generate_project_actions(summary: ProjectRiskSummary) -> list[str]:
    """Generate action items for a specific project."""
    actions: list[str] = []

    for risk in summary.risks[:3]:
        if risk.suggested_mitigation:
            # Take first sentence of mitigation as an action
            first_sentence = risk.suggested_mitigation.split(". ")[0]
            actions.append(f"{first_sentence}.")

    if not actions:
        if summary.rag_status == "Green":
            actions.append("Continue on current trajectory. No escalation needed.")

    return actions


# ──────────────────────────────────────────────
# Table helpers
# ──────────────────────────────────────────────


def _set_cell_bg(cell, colour_hex: str) -> None:
    """Set background colour of a table cell."""
    shading = cell._element.get_or_add_tcPr()
    shading_elm = shading.find(qn("w:shd"))
    if shading_elm is None:
        from docx.oxml import OxmlElement
        shading_elm = OxmlElement("w:shd")
        shading.append(shading_elm)
    shading_elm.set(qn("w:fill"), colour_hex)
    shading_elm.set(qn("w:val"), "clear")


def _get_top_n_risks(report: PortfolioRiskReport, n: int = 5) -> list[Risk]:
    """Get the top N risks across all projects, sorted by severity."""
    all_risks: list[Risk] = []
    for summary in report.project_summaries:
        all_risks.extend(summary.risks)

    severity_order = {
        RiskSeverity.CRITICAL: 0,
        RiskSeverity.HIGH: 1,
        RiskSeverity.MEDIUM: 2,
        RiskSeverity.LOW: 3,
    }
    all_risks.sort(key=lambda r: severity_order.get(r.severity, 99))
    return all_risks[:n]
