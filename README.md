# Portfolio Risk Copilot

**AI-powered decision intelligence for PMOs.** Turn messy project data into exec-ready briefings, proactive risk analysis, benefits tracking, and portfolio "what-if" scenarios — in under 90 seconds.

Built with [Claude Opus 4.6](https://www.anthropic.com) as a [Cowork](https://claude.com/product/cowork) plugin. Free, open-source, and 100% local — your data never leaves your machine.

> *"Before this, I spent 2–3 days per month assembling board packs from Jira exports and Excel trackers. Now I upload our data, run one command, and have an exec-ready briefing in 90 seconds."*

---

## What It Does

Upload your Jira/DevOps/Smartsheet exports and benefits register. Get back **8 publication-quality documents** with embedded charts:

| Artefact | What's in it |
|----------|-------------|
| **Portfolio Dashboard** (DOCX) | 2-page CXO overview: KPI cards, composite chart, RAG table, key decisions |
| **Board Briefing** (DOCX + PPTX) | Executive action summary, dashboard chart, top 3 risks, recommended decisions |
| **Steering Committee Pack** (DOCX) | Full narrative with RAG donut, budget bars, risk heatmap, benefits section, talking points |
| **Project Status Pack** (DOCX) | Per-project RAG status, risks, forecast deltas, action items |
| **Benefits Report** (DOCX) | Realisation rates, waterfall chart, drift analysis, recommendations |
| **Investment Summary** (DOCX) | ROI league table, Invest/Hold/Divest recommendations, bubble chart |
| **Decision Log** (DOCX) | Structured audit trail of portfolio decisions with options and rationale |

Every document opens with a punchy **executive action summary** — the paragraph a CXO reads on their phone at 7am.

### Charts

All documents include publication-quality charts (powered by matplotlib):

- **RAG donut** — portfolio health at a glance
- **Budget vs spend bars** — overspend highlighted in red
- **Risk heatmap** — severity × category matrix
- **Benefits waterfall** — Expected → Realised → At Risk → Adjusted
- **Benefits drift bars** — per-project with 15%/30% threshold lines
- **ROI bubble chart** — ROI vs Risk, bubble size = budget, colour = Invest/Hold/Divest
- **Composite dashboard** — 2×2 grid combining the key views

Charts degrade gracefully to text-only if matplotlib is not installed.

---

## Quick Start

### Option 1: Cowork Plugin (recommended)

1. Download **[portfolio-risk-copilot-v1.2.0.zip](https://github.com/JustinNarracott/portfolio-risk-copilot/releases/latest)** from Releases
2. Open Claude Desktop → Cowork → Plugins → **Upload plugin** → select the zip
3. Start using it:

```
/help                              — Quick-start guide and reference
/ingest <folder>                   — Load and analyse project data
/risks                             — Show top risks per project
/scenario "delay Alpha by 3 months" — Model a what-if scenario
/brief all --output-dir ./output   — Generate all 8 documents
```

That's it. No git, no terminal, no setup.

### Option 2: CLI

```bash
# Clone
git clone https://github.com/JustinNarracott/portfolio-risk-copilot.git
cd portfolio-risk-copilot

# Install dependencies
pip install -r requirements.txt

# Run with sample data
python -c "
from src.cli import main, _session
from datetime import date
_session.reference_date = date.today()
main(['ingest', './sample-data'])
main(['risks'])
main(['brief', 'all', '--output-dir', './output'])
"
```

Eight documents in your `./output` folder.

---

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
| `brief dashboard` | Generate 2-page portfolio dashboard (DOCX) |
| `brief decisions` | Generate decision log (DOCX) |
| `brief all` | Generate all 8 artefacts |

### Options

```bash
--output-dir ./my-folder    # Where to save generated files
--logo ./logo.png           # Add your logo to briefings
--colour 1F4E79             # Set primary brand colour (hex)
```

---

## What Data Do I Need?

**Minimum:** A CSV/Excel export from your PM tool with columns for project name, task name, and task status.

**For full analysis:** Add budget, actual spend, dates, priorities, assignees, sprint history, and comments.

**For benefits tracking:** A separate CSV/Excel with project name, expected benefit value, realised value, and status.

The parser handles messy column names, mixed date formats, and missing data gracefully. It supports exports from Jira, Azure DevOps, Smartsheet, MS Project, Monday.com, and generic trackers.

### Supported Export Formats

| Source | How to export |
|--------|-------------|
| **Jira** | Filters → Export → CSV (include all fields) |
| **Azure DevOps** | Queries → Export to CSV |
| **Smartsheet** | File → Export → CSV or Excel |
| **Monday.com** | Board menu → Export → Excel |
| **MS Project** | File → Save As → CSV |
| **Generic** | Any CSV/Excel with project name, task name, task status columns |

---

## Sample Data

The `sample-data/` folder contains a realistic 11-project portfolio:

- **portfolio-export.csv** — 11 projects, 69 tasks, mixed health states
- **benefits-register.csv** — 21 benefits across 11 projects
- **jira-export-sample.csv** — 6-project Jira export format
- **jira-export-sample.json** — Same data in JSON format

Projects include platform rebuilds, mobile launches, compliance programmes, office relocations, security upgrades, and an on-hold HR system — the kind of portfolio a real PMO manages.

---

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

```
"delay Alpha by 3 months"
"cut Beta budget by 30%"
"remove Delta from portfolio"
"increase Zeta scope by 25%"
```

Each scenario produces a before/after impact summary with cascade effects on dependent projects and recommendations.

## Benefits Intelligence

Upload a benefits register and get:

- **Realisation rates** per project and across the portfolio
- **Benefits drift detection** — flags when expected value is eroding
- **Drift RAG** — Green (<15%), Amber (15–30%), Red (>30%)
- **CXO-readable explanations** — "Alpha was forecast to deliver £500k. Adjusted estimate is £320k — 36% drift."
- **Recommendations** — escalate, protect, or write down

## Investment Analysis

See your portfolio through a financial lens:

- **ROI per project** — ranked from best to worst return
- **Invest/Hold/Divest recommendations** — based on ROI × RAG × drift
- **Cost-to-complete** — how much more each project needs
- **Reallocation opportunities** — where freed budget could go

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **Documents** | python-docx, python-pptx |
| **Charts** | matplotlib |
| **Data parsing** | pandas, openpyxl |
| **Testing** | pytest — 522 tests, 94% coverage |
| **Distribution** | Cowork plugin (GitHub) |
| **Licence** | MIT |

---

## Project Status

**v1.2.0** — All sprints complete

- ✅ Data ingestion (CSV, JSON, Excel) with flexible column mapping
- ✅ Risk detection engine (5 categories, severity ranking, plain-English explanations)
- ✅ Scenario simulator (budget, scope, delay, removal with cascade impact)
- ✅ 8 artefact types with publication-quality embedded charts
- ✅ Benefits realisation tracking and drift detection
- ✅ Portfolio investment & ROI analysis with Invest/Hold/Divest
- ✅ Decision log generator (audit trail from scenarios and analysis)
- ✅ Executive action summary (the "7am phone check" paragraph)
- ✅ Portfolio dashboard (2-page CXO overview with KPI cards and composite chart)
- ✅ Cowork plugin with 5 slash commands and 3 skills
- ✅ 522 tests, 94% coverage

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Contributions welcome — especially additional PM tool export formats, chart types, and artefact templates.

## Licence

MIT — see [LICENSE](LICENSE).

---

## About

Built by [Justin Narracott](https://www.linkedin.com/in/justinnarracott/) — PMO consultant, AI governance practitioner, and founder of [SignalBreak.io](https://signalbreak.io) and [Step5Consult](https://step5consult.co.uk).

Built with Claude Opus 4.6 in 5.5 hours (originally estimated at 240 hours / 12 weeks). Follow the journey on [LinkedIn](https://www.linkedin.com/in/justinnarracott/) and [Twitter/X](https://x.com/JustinNarracott).
