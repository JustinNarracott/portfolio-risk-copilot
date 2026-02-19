# Portfolio Risk Copilot

**A free, open-source Claude Opus-powered tool for PMOs and project leaders.**

Turn messy project data (Jira exports, Excel trackers, free-text notes) into exec-ready briefings, proactive risk analysis, and portfolio "what-if" scenarios in under 5 minutes.

> **Status:** 🔨 In Development — Sprint 1 (Core Ingestion & Risk Engine)

---

## What It Does

| Capability | Description |
|-----------|-------------|
| **Risk Detection** | Identifies blocked work, chronic carry-over, burn rate alerts, and dependency risks across your portfolio |
| **Scenario Simulation** | Model "what-if" changes (budget cuts, delays, scope changes) and see cascading impact on delivery |
| **Exec Briefings** | Auto-generate board briefings, steering committee packs, and project status reports (DOCX/PPTX) |
| **Tool-Agnostic** | Works with exports from Jira, Azure DevOps, Smartsheet, MS Project, or any CSV/Excel tracker |

---

## Quick Start

> ⚠️ **Coming Soon** — Cowork plugin marketplace installation will be available at launch (Q2 2026).

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/portfolio-risk-copilot.git
cd portfolio-risk-copilot

# Set up virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## Cowork Plugin Commands

| Command | Description |
|---------|-------------|
| `/pmo-ingest [folder]` | Ingest project data from a folder (CSV/JSON/Excel) |
| `/pmo-risks` | Generate top 5 risks per project with plain-English explanations |
| `/pmo-scenario "[description]"` | Run a what-if scenario and narrate portfolio impact |
| `/pmo-brief [board\|steering\|project]` | Generate a stakeholder-specific briefing (DOCX/PPTX) |

---

## Project Structure

```
portfolio-risk-copilot/
├── src/
│   ├── __init__.py
│   ├── ingestion/          # File parsing (CSV, JSON, Excel)
│   │   ├── __init__.py
│   │   ├── parser.py       # Core data parser
│   │   └── validators.py   # File format validation
│   ├── risk_engine/        # Risk detection & pattern analysis
│   │   ├── __init__.py
│   │   ├── blocked.py      # Blocked work detection
│   │   ├── carryover.py    # Chronic carry-over detection
│   │   ├── burnrate.py     # Burn rate alerts
│   │   ├── dependencies.py # Dependency keyword scanner
│   │   └── engine.py       # Risk aggregation & ranking
│   ├── scenario/           # What-if scenario simulation (Sprint 2)
│   ├── artefacts/          # Document generation (Sprint 3)
│   └── plugin/             # Cowork plugin packaging (Sprint 4)
├── tests/
│   ├── fixtures/           # Test data files
│   ├── unit/               # Unit tests
│   └── integration/        # End-to-end tests
├── sample-data/            # Example Jira/DevOps exports for testing and demos
├── docs/                   # User guide, contributing guide
├── templates/              # DOCX/PPTX briefing templates
├── pyproject.toml          # Project config and dependencies
└── README.md
```

---

## Roadmap

| Sprint | Weeks | Focus | Status |
|--------|-------|-------|--------|
| **Sprint 1** | 1–3 | Core Ingestion & Risk Engine | 🔨 In Progress |
| **Sprint 2** | 4–6 | Scenario Simulator & Portfolio Impact | ⏳ Planned |
| **Sprint 3** | 7–9 | Artefact Generation & Stakeholder Templates | ⏳ Planned |
| **Sprint 4** | 10–12 | Cowork Plugin Packaging & Launch | ⏳ Planned |

---

## Tech Stack

- **Runtime:** Claude Cowork (Windows x64 / Mac) with Opus 4.6
- **Language:** Python 3.11+
- **Libraries:** pandas, python-docx, python-pptx, openpyxl, pytest
- **Distribution:** Cowork plugin marketplace (GitHub-hosted)

---

## Contributing

This project is currently in solo development. Contributing guidelines will be published before the public launch. If you're a PMO professional interested in beta testing, please reach out.

---

## Licence

MIT — see [LICENSE](LICENSE) for details.
