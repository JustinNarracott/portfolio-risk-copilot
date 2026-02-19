"""
Portfolio Risk Copilot — CLI entry point.

Provides the unified command interface for Cowork plugin slash commands.
Manages session state between commands.

Sprint 4 — Week 10 deliverable.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from src.ingestion.parser import parse_file, Project
from src.ingestion.validators import validate_file
from src.risk_engine.engine import PortfolioRiskReport, analyse_portfolio
from src.scenario.graph import build_dependency_graph, DependencyGraph
from src.scenario.narrative import generate_narrative
from src.scenario.parser import parse_scenario, ParseError
from src.scenario.simulator import simulate
from src.artefacts.docx_generator import (
    BrandConfig,
    generate_board_briefing,
    generate_steering_pack,
    generate_project_status_pack,
)
from src.artefacts.pptx_generator import generate_board_slides
from src.benefits.parser import parse_benefits, Benefit
from src.benefits.calculator import analyse_benefits, PortfolioBenefitReport
from src.benefits.artefacts import generate_benefits_report
from src.investment import analyse_investments, PortfolioInvestmentReport
from src.investment.artefacts import generate_investment_report
from src.decisions import (
    DecisionLog, decision_from_scenario, decisions_from_risk_report,
    decisions_from_investment, export_decision_log,
)

__version__ = "1.1.0"


class Session:
    """In-memory session state between commands."""

    def __init__(self) -> None:
        self.projects: list[Project] = []
        self.report: PortfolioRiskReport | None = None
        self.benefit_report: PortfolioBenefitReport | None = None
        self.investment_report: PortfolioInvestmentReport | None = None
        self.decision_log: DecisionLog = DecisionLog()
        self.benefits: list[Benefit] = []
        self.graph: DependencyGraph | None = None
        self.brand: BrandConfig = BrandConfig()
        self.reference_date: date = date.today()
        self.output_dir: Path = Path(".")

    @property
    def is_loaded(self) -> bool:
        return len(self.projects) > 0


# Global session (for CLI use)
_session = Session()


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pmo-copilot",
        description="Portfolio Risk Copilot — AI-powered PMO decision support",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # pmo-ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest project data from folder")
    ingest_parser.add_argument("folder", type=str, help="Path to folder containing CSV/JSON/Excel files")
    ingest_parser.add_argument("--output-dir", type=str, default=".", help="Output directory for generated files")

    # pmo-risks
    risks_parser = subparsers.add_parser("risks", help="Generate top 5 risks per project")
    risks_parser.add_argument("--top", type=int, default=5, help="Number of top risks per project")
    risks_parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")

    # pmo-scenario
    scenario_parser = subparsers.add_parser("scenario", help="Run what-if scenario")
    scenario_parser.add_argument("description", type=str, help="Scenario description in natural language")

    # pmo-brief
    brief_parser = subparsers.add_parser("brief", help="Generate stakeholder briefing")
    brief_parser.add_argument("type", choices=["board", "steering", "project", "benefits", "investment", "decisions", "all"], help="Briefing type")
    brief_parser.add_argument("--logo", type=str, help="Path to logo image (PNG/JPG)")
    brief_parser.add_argument("--colour", type=str, help="Primary brand colour (hex, e.g. 1F4E79)")
    brief_parser.add_argument("--output-dir", type=str, help="Output directory")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "ingest":
            return cmd_ingest(args)
        elif args.command == "risks":
            return cmd_risks(args)
        elif args.command == "scenario":
            return cmd_scenario(args)
        elif args.command == "brief":
            return cmd_brief(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


# ──────────────────────────────────────────────
# Command implementations
# ──────────────────────────────────────────────


def cmd_ingest(args) -> int:
    """Scan folder for data files, validate, parse, and run risk analysis."""
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a directory.", file=sys.stderr)
        return 1

    # Find supported files
    extensions = {".csv", ".json", ".xlsx"}
    files = [f for f in folder.iterdir() if f.suffix.lower() in extensions]

    if not files:
        print(f"No CSV, JSON, or Excel files found in '{folder}'.", file=sys.stderr)
        return 1

    print(f"Found {len(files)} data file(s) in '{folder}':")

    all_projects: list[Project] = []
    for f in sorted(files):
        # Validate
        result = validate_file(f)
        if not result.valid:
            print(f"  ⚠ {f.name}: Skipped ({'; '.join(result.errors[:2])})")
            continue

        # Parse
        projects = parse_file(f)
        all_projects.extend(projects)
        print(f"  ✓ {f.name}: {len(projects)} projects, {result.row_count} rows")

    if not all_projects:
        print("No valid project data found.", file=sys.stderr)
        return 1

    # Deduplicate by project name (keep the one with most tasks)
    project_map: dict[str, Project] = {}
    for p in all_projects:
        if p.name not in project_map or len(p.tasks) > len(project_map[p.name].tasks):
            project_map[p.name] = p
    deduplicated = list(project_map.values())

    # Store in session
    _session.projects = deduplicated
    _session.graph = build_dependency_graph(deduplicated)
    _session.report = analyse_portfolio(deduplicated, top_n=5, reference_date=_session.reference_date)

    # Attempt to parse benefit files (files that failed project parsing may be benefit trackers)
    _session.benefits = []
    for f in sorted(files):
        try:
            benefits = parse_benefits(f)
            # Quality gate: only accept as benefit file if ≥1 benefit has expected_value > 0
            if benefits and any(b.expected_value > 0 for b in benefits):
                # Further gate: must have recognisable benefit columns (not just project data)
                has_benefit_value = sum(1 for b in benefits if b.expected_value > 0)
                if has_benefit_value / len(benefits) >= 0.3:  # At least 30% have values
                    _session.benefits.extend(benefits)
        except Exception:
            pass

    # Deduplicate benefits by project + name
    seen_bens: set[str] = set()
    unique_benefits: list[Benefit] = []
    for b in _session.benefits:
        key = f"{b.project_name}|{b.name}"
        if key not in seen_bens:
            seen_bens.add(key)
            unique_benefits.append(b)
    _session.benefits = unique_benefits

    # Run benefits analysis if we have benefit data
    if _session.benefits:
        _session.benefit_report = analyse_benefits(
            _session.benefits, _session.report, _session.reference_date
        )

    # Run investment analysis
    _session.investment_report = analyse_investments(
        deduplicated, _session.report, _session.benefit_report
    )

    # Populate decision log from analysis
    _session.decision_log = DecisionLog()
    decisions_from_risk_report(_session.report, _session.decision_log, _session.reference_date)
    if _session.investment_report:
        decisions_from_investment(_session.investment_report, _session.decision_log, _session.reference_date)

    if hasattr(args, "output_dir") and args.output_dir:
        _session.output_dir = Path(args.output_dir)

    print(f"\n✓ Ingested {len(deduplicated)} projects.")
    print(f"  Portfolio RAG: {_session.report.portfolio_rag}")
    print(f"  Projects at risk: {_session.report.projects_at_risk}/{len(deduplicated)}")
    print(f"  Total risks identified: {_session.report.total_risks}")
    if _session.benefits:
        print(f"  Benefits tracked: {len(_session.benefits)} across {len({b.project_name for b in _session.benefits})} projects")
        if _session.benefit_report:
            print(f"  Portfolio benefits drift: {_session.benefit_report.portfolio_drift_pct:.0%} ({_session.benefit_report.portfolio_drift_rag})")
    print(f"\nRun 'pmo-copilot risks' for details or 'pmo-copilot brief <type>' to generate artefacts.")

    return 0


def cmd_risks(args) -> int:
    """Display top risks per project."""
    if not _session.is_loaded:
        print("No data loaded. Run 'pmo-copilot ingest <folder>' first.", file=sys.stderr)
        return 1

    report = _session.report
    if report is None:
        return 1

    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"Portfolio Risk Report — {date.today().isoformat()}")
    print(f"Overall RAG: {report.portfolio_rag}")
    print(f"Projects: {len(report.project_summaries)} | At Risk: {report.projects_at_risk} | Total Risks: {report.total_risks}")
    print("=" * 70)

    for summary in report.project_summaries:
        print(f"\n{summary.project_name} [{summary.rag_status}] — {summary.project_status}")
        if summary.risks:
            for i, risk in enumerate(summary.risks[:args.top], 1):
                print(f"  {i}. [{risk.severity.value}] {risk.title}")
                print(f"     {risk.explanation[:120]}...")
        else:
            print("  No significant risks.")

    return 0


def cmd_scenario(args) -> int:
    """Run a what-if scenario simulation."""
    if not _session.is_loaded:
        print("No data loaded. Run 'pmo-copilot ingest <folder>' first.", file=sys.stderr)
        return 1

    try:
        action = parse_scenario(args.description)
    except ParseError as e:
        print(f"Could not parse scenario: {e}", file=sys.stderr)
        return 1

    result = simulate(action, _session.projects, _session.graph, _session.reference_date)
    narrative = generate_narrative(result)

    # Add to decision log
    decision_from_scenario(result, _session.decision_log, _session.reference_date)

    print(narrative.full_text)

    if result.warnings:
        print("\n⚠ Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    return 0


def cmd_brief(args) -> int:
    """Generate stakeholder briefing documents."""
    if not _session.is_loaded:
        print("No data loaded. Run 'pmo-copilot ingest <folder>' first.", file=sys.stderr)
        return 1

    report = _session.report
    brand = _session.brand
    output_dir = Path(args.output_dir) if args.output_dir else _session.output_dir

    # Apply CLI brand overrides
    if args.logo:
        brand.logo_path = args.logo
    if args.colour:
        brand.primary_colour = args.colour

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    if args.type in ("board", "all"):
        p = generate_board_briefing(
            report, brand=brand, output_path=output_dir / "board-briefing.docx",
            benefit_report=_session.benefit_report,
            investment_report=_session.investment_report,
            projects=_session.projects,
        )
        generated.append(p)
        p2 = generate_board_slides(report, brand=brand, output_path=output_dir / "board-briefing.pptx")
        generated.append(p2)

    if args.type in ("steering", "all"):
        p = generate_steering_pack(
            report, brand=brand, output_path=output_dir / "steering-committee-pack.docx",
            benefit_report=_session.benefit_report,
            investment_report=_session.investment_report,
            projects=_session.projects,
        )
        generated.append(p)

    if args.type in ("project", "all"):
        p = generate_project_status_pack(report, brand=brand, output_path=output_dir / "project-status-pack.docx")
        generated.append(p)

    if args.type in ("benefits", "all"):
        if _session.benefit_report:
            p = generate_benefits_report(
                _session.benefit_report, brand=brand,
                output_path=output_dir / "benefits-report.docx",
            )
            generated.append(p)
        elif args.type == "benefits":
            print("No benefit data loaded. Ensure benefit tracker CSV is in the ingested folder.")
            return 1

    if args.type in ("investment", "all"):
        if _session.investment_report:
            p = generate_investment_report(
                _session.investment_report, brand=brand,
                output_path=output_dir / "investment-summary.docx",
            )
            generated.append(p)
        elif args.type == "investment":
            print("No investment data available. Run 'pmo-copilot ingest' first.")
            return 1

    if args.type in ("decisions", "all"):
        if _session.decision_log.decisions:
            p = export_decision_log(
                _session.decision_log, brand=brand,
                output_path=output_dir / "decision-log.docx",
            )
            generated.append(p)

    print(f"✓ Generated {len(generated)} artefact(s):")
    for g in generated:
        print(f"  → {g}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
