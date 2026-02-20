#!/usr/bin/env python3
"""
Demo script — runs the full Portfolio Risk Copilot workflow.

Usage:
    python demo.py

Generates all 8 artefact types in ./demo-output/ using sample data.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.cli import main as cli_main, _session

OUTPUT_DIR = Path("demo-output")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("=" * 60)
    print("Portfolio Risk Copilot — Full Demo")
    print("=" * 60)

    # Set reference date for consistent risk/date calculations
    _session.reference_date = date.today()

    # Step 1: Ingest all sample data
    print("\n▸ Step 1: Ingesting sample data...")
    cli_main(["ingest", "./sample-data"])

    # Step 2: Show risks
    print("\n▸ Step 2: Portfolio risks...")
    cli_main(["risks"])

    # Step 3: Run a sample scenario
    print("\n▸ Step 3: Scenario simulation...")
    cli_main(["scenario", "delay Alpha by 3 months"])

    # Step 4: Generate all artefacts
    print("\n▸ Step 4: Generating all briefing artefacts...")
    cli_main(["brief", "all", "--output-dir", str(OUTPUT_DIR)])

    print("\n" + "=" * 60)
    print(f"Demo complete! Artefacts saved to ./{OUTPUT_DIR}/")
    print("Open the .docx files in Word to see charts and formatting.")
    print("=" * 60)


if __name__ == "__main__":
    main()
