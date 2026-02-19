# Portfolio Risk Copilot

**AI-powered decision intelligence for PMOs.** Turn messy project data into exec-ready briefings, proactive risk analysis, benefits tracking, and portfolio "what-if" scenarios — in under 90 seconds.

> *"Before this, I spent 2-3 days per month assembling board packs from Jira exports and Excel trackers. Now I upload our data, run one command, and have an exec-ready briefing in 90 seconds."*

## What It Does

Upload your Jira/DevOps/Smartsheet exports and benefits register. Get back:

| Artefact | What's in it |
|----------|-------------|
| **Board Briefing** (DOCX + PPTX) | Executive action summary, portfolio dashboard, top 3 risks, recommended decisions |
| **Steering Committee Pack** (DOCX) | Full narrative with risk commentary, benefits & value section, talking points |
| **Project Status Pack** (DOCX) | Per-project RAG status, risks, forecast deltas, action items |
| **Benefits Report** (DOCX) | Realisation rates, drift analysis, benefits at risk, recommendations |
| **Investment Summary** (DOCX) | ROI league table, Invest/Hold/Divest recommendations, cost-to-complete |
| **Decision Log** (DOCX) | Structured audit trail of portfolio decisions with options and rationale |

Every document opens with a punchy **executive action summary** — the paragraph a CXO reads on their phone at 7am.

## Quick Start

```bash
# Clone
git clone https://github.com/JustinNarracott/portfolio-risk-copilot.git
cd portfolio-risk-copilot

# Install dependencies
pip install -r requirements.txt

# Run with sample data
python -m src.cli ingest ./sample-data
python -m src.cli risks
python -m src.cli scenario "delay Alpha by 3 months"
python -m src.cli brief all --output-dir ./output
```

That's it. Seven documents in your `./output` folder.

## Commands

| Command | What it does |
|---------|-------------|
| `ingest <folder>` | Scan folder for CSV/JSON/Excel files, parse projects and benefits, run analysis |
| `risks` | Display top 5 risks per project with plain-English explanations |
| `risks --json` | Output risk report as JSON |
| `scenario "<description>"` | Model a what-if scenario (e.g. "cut Beta budget by 30%") |
| `brief board` | Generate board briefing (DOCX + PPTX) |
| `brief steering` | Generate steering committee pack (DOCX) |
| `brief project` | Generate per-project status packs (DOCX) |
| `brief benefits` | Generate benefits realisation report (DOCX) |
| `brief investment` | Generate portfolio investment summary (DOCX) |
| `brief decisions` | Generate decision log (DOCX) |
| `brief all` | Generate all artefacts |

### Options

```bash
--output-dir ./my-folder    # Where to save generated files
--logo ./logo.png           # Add your logo to briefings
--colour 1F4E79             # Set primary brand colour (hex)
```

## What Data Do I Need?

**Minimum:** A CSV/Excel export from your PM tool with columns for project name, task name, and task status.

**For full analysis:** Add budget, actual spend, dates, priorities, assignees, sprint history, and comments.

**For benefits tracking:** A separate CSV/Excel with project name, expected benefit value, realised value, and status.

The parser handles messy column names, mixed date formats, and missing data gracefully. It supports exports from Jira, Azure DevOps, Smartsheet, MS Project, and generic trackers.

## Sample Data

The `sample-data/` folder contains a realistic 11-project portfolio:

- **portfolio-export.csv** — 11 projects, 69 tasks, mixed health states
- **benefits-register.csv** — 21 benefits across 11 projects
- **jira-export-sample.csv** — 6-project Jira export format

Projects include platform rebuilds, mobile launches, compliance programmes, office relocations, security upgrades, and an on-hold HR system — the kind of portfolio a real PMO manages.

## Risk Detection

The tool identifies five categories of risk:

1. **Blocked work** — tasks stuck with no resolution plan
2. **Chronic carry-over** — tasks bouncing between sprints
3. **Burn rate alerts** — budget consumption outpacing timeline
4. **Dependency tangles** — tasks with multiple blocking dependencies
5. **Benefits drift** — expected value eroding due to delivery issues

Every risk gets a plain-English explanation and suggested mitigation. No jargon, no database field names.

## Scenario Simulation

Model portfolio changes in natural language:

```bash
python -m src.cli scenario "delay Alpha by 3 months"
python -m src.cli scenario "cut Beta budget by 30%"
python -m src.cli scenario "remove Delta from portfolio"
python -m src.cli scenario "increase Zeta scope by 25%"
```

Each scenario produces a before/after impact summary with cascade effects on dependent projects and recommendations.

## Benefits Intelligence

Upload a benefits register and get:

- **Realisation rates** per project and across the portfolio
- **Benefits drift detection** — flags when expected value is eroding
- **Drift RAG** — Green (<15%), Amber (15-30%), Red (>30%)
- **CXO-readable explanations** — "Alpha was forecast to deliver £500k. Adjusted estimate is £320k — 36% drift."
- **Recommendations** — escalate, protect, or write down

## Investment Analysis

See your portfolio through a financial lens:

- **ROI per project** — ranked from best to worst return
- **Invest/Hold/Divest recommendations** — based on ROI × RAG × drift
- **Cost-to-complete** — how much more each project needs
- **Reallocation opportunities** — where freed budget could go

## Cowork Plugin

This tool is designed to work as a Claude Cowork plugin:

```
/pmo-ingest ./project-data
/pmo-risks
/pmo-scenario "delay Alpha by 1 quarter"
/pmo-brief all
```

See `.claude-plugin/marketplace.json` for the plugin manifest.

## Tech Stack

- **Python 3.11+** — core logic
- **python-docx** — Word document generation
- **python-pptx** — PowerPoint generation
- **pandas** — data parsing
- **openpyxl** — Excel support
- **pytest** — 522 tests, 96% coverage

## Project Status

**v1.1.0** — Sprint 7 complete

- ✅ Data ingestion (CSV, JSON, Excel) with flexible column mapping
- ✅ Risk detection engine (5 categories, severity ranking, plain-English explanations)
- ✅ Scenario simulator (budget, scope, delay, removal)
- ✅ 7 artefact types (board, steering, project, benefits, investment, decisions, PPTX)
- ✅ Benefits realisation tracking and drift detection
- ✅ Portfolio investment & ROI analysis with Invest/Hold/Divest
- ✅ Decision log generator (audit trail from scenarios and analysis)
- ✅ Executive action summary (the "7am phone check" paragraph)
- ✅ 522 tests, 96% coverage

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Licence

MIT — see [LICENCE](LICENCE).

## Built By

[Your Name] — PMO consultant, AI governance practitioner, and founder of [SignalBreak.io](https://signalbreak.io).

Built with Claude Opus as part of a 90-day public build sprint. Follow the journey on [Twitter/X](https://twitter.com/yourhandle) and [LinkedIn](https://linkedin.com/in/yourprofile).
