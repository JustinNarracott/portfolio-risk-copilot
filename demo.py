#!/usr/bin/env python3
"""
Demo script — runs the full Portfolio Risk Copilot workflow.

Usage:
    python demo.py

Generates sample artefacts in ./demo-output/
"""

import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.parser import parse_file
from src.risk_engine.engine import analyse_portfolio
from src.scenario.graph import build_dependency_graph
from src.scenario.narrative import generate_narrative
from src.scenario.parser import parse_scenario
from src.scenario.simulator import simulate
from src.artefacts.docx_generator import (
    BrandConfig,
    generate_board_briefing,
    generate_steering_pack,
    generate_project_status_pack,
)
from src.artefacts.pptx_generator import generate_board_slides

REF_DATE = date(2026, 2, 19)
OUTPUT_DIR = Path("demo-output")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("=" * 60)
    print("Portfolio Risk Copilot — Full Demo")
    print("=" * 60)

    # Step 1: Ingest
    print("\n▸ Step 1: Ingesting sample data...")
    projects = parse_file("sample-data/jira-export-sample.csv")
    print(f"  Parsed {len(projects)} projects")

    # Step 2: Risk analysis
    print("\n▸ Step 2: Running risk analysis...")
    report = analyse_portfolio(projects, top_n=5, reference_date=REF_DATE)
    print(f"  Portfolio RAG: {report.portfolio_rag}")
    print(f"  Projects at risk: {report.projects_at_risk}/{len(report.project_summaries)}")
    print(f"  Total risks: {report.total_risks}")

    for summary in report.project_summaries:
        risk_text = f"{summary.risk_count} risks" if summary.risks else "no risks"
        print(f"    {summary.project_name}: {summary.rag_status} ({risk_text})")

    # Step 3: Scenario simulation
    print("\n▸ Step 3: Running scenario simulations...")
    graph = build_dependency_graph(projects)

    scenarios = [
        "cut Beta scope by 30%",
        "increase Gamma budget by 50%",
        "delay Alpha by 1 quarter",
        "remove Delta",
    ]

    for text in scenarios:
        action = parse_scenario(text)
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)
        print(f"  ✓ '{text}' → {narrative.title}")

    # Step 4: Generate artefacts
    print("\n▸ Step 4: Generating briefing artefacts...")
    brand = BrandConfig(company_name="Demo Corp")

    paths = [
        generate_board_briefing(report, brand=brand, output_path=OUTPUT_DIR / "board-briefing.docx"),
        generate_steering_pack(report, brand=brand, output_path=OUTPUT_DIR / "steering-committee-pack.docx"),
        generate_project_status_pack(report, brand=brand, output_path=OUTPUT_DIR / "project-status-pack.docx"),
        generate_board_slides(report, brand=brand, output_path=OUTPUT_DIR / "board-briefing.pptx"),
    ]

    for p in paths:
        print(f"  ✓ {p}")

    print("\n" + "=" * 60)
    print(f"Demo complete! Artefacts saved to ./{OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
