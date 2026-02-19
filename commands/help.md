# /pmo:help

Show the user how to get started with Portfolio Risk Copilot.

## What to do

Display a clear, friendly getting-started guide. Do not run any code — just explain.

Present the following information conversationally:

---

**Portfolio Risk Copilot** turns messy project data into exec-ready briefings, risk analysis, and what-if scenarios.

### Quick start

1. **Export your project data** from Jira, Azure DevOps, Smartsheet, or any PM tool as CSV, JSON, or Excel.
2. **Put the files in a folder** on your machine (e.g., `~/Documents/project-data/`).
3. **Run the commands** in order:

| Step | Command | What it does |
|------|---------|-------------|
| 1 | `/ingest <folder>` | Loads and analyses your project data |
| 2 | `/risks` | Shows top risks per project with plain-English explanations |
| 3 | `/scenario "<change>"` | Models a what-if scenario (budget cut, delay, scope change) |
| 4 | `/brief <type>` | Generates exec-ready documents (DOCX/PPTX) |

### What data do I need?

**Project data** (required) — CSV, JSON, or Excel with these columns:
- **Required**: Project name, Task name, Task status
- **Recommended**: Start date, End date, Budget, Actual spend, Assignee, Comments/descriptions
- Common sources: Jira export, Azure DevOps query export, Smartsheet download, MS Project CSV

**Benefits data** (optional, improves output) — CSV or Excel with:
- Project name, Benefit description, Expected value, Realised value, Status

You can put multiple files in the same folder — the tool will parse all supported files automatically.

### Brief types

| Type | What you get |
|------|-------------|
| `board` | 1-page exec summary + PowerPoint (dashboard chart, top risks, decisions) |
| `steering` | 2-3 page steering committee pack with charts and talking points |
| `project` | Per-project status pack with RAG, risks, and actions |
| `benefits` | Benefits realisation report with waterfall and drift charts |
| `investment` | ROI analysis with Invest/Hold/Divest recommendations |
| `dashboard` | 2-page CXO dashboard with KPI cards and composite chart |
| `decisions` | Decision log and audit trail |
| `all` | All 8 documents above |

### Example scenarios

```
/scenario "delay Alpha by 3 months"
/scenario "cut Beta scope by 30%"
/scenario "increase Gamma budget by 50%"
/scenario "remove the HR system project"
```

### Sample data

The plugin includes sample data in the `sample-data/` folder. Try `/ingest sample-data` to see how it works before using your own data.

### Tips

- All processing happens locally — your data never leaves your machine.
- Generated documents are standard DOCX/PPTX — fully editable in Word, PowerPoint, or Google Docs.
- Charts are embedded automatically (requires matplotlib). Documents degrade gracefully to text-only if matplotlib isn't available.
- Run `/ingest` at the start of each Cowork session — data doesn't persist between sessions.
