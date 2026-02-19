# Portfolio Risk Copilot — User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Preparing Your Data](#preparing-your-data)
3. [Workflow: Risk Analysis](#workflow-risk-analysis)
4. [Workflow: Scenario Simulation](#workflow-scenario-simulation)
5. [Workflow: Generating Briefings](#workflow-generating-briefings)
6. [Customising Output](#customising-output)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Python 3.11 or later
- A Claude Max, Team, or Enterprise subscription (for Cowork)
- Windows (x64) or macOS

### Installation

```bash
git clone https://github.com/JustinNarracott/portfolio-risk-copilot.git
cd portfolio-risk-copilot
pip install -r requirements.txt
```

### Verify Installation

```bash
python -m src.cli --version
# Output: pmo-copilot 1.0.0
```

---

## Preparing Your Data

### Supported Formats

The tool accepts **CSV**, **JSON**, and **Excel (XLSX)** files exported from any PM tool.

### Required Columns

At minimum, your export should include:

| Data | Example Column Names |
|------|---------------------|
| Project name | `Project`, `Project Name`, `Project Key` |
| Task name | `Task`, `Summary`, `Issue`, `Title` |
| Task status | `Status`, `State`, `Task Status` |
| Start date | `Start Date`, `Created`, `Start` |
| End date | `End Date`, `Due Date`, `Target Date` |
| Budget | `Budget`, `Planned Cost`, `Estimated Cost` |
| Actual spend | `Actual`, `Actual Cost`, `Actual Spend` |
| Comments | `Comments`, `Notes`, `Description` |

The parser recognises **40+ column name aliases** automatically. If your export uses different names, the tool will still attempt to match them.

### Optional Columns (Improve Risk Detection)

| Data | Purpose |
|------|---------|
| Assignee | Identify workload concentration |
| Priority | Weight risk severity |
| Sprint/Iteration | Detect carry-over patterns |
| Labels/Tags | Additional context for risk analysis |

### Folder Structure

Place all your export files in a single folder:

```
project-data/
├── jira-export-q1.csv
├── benefit-tracker.xlsx
└── status-notes.json
```

---

## Workflow: Risk Analysis

### Step 1: Ingest Data

```bash
python -m src.cli ingest ./project-data
```

The tool will scan the folder, validate each file, parse project data, and run initial risk analysis.

### Step 2: View Risks

```bash
python -m src.cli risks
```

This displays the top 5 risks per project, ranked by severity:

- **Critical** — Immediate intervention required
- **High** — Attention needed this cycle
- **Medium** — Monitor and plan mitigation
- **Low** — Awareness item

### Understanding Risk Categories

**Blocked Work**: Tasks stuck in "Blocked", "Waiting", or "On Hold" status for more than 2 weeks. Also detects blocker keywords in comments ("blocked by", "waiting for").

**Chronic Carry-Over**: Tasks that have been moved across 3 or more sprints without completion. Indicates scope creep or persistent impediments.

**Burn Rate**: Projects where actual spend exceeds 90% of budget with more than 10% of the timeline remaining. Flags budget exhaustion risk.

**Dependencies**: Cross-project dependency risks detected from task comments containing phrases like "depends on Project X", "blocked by Alpha", "waiting for Beta delivery".

---

## Workflow: Scenario Simulation

After ingesting data, you can model portfolio changes:

### Budget Changes

```bash
python -m src.cli scenario "increase Alpha budget by 20%"
python -m src.cli scenario "decrease Gamma budget by £50000"
```

Shows impact on runway, risk levels, and whether the project is still within budget.

### Scope Cuts

```bash
python -m src.cli scenario "cut Beta scope by 30%"
```

Models the delivery date shift (linear model) and identifies dependent projects that benefit from earlier delivery.

### Delays

```bash
python -m src.cli scenario "delay Alpha by 1 quarter"
```

Shifts the timeline and shows cascade delays on all dependent projects.

### Project Removal

```bash
python -m src.cli scenario "remove Delta"
```

Calculates freed budget, identifies broken dependencies, and flags projects that need re-planning.

---

## Workflow: Generating Briefings

### Board Briefing (1 page)

```bash
python -m src.cli brief board --output-dir ./output
```

Generates `board-briefing.docx` and `board-briefing.pptx` containing:
- Portfolio health RAG summary
- Project-level RAG table
- Top 3 risks with severity indicators
- 3 recommended decisions

### Steering Committee Pack (2–3 pages)

```bash
python -m src.cli brief steering --output-dir ./output
```

Generates `steering-committee-pack.docx` containing:
- Executive summary with portfolio statistics
- Detailed project RAG table
- Top 5 risks with explanations and mitigations
- Recommended decisions
- Key talking points for the meeting

### Project Status Pack

```bash
python -m src.cli brief project --output-dir ./output
```

Generates `project-status-pack.docx` with 1–2 pages per project:
- RAG status with explanation
- Risk list with severities
- Action items derived from mitigations

### All Artefacts

```bash
python -m src.cli brief all --output-dir ./output
```

Generates all briefing types in one command.

---

## Customising Output

### Brand Colours

```bash
python -m src.cli brief board --colour 003366 --output-dir ./output
```

The `--colour` flag sets the primary brand colour (hex without #) used for headings, table headers, and accent elements.

### Company Logo

```bash
python -m src.cli brief steering --logo ./assets/logo.png --output-dir ./output
```

Adds your company logo to the document header. Accepts PNG and JPG formats.

### Custom Section Headings

For programmatic use, the `BrandConfig` class accepts custom heading overrides:

```python
from src.artefacts.docx_generator import BrandConfig, generate_board_briefing

brand = BrandConfig(
    primary_colour="003366",
    company_name="Acme Corp",
    custom_headings={
        "board_title": "Acme Corp — Monthly Portfolio Update",
        "top_risks": "Priority Risk Items",
        "decisions": "Actions for Board Approval",
    },
)
```

---

## Troubleshooting

### "No CSV, JSON, or Excel files found"

Check that your data folder contains files with `.csv`, `.json`, or `.xlsx` extensions. The tool does not read `.xls` (legacy Excel) or `.txt` files during ingestion.

### "No valid project data found"

Your files were found but couldn't be parsed. Common causes:
- CSV file is empty or has no header row
- Column names don't match any of the 40+ recognised aliases
- JSON file is not an array of objects

### Risk counts seem low

The tool only flags risks that meet defined thresholds:
- Blocked work: must be blocked >2 weeks
- Carry-over: must span 3+ sprints
- Burn rate: must exceed 90% spent with >10% time remaining
- Dependencies: must contain explicit cross-project keywords in comments

### Scenario parser doesn't recognise my input

The parser supports these patterns:
- `"increase/decrease <project> budget by <N>%"` or `"by £<N>"`
- `"cut/reduce <project> scope by <N>%"`
- `"delay/postpone <project> by <N> weeks/months/quarters"`
- `"remove/cancel <project>"`

Ensure the project name matches what was ingested (case-insensitive).
