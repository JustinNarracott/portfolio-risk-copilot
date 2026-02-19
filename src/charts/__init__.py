"""
Chart engine — publication-quality portfolio visualisations.

Generates PNG charts for embedding in DOCX and PPTX artefacts.
Uses matplotlib with a custom PMO-friendly colour palette.

All functions return a Path to the generated PNG.
"""

from __future__ import annotations

import math
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np

from src.risk_engine.engine import PortfolioRiskReport, RiskCategory, RiskSeverity
from src.benefits.calculator import PortfolioBenefitReport
from src.investment import PortfolioInvestmentReport, InvestmentAction


# ──────────────────────────────────────────────
# Palette
# ──────────────────────────────────────────────

COLOURS = {
    "primary": "#1B3A5C",
    "accent": "#2E75B6",
    "light_bg": "#F8F9FA",
    "dark_text": "#2C3E50",
    "red": "#E74C3C",
    "amber": "#F39C12",
    "green": "#27AE60",
    "red_light": "#FADBD8",
    "amber_light": "#FEF5E7",
    "green_light": "#D5F5E3",
    "grey": "#BDC3C7",
    "dark_grey": "#7F8C8D",
    "invest": "#27AE60",
    "hold": "#2E75B6",
    "review": "#F39C12",
    "divest": "#E74C3C",
    "critical": "#922B21",
    "high": "#E74C3C",
    "medium": "#F39C12",
    "low": "#3498DB",
}

RAG_COLOURS = {"Red": COLOURS["red"], "Amber": COLOURS["amber"], "Green": COLOURS["green"]}
SEVERITY_COLOURS = {
    RiskSeverity.CRITICAL: COLOURS["critical"],
    RiskSeverity.HIGH: COLOURS["high"],
    RiskSeverity.MEDIUM: COLOURS["medium"],
    RiskSeverity.LOW: COLOURS["low"],
}

_chart_dir: str | None = None

def _get_chart_dir() -> Path:
    global _chart_dir
    if _chart_dir is None:
        _chart_dir = mkdtemp(prefix="pmo_charts_")
    return Path(_chart_dir)


def _save(fig: plt.Figure, name: str, dpi: int = 200) -> Path:
    path = _get_chart_dir() / f"{name}.png"
    fig.savefig(str(path), dpi=dpi, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close(fig)
    return path


def _style_ax(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOURS["grey"])
    ax.spines["bottom"].set_color(COLOURS["grey"])
    ax.tick_params(colors=COLOURS["dark_text"], labelsize=8)


# ──────────────────────────────────────────────
# 1. Portfolio RAG Donut
# ──────────────────────────────────────────────

def chart_rag_donut(report: PortfolioRiskReport) -> Path:
    """Donut chart showing Red/Amber/Green project distribution."""
    counts = {"Red": 0, "Amber": 0, "Green": 0}
    for s in report.project_summaries:
        counts[s.rag_status] = counts.get(s.rag_status, 0) + 1

    labels = [k for k, v in counts.items() if v > 0]
    sizes = [counts[k] for k in labels]
    colors = [RAG_COLOURS[k] for k in labels]

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, colors=colors, autopct=lambda p: f"{int(round(p * sum(sizes) / 100))}",
        startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
        textprops={"fontsize": 14, "fontweight": "bold", "color": "white"},
    )
    # Centre text
    total = sum(sizes)
    ax.text(0, 0.08, str(total), ha="center", va="center", fontsize=28, fontweight="bold", color=COLOURS["primary"])
    ax.text(0, -0.15, "PROJECTS", ha="center", va="center", fontsize=7, fontweight="bold", color=COLOURS["dark_grey"])

    # Legend
    legend_patches = [mpatches.Patch(color=RAG_COLOURS[k], label=f"{k} ({counts[k]})") for k in ["Red", "Amber", "Green"] if counts[k] > 0]
    ax.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8, frameon=False)

    ax.set_aspect("equal")
    fig.patch.set_facecolor("white")
    return _save(fig, "rag_donut")


# ──────────────────────────────────────────────
# 2. Budget vs Spend Bar Chart
# ──────────────────────────────────────────────

def chart_budget_vs_spend(report: PortfolioRiskReport, projects: list | None = None) -> Path:
    """Horizontal bar chart: budget vs actual spend per project."""
    from src.ingestion.parser import Project

    # Build budget/spend lookup from projects
    budget_map: dict[str, tuple[float, float]] = {}
    if projects:
        for p in projects:
            if p.name not in budget_map:
                budget_map[p.name] = (p.budget or 0, p.actual_spend or 0)

    summaries = sorted(report.project_summaries, key=lambda s: -budget_map.get(s.project_name, (0, 0))[0])
    summaries = [s for s in summaries if budget_map.get(s.project_name, (0, 0))[0] > 0][:12]

    if not summaries:
        fig, ax = plt.subplots(figsize=(5, 2))
        ax.text(0.5, 0.5, "No budget data available", ha="center", va="center", fontsize=10, color=COLOURS["dark_grey"])
        ax.set_axis_off()
        return _save(fig, "budget_vs_spend")

    names = [s.project_name[:20] for s in summaries]
    budgets = [budget_map.get(s.project_name, (0, 0))[0] for s in summaries]
    spends = [budget_map.get(s.project_name, (0, 0))[1] for s in summaries]

    y = np.arange(len(names))
    h = 0.35

    fig, ax = plt.subplots(figsize=(6, max(3, len(names) * 0.45)))
    bars_budget = ax.barh(y + h/2, budgets, h, label="Budget", color=COLOURS["accent"], alpha=0.3, edgecolor=COLOURS["accent"])
    bars_spend = ax.barh(y - h/2, spends, h, label="Actual Spend", color=COLOURS["accent"], edgecolor=COLOURS["accent"])

    # Highlight overspend
    for i, (b, s) in enumerate(zip(budgets, spends)):
        if b > 0 and s / b > 0.85:
            bars_spend[i].set_color(COLOURS["red"])
            bars_spend[i].set_edgecolor(COLOURS["red"])

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("£", fontsize=9, color=COLOURS["dark_text"])
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.invert_yaxis()
    _style_ax(ax)
    ax.set_title("Budget vs Actual Spend", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=12)

    # Format x-axis as £k
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"£{x/1000:.0f}k"))

    fig.tight_layout()
    return _save(fig, "budget_vs_spend")


# ──────────────────────────────────────────────
# 3. Risk Heatmap
# ──────────────────────────────────────────────

def chart_risk_heatmap(report: PortfolioRiskReport) -> Path:
    """Risk heatmap: severity × category matrix."""
    categories = [RiskCategory.BLOCKED_WORK, RiskCategory.BURN_RATE, RiskCategory.CHRONIC_CARRYOVER, RiskCategory.DEPENDENCY]
    severities = [RiskSeverity.CRITICAL, RiskSeverity.HIGH, RiskSeverity.MEDIUM, RiskSeverity.LOW]
    cat_labels = ["Blocked\nWork", "Burn\nRate", "Carry-\nOver", "Depend-\nency"]
    sev_labels = ["Critical", "High", "Medium", "Low"]

    matrix = np.zeros((len(severities), len(categories)))
    for s in report.project_summaries:
        for r in s.risks:
            ci = categories.index(r.category) if r.category in categories else -1
            si = severities.index(r.severity) if r.severity in severities else -1
            if ci >= 0 and si >= 0:
                matrix[si][ci] += 1

    fig, ax = plt.subplots(figsize=(4.5, 3))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("pmo", ["#FFFFFF", COLOURS["amber_light"], COLOURS["amber"], COLOURS["red"]])
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0)

    ax.set_xticks(np.arange(len(cat_labels)))
    ax.set_yticks(np.arange(len(sev_labels)))
    ax.set_xticklabels(cat_labels, fontsize=8)
    ax.set_yticklabels(sev_labels, fontsize=8)

    # Annotate cells
    for i in range(len(severities)):
        for j in range(len(categories)):
            val = int(matrix[i][j])
            if val > 0:
                ax.text(j, i, str(val), ha="center", va="center", fontsize=12, fontweight="bold", color=COLOURS["dark_text"])

    ax.set_title("Risk Heatmap", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=10)
    fig.tight_layout()
    return _save(fig, "risk_heatmap")


# ──────────────────────────────────────────────
# 4. Timeline Chart (Gantt-style)
# ──────────────────────────────────────────────

def chart_timeline(report: PortfolioRiskReport, projects: list | None = None) -> Path:
    """Horizontal bar timeline showing project durations coloured by RAG."""
    from datetime import date
    from src.ingestion.parser import Project

    # Build date lookup from projects
    date_map: dict[str, tuple[date | None, date | None]] = {}
    if projects:
        for p in projects:
            if p.name not in date_map and p.start_date and p.end_date:
                date_map[p.name] = (p.start_date, p.end_date)

    entries = []
    for s in report.project_summaries:
        dates = date_map.get(s.project_name)
        if dates and dates[0] and dates[1]:
            entries.append((s, dates[0], dates[1]))
    entries = sorted(entries, key=lambda e: e[1])[:15]

    if not entries:
        # Fallback: empty chart
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No timeline data available", ha="center", va="center", fontsize=10)
        ax.set_axis_off()
        return _save(fig, "timeline")

    fig, ax = plt.subplots(figsize=(7, max(3, len(entries) * 0.4)))
    today = date.today()

    for i, (s, start, end) in enumerate(entries):
        s_ord = start.toordinal()
        e_ord = end.toordinal()
        duration = max(1, e_ord - s_ord)
        colour = RAG_COLOURS.get(s.rag_status, COLOURS["grey"])
        ax.barh(i, duration, left=s_ord, height=0.6, color=colour, alpha=0.85, edgecolor="white", linewidth=0.5)

    # Today line
    ax.axvline(x=today.toordinal(), color=COLOURS["primary"], linestyle="--", linewidth=1, alpha=0.7)
    ax.text(today.toordinal(), len(entries) + 0.3, "Today", fontsize=7, ha="center", color=COLOURS["primary"])

    ax.set_yticks(range(len(entries)))
    ax.set_yticklabels([e[0].project_name[:22] for e in entries], fontsize=7)
    ax.invert_yaxis()
    _style_ax(ax)

    # Format x-axis as months
    from matplotlib.dates import MonthLocator, DateFormatter
    import matplotlib.dates as mdates
    ax.xaxis_date()
    ax.xaxis.set_major_locator(MonthLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b %y"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)

    ax.set_title("Project Timeline", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=10)
    fig.tight_layout()
    return _save(fig, "timeline")


# ──────────────────────────────────────────────
# 5. Benefits Waterfall
# ──────────────────────────────────────────────

def chart_benefits_waterfall(benefit_report: PortfolioBenefitReport) -> Path:
    """Waterfall chart: Expected → Realised → At Risk → Adjusted."""
    expected = benefit_report.total_expected
    realised = benefit_report.total_realised
    at_risk = benefit_report.total_at_risk_value
    adjusted = benefit_report.total_adjusted
    gap = expected - realised - at_risk - adjusted
    if gap < 0:
        gap = 0

    labels = ["Expected\nValue", "Realised\nto Date", "At Risk", "Adjusted\nForecast"]
    values = [expected, realised, at_risk, adjusted]
    colors = [COLOURS["primary"], COLOURS["green"], COLOURS["red"], COLOURS["accent"]]

    fig, ax = plt.subplots(figsize=(5, 3.5))
    bars = ax.bar(labels, values, color=colors, width=0.6, edgecolor="white", linewidth=1.5)

    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + expected * 0.02,
                f"£{val/1000:.0f}k", ha="center", va="bottom", fontsize=9, fontweight="bold", color=COLOURS["dark_text"])

    _style_ax(ax)
    ax.set_ylabel("")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"£{x/1000:.0f}k"))
    ax.set_title("Benefits Value Breakdown", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=12)
    fig.tight_layout()
    return _save(fig, "benefits_waterfall")


# ──────────────────────────────────────────────
# 6. Benefits Drift by Project
# ──────────────────────────────────────────────

def chart_benefits_drift(benefit_report: PortfolioBenefitReport) -> Path:
    """Horizontal bar chart showing drift % per project, coloured by drift RAG."""
    summaries = [s for s in benefit_report.project_summaries if s.total_expected > 0]
    summaries = sorted(summaries, key=lambda s: -s.drift_pct)

    if not summaries:
        fig, ax = plt.subplots(figsize=(5, 2))
        ax.text(0.5, 0.5, "No benefits data", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, "benefits_drift")

    names = [s.project_name[:20] for s in summaries]
    drifts = [s.drift_pct * 100 for s in summaries]
    colors = [RAG_COLOURS.get(s.drift_rag, COLOURS["grey"]) for s in summaries]

    fig, ax = plt.subplots(figsize=(5.5, max(2.5, len(names) * 0.4)))
    bars = ax.barh(names, drifts, color=colors, height=0.6, edgecolor="white", linewidth=0.5)

    # Threshold lines
    ax.axvline(x=15, color=COLOURS["amber"], linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(x=30, color=COLOURS["red"], linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(15, len(names) + 0.3, "15%", fontsize=6, color=COLOURS["amber"], ha="center")
    ax.text(30, len(names) + 0.3, "30%", fontsize=6, color=COLOURS["red"], ha="center")

    # Value labels
    for bar, val in zip(bars, drifts):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}%", ha="left", va="center", fontsize=8, color=COLOURS["dark_text"])

    ax.invert_yaxis()
    ax.set_xlabel("Drift %", fontsize=9, color=COLOURS["dark_text"])
    _style_ax(ax)
    ax.set_title("Benefits Drift by Project", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=10)
    fig.tight_layout()
    return _save(fig, "benefits_drift")


# ──────────────────────────────────────────────
# 7. ROI Bubble Chart (Investment)
# ──────────────────────────────────────────────

def chart_roi_vs_risk(investment_report: PortfolioInvestmentReport) -> Path:
    """Scatter/bubble: X=risk (count), Y=ROI (%), bubble size=budget, colour=action."""
    projects = investment_report.project_investments
    if not projects:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "No investment data", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, "roi_vs_risk")

    action_cols = {
        InvestmentAction.INVEST: COLOURS["invest"],
        InvestmentAction.HOLD: COLOURS["hold"],
        InvestmentAction.REVIEW: COLOURS["review"],
        InvestmentAction.DIVEST: COLOURS["divest"],
    }

    x = [p.risk_count for p in projects]
    y = [p.roi * 100 for p in projects]
    sizes = [max(80, (p.budget / 5000)) for p in projects]  # Scale bubbles
    colors = [action_cols.get(p.action, COLOURS["grey"]) for p in projects]

    fig, ax = plt.subplots(figsize=(6, 4))
    scatter = ax.scatter(x, y, s=sizes, c=colors, alpha=0.7, edgecolors="white", linewidth=1.5)

    # Labels
    for p, xi, yi in zip(projects, x, y):
        short_name = p.project_name.split(" - ")[0][:12] if " - " in p.project_name else p.project_name[:12]
        ax.annotate(short_name, (xi, yi), fontsize=6.5, ha="center", va="bottom",
                    xytext=(0, 6), textcoords="offset points", color=COLOURS["dark_text"])

    # Quadrant lines
    ax.axhline(y=0, color=COLOURS["grey"], linestyle="-", linewidth=0.8, alpha=0.5)
    ax.axvline(x=3, color=COLOURS["grey"], linestyle="--", linewidth=0.5, alpha=0.4)

    # Quadrant labels
    ax.text(0.5, max(y) * 0.85 if max(y) > 0 else 50, "INVEST\n(High ROI, Low Risk)", fontsize=7, color=COLOURS["green"], alpha=0.5, ha="center")
    ax.text(max(x) * 0.75 if max(x) > 3 else 5, max(y) * 0.85 if max(y) > 0 else 50, "REVIEW\n(High ROI, High Risk)", fontsize=7, color=COLOURS["amber"], alpha=0.5, ha="center")
    ax.text(max(x) * 0.75 if max(x) > 3 else 5, min(y) * 0.85 if min(y) < 0 else -20, "DIVEST\n(Low ROI, High Risk)", fontsize=7, color=COLOURS["red"], alpha=0.5, ha="center")

    ax.set_xlabel("Risk Count", fontsize=9, color=COLOURS["dark_text"])
    ax.set_ylabel("ROI %", fontsize=9, color=COLOURS["dark_text"])

    # Legend
    legend_patches = [mpatches.Patch(color=v, label=k.value) for k, v in action_cols.items()]
    ax.legend(handles=legend_patches, fontsize=7, frameon=False, loc="upper right")

    _style_ax(ax)
    ax.set_title("ROI vs Risk (bubble size = budget)", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=12)
    fig.tight_layout()
    return _save(fig, "roi_vs_risk")


# ──────────────────────────────────────────────
# 8. Budget Allocation Treemap (simplified as pie)
# ──────────────────────────────────────────────

def chart_budget_allocation(report: PortfolioRiskReport, projects: list | None = None) -> Path:
    """Pie chart showing budget allocation across projects."""
    # Build budget lookup
    budget_map: dict[str, float] = {}
    if projects:
        for p in projects:
            if p.name not in budget_map:
                budget_map[p.name] = p.budget or 0

    summaries = [(s, budget_map.get(s.project_name, 0)) for s in report.project_summaries]
    summaries = [(s, b) for s, b in summaries if b > 0]
    summaries = sorted(summaries, key=lambda x: -x[1])

    if not summaries:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "No budget data", ha="center", va="center")
        ax.set_axis_off()
        return _save(fig, "budget_allocation")

    # Top 8, bundle rest
    top = summaries[:8]
    rest_budget = sum(b for _, b in summaries[8:])
    names = [s.project_name.split(" - ")[0][:15] if " - " in s.project_name else s.project_name[:15] for s, _ in top]
    values = [b for _, b in top]
    if rest_budget > 0:
        names.append("Other")
        values.append(rest_budget)

    # Colour by RAG
    colors = [RAG_COLOURS.get(s.rag_status, COLOURS["grey"]) for s, _ in top]
    if rest_budget > 0:
        colors.append(COLOURS["grey"])

    fig, ax = plt.subplots(figsize=(4.5, 4))
    wedges, texts, autotexts = ax.pie(
        values, labels=names, colors=colors, autopct=lambda p: f"£{p*sum(values)/100/1000:.0f}k",
        startangle=140, pctdistance=0.78,
        wedgeprops=dict(edgecolor="white", linewidth=1.5),
        textprops={"fontsize": 7, "color": COLOURS["dark_text"]},
    )
    for at in autotexts:
        at.set_fontsize(7)
        at.set_fontweight("bold")

    ax.set_title("Budget Allocation", fontsize=11, fontweight="bold", color=COLOURS["primary"], pad=10)
    fig.tight_layout()
    return _save(fig, "budget_allocation")


# ──────────────────────────────────────────────
# Portfolio Dashboard (composite)
# ──────────────────────────────────────────────

def chart_portfolio_dashboard(
    risk_report: PortfolioRiskReport,
    benefit_report: PortfolioBenefitReport | None = None,
    investment_report: PortfolioInvestmentReport | None = None,
    projects: list | None = None,
) -> Path:
    """Composite 2×2 dashboard: RAG donut, budget chart, risk heatmap, timeline."""
    # Build budget lookup
    budget_map: dict[str, tuple[float, float]] = {}
    if projects:
        for p in projects:
            if p.name not in budget_map:
                budget_map[p.name] = (p.budget or 0, p.actual_spend or 0)

    fig = plt.figure(figsize=(11, 7.5))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    # 1. RAG donut (top-left)
    ax1 = fig.add_subplot(gs[0, 0])
    counts = {"Red": 0, "Amber": 0, "Green": 0}
    for s in risk_report.project_summaries:
        counts[s.rag_status] = counts.get(s.rag_status, 0) + 1
    labels = [k for k, v in counts.items() if v > 0]
    sizes = [counts[k] for k in labels]
    colors = [RAG_COLOURS[k] for k in labels]
    wedges, texts, autotexts = ax1.pie(
        sizes, labels=None, colors=colors, autopct=lambda p: f"{int(round(p * sum(sizes) / 100))}",
        startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
        textprops={"fontsize": 13, "fontweight": "bold", "color": "white"},
    )
    ax1.text(0, 0.08, str(sum(sizes)), ha="center", va="center", fontsize=24, fontweight="bold", color=COLOURS["primary"])
    ax1.text(0, -0.15, "PROJECTS", ha="center", va="center", fontsize=6, fontweight="bold", color=COLOURS["dark_grey"])
    legend_patches = [mpatches.Patch(color=RAG_COLOURS[k], label=f"{k} ({counts[k]})") for k in ["Red", "Amber", "Green"] if counts[k] > 0]
    ax1.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=7, frameon=False)
    ax1.set_title("Portfolio Health", fontsize=10, fontweight="bold", color=COLOURS["primary"], pad=8)

    # 2. Budget vs Spend (top-right)
    ax2 = fig.add_subplot(gs[0, 1])
    summaries_b = sorted(risk_report.project_summaries, key=lambda s: -budget_map.get(s.project_name, (0, 0))[0])
    summaries_b = [s for s in summaries_b if budget_map.get(s.project_name, (0, 0))[0] > 0][:10]
    if summaries_b:
        names = [s.project_name.split(" - ")[0][:14] if " - " in s.project_name else s.project_name[:14] for s in summaries_b]
        budgets = [budget_map.get(s.project_name, (0, 0))[0] for s in summaries_b]
        spends = [budget_map.get(s.project_name, (0, 0))[1] for s in summaries_b]
        y = np.arange(len(names))
        h = 0.35
        ax2.barh(y + h/2, budgets, h, label="Budget", color=COLOURS["accent"], alpha=0.3, edgecolor=COLOURS["accent"])
        spend_bars = ax2.barh(y - h/2, spends, h, label="Spent", color=COLOURS["accent"], edgecolor=COLOURS["accent"])
        for i, (b, s) in enumerate(zip(budgets, spends)):
            if b > 0 and s / b > 0.85:
                spend_bars[i].set_color(COLOURS["red"])
                spend_bars[i].set_edgecolor(COLOURS["red"])
        ax2.set_yticks(y)
        ax2.set_yticklabels(names, fontsize=7)
        ax2.invert_yaxis()
        ax2.legend(fontsize=7, frameon=False, loc="lower right")
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"£{x/1000:.0f}k"))
    else:
        ax2.text(0.5, 0.5, "No budget data", ha="center", va="center", fontsize=9, color=COLOURS["dark_grey"])
        ax2.set_axis_off()
    _style_ax(ax2)
    ax2.tick_params(labelsize=7)
    ax2.set_title("Budget vs Spend", fontsize=10, fontweight="bold", color=COLOURS["primary"], pad=8)

    # 3. Risk Heatmap (bottom-left)
    ax3 = fig.add_subplot(gs[1, 0])
    categories = [RiskCategory.BLOCKED_WORK, RiskCategory.BURN_RATE, RiskCategory.CHRONIC_CARRYOVER, RiskCategory.DEPENDENCY]
    severities = [RiskSeverity.CRITICAL, RiskSeverity.HIGH, RiskSeverity.MEDIUM, RiskSeverity.LOW]
    matrix = np.zeros((len(severities), len(categories)))
    for s in risk_report.project_summaries:
        for r in s.risks:
            ci = categories.index(r.category) if r.category in categories else -1
            si = severities.index(r.severity) if r.severity in severities else -1
            if ci >= 0 and si >= 0:
                matrix[si][ci] += 1
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("pmo", ["#FFFFFF", COLOURS["amber_light"], COLOURS["amber"], COLOURS["red"]])
    ax3.imshow(matrix, cmap=cmap, aspect="auto", vmin=0)
    ax3.set_xticks(np.arange(4))
    ax3.set_yticks(np.arange(4))
    ax3.set_xticklabels(["Blocked", "Burn Rate", "Carry-Over", "Dependency"], fontsize=7)
    ax3.set_yticklabels(["Critical", "High", "Medium", "Low"], fontsize=7)
    for i in range(4):
        for j in range(4):
            val = int(matrix[i][j])
            if val > 0:
                ax3.text(j, i, str(val), ha="center", va="center", fontsize=11, fontweight="bold",
                         color=COLOURS["dark_text"])
    ax3.set_title("Risk Heatmap", fontsize=10, fontweight="bold", color=COLOURS["primary"], pad=8)

    # 4. Timeline (bottom-right) or Benefits drift
    ax4 = fig.add_subplot(gs[1, 1])
    if benefit_report and any(s.total_expected > 0 for s in benefit_report.project_summaries):
        # Benefits drift bars
        bs = [s for s in benefit_report.project_summaries if s.total_expected > 0]
        bs = sorted(bs, key=lambda s: -s.drift_pct)[:10]
        bnames = [s.project_name.split(" - ")[0][:14] if " - " in s.project_name else s.project_name[:14] for s in bs]
        drifts = [s.drift_pct * 100 for s in bs]
        bcolors = [RAG_COLOURS.get(s.drift_rag, COLOURS["grey"]) for s in bs]
        ax4.barh(bnames, drifts, color=bcolors, height=0.6, edgecolor="white")
        ax4.axvline(x=15, color=COLOURS["amber"], linestyle="--", linewidth=0.7, alpha=0.5)
        ax4.axvline(x=30, color=COLOURS["red"], linestyle="--", linewidth=0.7, alpha=0.5)
        ax4.invert_yaxis()
        ax4.set_xlabel("Drift %", fontsize=7, color=COLOURS["dark_text"])
        _style_ax(ax4)
        ax4.tick_params(labelsize=7)
        ax4.set_title("Benefits Drift", fontsize=10, fontweight="bold", color=COLOURS["primary"], pad=8)
    else:
        # Timeline fallback using projects
        from datetime import date as dt_date
        date_map: dict[str, tuple] = {}
        if projects:
            for p in projects:
                if p.name not in date_map and p.start_date and p.end_date:
                    date_map[p.name] = (p.start_date, p.end_date)
        tl_entries = []
        for s in risk_report.project_summaries:
            dates = date_map.get(s.project_name)
            if dates:
                tl_entries.append((s, dates[0], dates[1]))
        tl_entries = sorted(tl_entries, key=lambda e: e[1])[:10]
        if tl_entries:
            for i, (s, start, end) in enumerate(tl_entries):
                ax4.barh(i, max(1, end.toordinal() - start.toordinal()), left=start.toordinal(),
                         height=0.5, color=RAG_COLOURS.get(s.rag_status, COLOURS["grey"]), edgecolor="white")
            ax4.set_yticks(range(len(tl_entries)))
            ax4.set_yticklabels([e[0].project_name[:14] for e in tl_entries], fontsize=6)
            ax4.invert_yaxis()
            ax4.xaxis_date()
            from matplotlib.dates import MonthLocator, DateFormatter
            ax4.xaxis.set_major_locator(MonthLocator())
            ax4.xaxis.set_major_formatter(DateFormatter("%b"))
            plt.setp(ax4.get_xticklabels(), rotation=45, ha="right", fontsize=6)
        _style_ax(ax4)
        ax4.set_title("Project Timeline", fontsize=10, fontweight="bold", color=COLOURS["primary"], pad=8)

    fig.suptitle("Portfolio Dashboard", fontsize=14, fontweight="bold", color=COLOURS["primary"], y=0.98)
    return _save(fig, "portfolio_dashboard", dpi=220)


def chart_portfolio_dashboard_compact(
    risk_report: PortfolioRiskReport,
    benefit_report: PortfolioBenefitReport | None = None,
    investment_report: PortfolioInvestmentReport | None = None,
    projects: list | None = None,
) -> Path:
    """Compact 2×2 dashboard for tight page fits (smaller figure)."""
    budget_map: dict[str, tuple[float, float]] = {}
    if projects:
        for p in projects:
            if p.name not in budget_map:
                budget_map[p.name] = (p.budget or 0, p.actual_spend or 0)

    fig = plt.figure(figsize=(9, 5.5))
    gs = GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

    # 1. RAG donut (top-left)
    ax1 = fig.add_subplot(gs[0, 0])
    counts = {"Red": 0, "Amber": 0, "Green": 0}
    for s in risk_report.project_summaries:
        counts[s.rag_status] = counts.get(s.rag_status, 0) + 1
    labels = [k for k, v in counts.items() if v > 0]
    sizes = [counts[k] for k in labels]
    colors = [RAG_COLOURS[k] for k in labels]
    wedges, texts, autotexts = ax1.pie(
        sizes, labels=None, colors=colors, autopct=lambda p: f"{int(round(p * sum(sizes) / 100))}",
        startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.35, edgecolor="white", linewidth=2),
        textprops={"fontsize": 11, "fontweight": "bold", "color": "white"},
    )
    ax1.text(0, 0.08, str(sum(sizes)), ha="center", va="center", fontsize=20, fontweight="bold", color=COLOURS["primary"])
    ax1.text(0, -0.15, "PROJECTS", ha="center", va="center", fontsize=6, fontweight="bold", color=COLOURS["dark_grey"])
    legend_patches = [mpatches.Patch(color=RAG_COLOURS[k], label=f"{k} ({counts[k]})") for k in ["Red", "Amber", "Green"] if counts[k] > 0]
    ax1.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=6, frameon=False)
    ax1.set_title("Portfolio Health", fontsize=9, fontweight="bold", color=COLOURS["primary"], pad=6)

    # 2. Budget vs Spend (top-right)
    ax2 = fig.add_subplot(gs[0, 1])
    summaries_b = sorted(risk_report.project_summaries, key=lambda s: -budget_map.get(s.project_name, (0, 0))[0])
    summaries_b = [s for s in summaries_b if budget_map.get(s.project_name, (0, 0))[0] > 0][:8]
    if summaries_b:
        bnames = [s.project_name.split(" - ")[0][:12] if " - " in s.project_name else s.project_name[:12] for s in summaries_b]
        budgets = [budget_map.get(s.project_name, (0, 0))[0] for s in summaries_b]
        spends = [budget_map.get(s.project_name, (0, 0))[1] for s in summaries_b]
        y = np.arange(len(bnames))
        h = 0.35
        ax2.barh(y + h/2, budgets, h, label="Budget", color=COLOURS["accent"], alpha=0.3, edgecolor=COLOURS["accent"])
        spend_bars = ax2.barh(y - h/2, spends, h, label="Spent", color=COLOURS["accent"], edgecolor=COLOURS["accent"])
        for i, (b, s) in enumerate(zip(budgets, spends)):
            if b > 0 and s / b > 0.85:
                spend_bars[i].set_color(COLOURS["red"])
                spend_bars[i].set_edgecolor(COLOURS["red"])
        ax2.set_yticks(y)
        ax2.set_yticklabels(bnames, fontsize=6)
        ax2.invert_yaxis()
        ax2.legend(fontsize=6, frameon=False, loc="lower right")
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"£{x/1000:.0f}k"))
    _style_ax(ax2)
    ax2.tick_params(labelsize=6)
    ax2.set_title("Budget vs Spend", fontsize=9, fontweight="bold", color=COLOURS["primary"], pad=6)

    # 3. Risk Heatmap (bottom-left)
    ax3 = fig.add_subplot(gs[1, 0])
    categories = [RiskCategory.BLOCKED_WORK, RiskCategory.BURN_RATE, RiskCategory.CHRONIC_CARRYOVER, RiskCategory.DEPENDENCY]
    severities = [RiskSeverity.CRITICAL, RiskSeverity.HIGH, RiskSeverity.MEDIUM, RiskSeverity.LOW]
    matrix = np.zeros((len(severities), len(categories)))
    for s in risk_report.project_summaries:
        for r in s.risks:
            ci = categories.index(r.category) if r.category in categories else -1
            si = severities.index(r.severity) if r.severity in severities else -1
            if ci >= 0 and si >= 0:
                matrix[si][ci] += 1
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("pmo", ["#FFFFFF", COLOURS["amber_light"], COLOURS["amber"], COLOURS["red"]])
    ax3.imshow(matrix, cmap=cmap, aspect="auto", vmin=0)
    ax3.set_xticks(np.arange(4))
    ax3.set_yticks(np.arange(4))
    ax3.set_xticklabels(["Blocked", "Burn Rate", "Carry-Over", "Dependency"], fontsize=6)
    ax3.set_yticklabels(["Critical", "High", "Medium", "Low"], fontsize=6)
    for i in range(4):
        for j in range(4):
            val = int(matrix[i][j])
            if val > 0:
                ax3.text(j, i, str(val), ha="center", va="center", fontsize=10, fontweight="bold",
                         color=COLOURS["dark_text"])
    ax3.set_title("Risk Heatmap", fontsize=9, fontweight="bold", color=COLOURS["primary"], pad=6)

    # 4. Benefits drift (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    if benefit_report and any(s.total_expected > 0 for s in benefit_report.project_summaries):
        bs = [s for s in benefit_report.project_summaries if s.total_expected > 0]
        bs = sorted(bs, key=lambda s: -s.drift_pct)[:8]
        bnames2 = [s.project_name.split(" - ")[0][:12] if " - " in s.project_name else s.project_name[:12] for s in bs]
        drifts = [s.drift_pct * 100 for s in bs]
        bcolors = [RAG_COLOURS.get(s.drift_rag, COLOURS["grey"]) for s in bs]
        ax4.barh(bnames2, drifts, color=bcolors, height=0.5, edgecolor="white")
        ax4.axvline(x=15, color=COLOURS["amber"], linestyle="--", linewidth=0.6, alpha=0.5)
        ax4.axvline(x=30, color=COLOURS["red"], linestyle="--", linewidth=0.6, alpha=0.5)
        ax4.invert_yaxis()
        ax4.set_xlabel("Drift %", fontsize=6, color=COLOURS["dark_text"])
        ax4.set_title("Benefits Drift", fontsize=9, fontweight="bold", color=COLOURS["primary"], pad=6)
    else:
        ax4.text(0.5, 0.5, "No benefits data", ha="center", va="center", fontsize=8, color=COLOURS["dark_grey"])
        ax4.set_axis_off()
    _style_ax(ax4)
    ax4.tick_params(labelsize=6)

    fig.suptitle("", fontsize=1)  # No title — already in DOCX header
    return _save(fig, "portfolio_dashboard_compact", dpi=200)
