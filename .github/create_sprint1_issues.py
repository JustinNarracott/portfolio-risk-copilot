#!/usr/bin/env python3
"""
Create Sprint 1 GitHub Issues for portfolio-risk-copilot.

Usage:
    Set GITHUB_PAT and GITHUB_REPO environment variables, then run:
    python create_sprint1_issues.py

    Or create them manually from the issue definitions below.
"""

import json
import os
import sys
import urllib.request

ISSUES = [
    # ── WEEK 1: File Handler & Data Parser ──
    {
        "title": "[Sprint 1 / Week 1] Set up GitHub repo and dev environment",
        "body": """## Description
Set up the project foundation: GitHub repo structure, Python virtual environment, 
dependencies, and CI configuration.

## Tasks
- [x] Create GitHub repo (portfolio-risk-copilot, private, MIT licence)
- [ ] Set up Python 3.11+ virtual environment
- [ ] Install core dependencies (pandas, openpyxl, python-docx, python-pptx, pytest)
- [ ] Verify `pytest` runs with smoke tests passing
- [ ] Set up `.gitignore`, `pyproject.toml`, `LICENSE`

## Acceptance Criteria
- [ ] `pip install -e ".[dev]"` completes without errors
- [ ] `pytest` runs and passes smoke tests
- [ ] Project structure matches README

## Labels
`sprint-1`, `week-1`, `setup`
""",
        "labels": ["sprint-1", "week-1", "setup"],
    },
    {
        "title": "[Sprint 1 / Week 1] Implement CSV parser for Jira exports",
        "body": """## Description
Parse Jira CSV exports into structured Project and Task objects. Handle the standard 
Jira export format with columns: Project, Status, Start Date, End Date, Budget, 
Actual Spend, Task Name, Task Status, Priority, Assignee, Sprint, Previous Sprints, Comments.

## Tasks
- [ ] Implement `_parse_csv()` in `src/ingestion/parser.py`
- [ ] Group rows by project name into `Project` objects
- [ ] Parse dates in common formats (YYYY-MM-DD, DD/MM/YYYY)
- [ ] Parse `Previous Sprints` field (semicolon-separated) into list
- [ ] Handle missing/empty columns gracefully
- [ ] Write unit tests covering: valid CSV, missing columns, empty file, malformed dates

## Acceptance Criteria
- [ ] Parser handles `sample-data/jira-export-sample.csv` without errors
- [ ] Returns 6 Project objects with correct task counts
- [ ] Unit tests pass with 95%+ coverage for parser module

## Test Data
Use `sample-data/jira-export-sample.csv` (50 tasks, 6 projects)

## Labels
`sprint-1`, `week-1`, `parser`
""",
        "labels": ["sprint-1", "week-1", "parser"],
    },
    {
        "title": "[Sprint 1 / Week 1] Implement JSON and Excel parsers",
        "body": """## Description
Extend the parser to handle JSON and Excel (XLSX) exports alongside CSV.

## Tasks
- [ ] Implement `_parse_json()` in `src/ingestion/parser.py`
- [ ] Implement `_parse_xlsx()` using openpyxl
- [ ] Implement `parse_file()` dispatch based on file extension
- [ ] Create sample JSON and XLSX test fixtures from the CSV sample data
- [ ] Write unit tests for JSON and XLSX parsing

## Acceptance Criteria
- [ ] `parse_file()` correctly routes to CSV, JSON, or XLSX parser
- [ ] All three formats produce identical Project/Task output for same data
- [ ] Unsupported file extensions raise `ValueError`

## Labels
`sprint-1`, `week-1`, `parser`
""",
        "labels": ["sprint-1", "week-1", "parser"],
    },
    {
        "title": "[Sprint 1 / Week 1] Implement file format validation",
        "body": """## Description
Validate uploaded files before parsing: check file extension, required columns, 
and basic data integrity.

## Tasks
- [ ] Implement `validate_file()` in `src/ingestion/validators.py`
- [ ] Check file exists and has supported extension
- [ ] Check required columns present (project, task_name, task_status)
- [ ] Return warnings for missing optional columns
- [ ] Write unit tests for valid files, missing columns, wrong extensions, empty files

## Acceptance Criteria
- [ ] Validation returns clear error messages for malformed files
- [ ] Valid files pass with optional column warnings
- [ ] Tests cover all edge cases

## Labels
`sprint-1`, `week-1`, `validation`
""",
        "labels": ["sprint-1", "week-1", "validation"],
    },

    # ── WEEK 2: Risk Engine (Blocked Work, Carry-Over) ──
    {
        "title": "[Sprint 1 / Week 2] Implement blocked work detection",
        "body": """## Description
Detect tasks that are blocked based on status fields and blocker keywords in comments.

## Tasks
- [ ] Implement `detect_blocked_work()` in `src/risk_engine/blocked.py`
- [ ] Scan task status for: blocked, waiting, on hold
- [ ] Scan task comments for keywords: "blocked by", "waiting for", "on hold pending"
- [ ] Flag tasks with Critical/High priority as higher severity
- [ ] Generate plain-English risk explanation per finding
- [ ] Write unit tests with sample data (Alpha and Epsilon have known blocked tasks)

## Acceptance Criteria
- [ ] Detects Alpha's payment gateway (blocked 3+ weeks, critical priority)
- [ ] Detects Epsilon's staff training (on hold)
- [ ] Explanations are plain-English and actionable
- [ ] Tests cover: status-based detection, keyword-based detection, priority weighting

## Expected Results (from sample data)
- Alpha: "Implement payment gateway" — Blocked status, critical priority, 3+ weeks
- Alpha: "Build user authentication API" — Blocker keyword in comments
- Epsilon: "Staff training rollout" — On Hold status

## Labels
`sprint-1`, `week-2`, `risk-engine`
""",
        "labels": ["sprint-1", "week-2", "risk-engine"],
    },
    {
        "title": "[Sprint 1 / Week 2] Implement chronic carry-over detection",
        "body": """## Description
Detect tasks that have been moved across 3+ sprints, indicating chronic delivery failure.

## Tasks
- [ ] Implement `detect_carryover()` in `src/risk_engine/carryover.py`
- [ ] Parse `previous_sprints` field to count sprint transitions
- [ ] Flag tasks carried over 3+ sprints (configurable threshold)
- [ ] Higher severity for Critical/High priority carry-over tasks
- [ ] Generate plain-English explanation including sprint history
- [ ] Write unit tests with sample data (Gamma and Epsilon have known carry-over)

## Acceptance Criteria
- [ ] Detects Gamma's core platform migration (4 sprint carry-over)
- [ ] Detects Epsilon's regulatory audit (2 sprint carry-over — below threshold, should NOT flag)
- [ ] Correctly counts sprints from previous_sprints field

## Expected Results (from sample data)
- Gamma: "Core platform migration" — 4 sprints (Sprint 4, 5, 6, 7 → now Sprint 8)
- Gamma: "Data migration pipeline" — 2 sprints (Sprint 6, 7 → Sprint 8) — below threshold

## Labels
`sprint-1`, `week-2`, `risk-engine`
""",
        "labels": ["sprint-1", "week-2", "risk-engine"],
    },

    # ── WEEK 3: Risk Engine (Burn Rate, Dependencies) & Integration ──
    {
        "title": "[Sprint 1 / Week 3] Implement burn rate alert detection",
        "body": """## Description
Calculate budget consumption vs time elapsed and flag dangerous patterns.

## Tasks
- [ ] Implement `detect_burn_rate()` in `src/risk_engine/burnrate.py`
- [ ] Calculate % budget spent: actual_spend / budget
- [ ] Calculate % time elapsed: (reference_date - start_date) / (end_date - start_date)
- [ ] Calculate % time remaining: 1 - time_elapsed
- [ ] Flag if spend >90% AND time remaining >10%
- [ ] Accept configurable reference_date (default: today)
- [ ] Write unit tests with sample data (Gamma and Epsilon have known burn rate issues)

## Acceptance Criteria
- [ ] Detects Gamma: 92.5% budget spent (185k/200k) with ~2 months remaining
- [ ] Detects Epsilon: 96.7% budget spent (58k/60k) with ~1 month remaining
- [ ] Does NOT flag Zeta: 12.5% spent (15k/120k) — healthy burn rate
- [ ] Reference date parameter works correctly

## Labels
`sprint-1`, `week-3`, `risk-engine`
""",
        "labels": ["sprint-1", "week-3", "risk-engine"],
    },
    {
        "title": "[Sprint 1 / Week 3] Implement dependency keyword scanner",
        "body": """## Description
Scan task comments for dependency indicators and flag unresolved dependency chains.

## Tasks
- [ ] Implement `detect_dependencies()` in `src/risk_engine/dependencies.py`
- [ ] Scan comments for keywords: "depends on", "blocked by", "waiting for", "prerequisite", "requires"
- [ ] Extract the dependency target where possible (e.g., "depends on API completion" → "API completion")
- [ ] Flag tasks with multiple dependencies as higher severity
- [ ] Generate plain-English explanation of dependency chain
- [ ] Write unit tests with sample data

## Acceptance Criteria
- [ ] Detects Alpha's dependency chains (frontend → API, tests → API + payment gateway)
- [ ] Detects cross-project keywords where present
- [ ] Explanations name the specific dependency

## Labels
`sprint-1`, `week-3`, `risk-engine`
""",
        "labels": ["sprint-1", "week-3", "risk-engine"],
    },
    {
        "title": "[Sprint 1 / Week 3] Implement risk aggregation and ranking engine",
        "body": """## Description
Combine all four risk detectors and produce a ranked top-N risk list per project.

## Tasks
- [ ] Implement `analyse_portfolio()` in `src/risk_engine/engine.py`
- [ ] Call all four detectors: blocked, carryover, burnrate, dependencies
- [ ] Aggregate risks per project
- [ ] Rank by severity (Critical > High > Medium > Low)
- [ ] Return top N risks per project (default: 5)
- [ ] Output as structured dict[str, list[Risk]]

## Acceptance Criteria
- [ ] Top risks match expected results from sample-data/README.md
- [ ] Gamma and Epsilon appear as highest-risk projects
- [ ] Delta and Zeta appear as lowest-risk projects
- [ ] All risks have plain-English explanations

## Labels
`sprint-1`, `week-3`, `risk-engine`
""",
        "labels": ["sprint-1", "week-3", "risk-engine"],
    },
    {
        "title": "[Sprint 1 / Week 3] End-to-end integration test: CSV upload → risk output",
        "body": """## Description
Verify the complete Sprint 1 pipeline: upload CSV → parse → analyse → output ranked risks.

## Tasks
- [ ] Write integration test in `tests/integration/test_sprint1_e2e.py`
- [ ] Load `sample-data/jira-export-sample.csv`
- [ ] Parse into Project objects
- [ ] Run `analyse_portfolio()` 
- [ ] Verify top risks match expected output
- [ ] Verify execution completes in <30 seconds
- [ ] Test with 100, 300, and 500 row datasets

## Acceptance Criteria
- [ ] End-to-end test passes: upload CSV → receive top 5 risks per project in <30 seconds
- [ ] All 6 projects analysed correctly
- [ ] Risk explanations are plain-English and actionable
- [ ] 95% test coverage across parser and risk engine modules

## Labels
`sprint-1`, `week-3`, `integration`, `milestone`
""",
        "labels": ["sprint-1", "week-3", "integration"],
    },
]


def create_issues(token: str, repo: str):
    """Create GitHub issues via API."""
    # First create labels
    labels_to_create = [
        {"name": "sprint-1", "color": "0075ca", "description": "Sprint 1: Core Ingestion & Risk Engine"},
        {"name": "sprint-2", "color": "008672", "description": "Sprint 2: Scenario Simulator"},
        {"name": "sprint-3", "color": "d876e3", "description": "Sprint 3: Artefact Generation"},
        {"name": "sprint-4", "color": "e4e669", "description": "Sprint 4: Plugin & Launch"},
        {"name": "week-1", "color": "bfdadc", "description": "Week 1"},
        {"name": "week-2", "color": "bfdadc", "description": "Week 2"},
        {"name": "week-3", "color": "bfdadc", "description": "Week 3"},
        {"name": "setup", "color": "c5def5", "description": "Project setup"},
        {"name": "parser", "color": "c5def5", "description": "Data parsing"},
        {"name": "validation", "color": "c5def5", "description": "Validation"},
        {"name": "risk-engine", "color": "f9d0c4", "description": "Risk detection engine"},
        {"name": "integration", "color": "fbca04", "description": "Integration testing"},
    ]

    for label in labels_to_create:
        data = json.dumps(label).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/labels",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            print(f"  Label created: {label['name']}")
        except urllib.error.HTTPError as e:
            if e.code == 422:  # Already exists
                print(f"  Label exists: {label['name']}")
            else:
                print(f"  Label error: {label['name']} ({e.code})")

    # Create issues
    for issue in ISSUES:
        data = json.dumps({
            "title": issue["title"],
            "body": issue["body"],
            "labels": issue["labels"],
        }).encode()

        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req)
            result = json.loads(resp.read())
            print(f"  Issue #{result['number']}: {issue['title']}")
        except urllib.error.HTTPError as e:
            print(f"  Error creating: {issue['title']} ({e.code}: {e.read().decode()})")


if __name__ == "__main__":
    token = os.environ.get("GITHUB_PAT", "")
    repo = os.environ.get("GITHUB_REPO", "")

    if not token or not repo:
        print("Sprint 1 Issues (10 total):")
        print("=" * 60)
        for i, issue in enumerate(ISSUES, 1):
            print(f"\n{i}. {issue['title']}")
            print(f"   Labels: {', '.join(issue['labels'])}")
        print("\nTo create automatically, set GITHUB_PAT and GITHUB_REPO env vars.")
        sys.exit(0)

    print(f"Creating issues in {repo}...")
    print("\nCreating labels...")
    create_issues(token, repo)
    print("\nDone!")
