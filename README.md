# Portfolio Risk Copilot

**Turn messy project data into exec-ready briefings in under 5 minutes.**

A free, open-source decision-support tool for PMOs and project leaders. Upload your Jira, Azure DevOps, or Smartsheet exports — get ranked risks, what-if scenarios, and board-ready briefings (Word & PowerPoint) powered by Claude Opus.

---

## Why This Exists

PMOs spend 40–60% of their time on manual reporting instead of strategic decision-making. Existing PM tools show *what is* (dashboards, status boards) but not *what if* (scenarios, forecasts, recommendations).

**Portfolio Risk Copilot** fills that gap:

- **Risk detection** — Surfaces blocked work, chronic carry-over, budget overruns, and dependency risks automatically
- **Scenario simulation** — Model budget cuts, scope changes, delays, and project removals with cascade impact analysis
- **Exec-ready artefacts** — Generates board briefings, steering committee packs, and project status reports in Word/PowerPoint
- **Tool-agnostic** — Works with exports from any PM tool (CSV, JSON, Excel)

---

## Quick Start

### Installation

```bash
git clone https://github.com/JustinNarracott/portfolio-risk-copilot.git
cd portfolio-risk-copilot
pip install -r requirements.txt
```

### 90-Second Workflow

```bash
# 1. Ingest your project data
python -m src.cli ingest ./sample-data

# 2. View top risks per project
python -m src.cli risks

# 3. Run a what-if scenario
python -m src.cli scenario "cut Beta scope by 30%"

# 4. Generate a steering committee briefing
python -m src.cli brief steering --output-dir ./output
```

That's it. Open `./output/steering-committee-pack.docx` and you have an exec-ready pack.

---

## Commands

### `pmo-copilot ingest <folder>`

Scan a folder for CSV, JSON, and Excel files. Parses project metadata, tasks, statuses, dates, budgets, and comments. Runs initial risk analysis automatically.

**Supported formats:** CSV, JSON, Excel (XLSX). Flexible column mapping handles Jira, Azure DevOps, Smartsheet, and generic exports.

### `pmo-copilot risks`

Display the top 5 risks per project with plain-English explanations.

| Flag | Description |
|------|-------------|
| `--top N` | Show top N risks per project (default: 5) |
| `--json` | Output raw JSON for programmatic use |

**Risk categories detected:**
- **Blocked Work** — Tasks stuck in blocked/waiting status for >2 weeks
- **Chronic Carry-Over** — Tasks moved between 3+ sprints without completion
- **Burn Rate** — Budget consumption >90% with >10% time remaining
- **Dependencies** — Cross-project dependency risks from task comments

### `pmo-copilot scenario "<description>"`

Run a natural language what-if scenario and see the portfolio impact.

**Supported scenarios:**
- `"increase Alpha budget by 20%"` — Budget increase (percentage or absolute)
- `"decrease Gamma budget by £50000"` — Budget decrease
- `"cut Beta scope by 30%"` — Scope reduction with delivery date shift
- `"delay Alpha by 1 quarter"` — Schedule delay with cascade impact
- `"remove Delta"` — Project removal with dependency analysis

### `pmo-copilot brief <type>`

Generate stakeholder-specific briefing documents.

| Type | Output | Content |
|------|--------|---------|
| `board` | DOCX + PPTX | 1-page portfolio health, top 3 risks, 3 decisions, RAG table |
| `steering` | DOCX | 2-3 page exec summary, top 5 risks, decisions, talking points |
| `project` | DOCX | Per-project status with RAG, risks, and action items |
| `all` | All above | Full artefact set |

| Flag | Description |
|------|-------------|
| `--logo <path>` | Company logo for document header (PNG/JPG) |
| `--colour <hex>` | Primary brand colour (e.g. `003366`) |
| `--output-dir <path>` | Output directory (default: current) |

---

## Sample Data

The `sample-data/` folder contains a representative dataset with 6 projects and 49 tasks, including baked-in risk patterns:

- **Alpha** — Active project with blocked work and dependency risks
- **Beta** — Planning stage, minimal risks
- **Gamma** — Critical burn rate (92.5% budget consumed)
- **Delta** — Completed project (control case)
- **Epsilon** — Critical burn rate (96.7% budget consumed)
- **Zeta** — Early stage with dependency on product strategy

---

## Architecture

```
src/
├── ingestion/          # File parsing & validation (CSV, JSON, Excel)
│   ├── parser.py       # Flexible column mapping, 40+ aliases
│   └── validators.py   # Format validation with actionable errors
├── risk_engine/        # Risk detection & aggregation
│   ├── blocked.py      # Blocked work detection
│   ├── burnrate.py     # Budget burn rate alerts
│   ├── carryover.py    # Chronic carry-over detection
│   ├── dependencies.py # Cross-project dependency scanning
│   └── engine.py       # Aggregation, RAG derivation, ranking
├── scenario/           # What-if simulation
│   ├── parser.py       # Natural language → structured actions
│   ├── graph.py        # Dependency graph with transitive traversal
│   ├── simulator.py    # Budget, scope, delay, remove simulators
│   └── narrative.py    # CXO-level impact summaries
├── artefacts/          # Document generation
│   ├── docx_generator.py  # Word briefings (python-docx)
│   └── pptx_generator.py  # PowerPoint slides (python-pptx)
└── cli.py              # Unified command interface
```

**Design principles:** Tool-agnostic, decision-first, narrative-driven, privacy-first (local execution, no data leaves your machine).

---

## Development

### Run Tests

```bash
python -m pytest                    # Full suite
python -m pytest --cov=src -v       # With coverage
python -m pytest tests/unit/        # Unit tests only
python -m pytest tests/integration/ # E2E tests only
```

### Current Metrics

- **421+ tests** across unit and integration suites
- **95%+ coverage** across all modules
- **<8 seconds** full suite execution

---

## Roadmap

### Phase 1 (Current) — Free Cowork Plugin
- ✅ CSV/JSON/Excel ingestion with flexible mapping
- ✅ 4 risk detection patterns with severity ranking
- ✅ What-if scenario simulation with cascade impact
- ✅ DOCX/PPTX artefact generation with branding
- ✅ CLI with session state management

### Phase 2 (Planned) — SaaS Version
- Direct Jira/Azure DevOps/Smartsheet API integration
- Team collaboration and shared portfolios
- Monte Carlo forecasting
- Continuous monitoring and alerts
- Web UI with real-time dashboards

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Licence

MIT — see [LICENSE](LICENSE).

## About

Built by [Justin Narracott](https://github.com/JustinNarracott) as part of the [SignalBreak.io](https://signalbreak.io) AI governance platform. Powered by Claude Opus.
