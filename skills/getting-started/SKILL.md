---
name: getting-started
description: Onboarding and first-use guidance for Portfolio Risk Copilot. Triggers when a user first installs the plugin, asks how to use it, asks what commands are available, or seems unfamiliar with the workflow. Also triggers on phrases like "how does this work", "what can you do", "help me get started", "what do I need", or "how do I use this".
---

# Getting Started with Portfolio Risk Copilot

You are helping a PMO professional or project leader get started with the Portfolio Risk Copilot plugin.

## When this skill triggers

- User has just installed the plugin and opens their first session
- User asks "how does this work?", "what can you do?", "help", or similar
- User seems confused about what data to provide or what commands to run
- User asks about supported file formats or data requirements

## How to onboard a new user

Be warm, concise, and practical. PMO professionals are busy — they want to see value fast, not read documentation.

### Step 1: Ask about their data

Ask what PM tool they use (Jira, Azure DevOps, Smartsheet, Monday, MS Project, or other). Then explain how to export:

- **Jira**: Filters → Export → CSV (include all fields)
- **Azure DevOps**: Queries → Export to CSV
- **Smartsheet**: File → Export → CSV or Excel
- **Monday.com**: Board menu → Export → Excel
- **MS Project**: File → Save As → CSV
- **Generic**: Any CSV/Excel with columns for project name, task name, and task status

### Step 2: Explain the workflow

The plugin works in 3 steps:
1. `/ingest <folder>` — point it at a folder containing your exports
2. `/risks` — see what's at risk and why
3. `/brief <type>` — generate the document you need

For what-if analysis, add `/scenario "<change>"` between steps 2 and 3.

### Step 3: Recommend a first action

If they have data ready: suggest running `/ingest` immediately.
If they don't have data yet: suggest trying the sample data first (`/ingest sample-data`).
If they're evaluating the tool: walk them through the sample data workflow and explain what each output means.

## Data format details

### Project data (required)

Minimum columns needed:
- **Project name** (or "Project", "project_name", "Project Key")
- **Task name** (or "Summary", "task_name", "Issue")
- **Task status** (or "Status", "task_status", "State")

Recommended additional columns (improve analysis quality):
- Start date, End date / Due date
- Budget, Actual spend
- Priority
- Assignee
- Sprint / Iteration
- Comments / Description (used for dependency and blocker keyword scanning)

### Benefits data (optional)

Separate CSV or Excel file with:
- Project name
- Benefit description
- Expected value (£ or $)
- Realised value (£ or $)
- Status (Planning, In Progress, Realised, At Risk)

### What happens if columns are missing?

The tool handles this gracefully:
- No budget data → budget/burn rate analysis skipped
- No dates → timeline analysis skipped
- No comments → dependency keyword scanning skipped
- No benefits file → benefits section shows "No data available"

The tool never fails on missing columns — it just produces less detailed analysis.

## Common first-session issues

- **"No data loaded"**: User needs to run `/ingest` first. Data doesn't persist between sessions.
- **"Missing required columns"**: The file doesn't have project name, task name, or task status columns. Help them identify which columns map to these.
- **Benefits file skipped**: Benefits files don't have task-level data — this is normal. They're parsed separately for the benefits analysis.
- **matplotlib not installed**: Charts won't embed in documents but everything else works. Suggest `pip install matplotlib`.
