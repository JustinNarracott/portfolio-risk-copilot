"""Generate JSON and XLSX test fixtures from the CSV sample data.

Run once to create test fixture files:
    python tests/fixtures/generate_fixtures.py
"""

import csv
import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample-data"
FIXTURE_DIR = Path(__file__).parent
CSV_FILE = SAMPLE_DIR / "jira-export-sample.csv"


def generate_json_flat():
    """Generate a flat JSON file (list of row objects)."""
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    output = FIXTURE_DIR / "jira-export-flat.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"Created: {output}")


def generate_json_wrapped():
    """Generate a wrapped JSON file (dict with 'issues' key)."""
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    output = FIXTURE_DIR / "jira-export-wrapped.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"issues": rows, "total": len(rows)}, f, indent=2)
    print(f"Created: {output}")


def generate_json_nested():
    """Generate a nested JSON file (projects with embedded tasks)."""
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    projects: dict[str, dict] = {}
    for row in rows:
        pname = row["Project"]
        if pname not in projects:
            projects[pname] = {
                "name": pname,
                "project_status": row["Project Status"],
                "start_date": row["Start Date"],
                "end_date": row["End Date"],
                "budget": row["Budget"],
                "actual_spend": row["Actual Spend"],
                "tasks": [],
            }
        projects[pname]["tasks"].append({
            "task_name": row["Task Name"],
            "task_status": row["Task Status"],
            "priority": row["Priority"],
            "assignee": row["Assignee"],
            "sprint": row["Sprint"],
            "previous_sprints": row["Previous Sprints"],
            "comments": row["Comments"],
        })

    output = FIXTURE_DIR / "jira-export-nested.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"projects": list(projects.values())}, f, indent=2)
    print(f"Created: {output}")


def generate_xlsx():
    """Generate an XLSX file from the CSV sample data."""
    try:
        import openpyxl
    except ImportError:
        print("Skipping XLSX generation — openpyxl not installed")
        return

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Project Export"

    for row in rows:
        ws.append(row)

    output = FIXTURE_DIR / "jira-export-sample.xlsx"
    wb.save(output)
    wb.close()
    print(f"Created: {output}")


if __name__ == "__main__":
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    generate_json_flat()
    generate_json_wrapped()
    generate_json_nested()
    generate_xlsx()
    print("Done!")
