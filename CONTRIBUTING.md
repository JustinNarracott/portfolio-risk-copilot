# Contributing to Portfolio Risk Copilot

Thanks for your interest in contributing! This guide covers everything you need to get started.

Please also read our [Code of Conduct](CODE_OF_CONDUCT.md) — we're committed to a welcoming community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/portfolio-risk-copilot.git`
3. Create a virtual environment:
   - **Windows:** `python -m venv .venv && .venv\Scripts\activate`
   - **macOS/Linux:** `python -m venv .venv && source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run tests: `python -m pytest`
6. Try the demo: `python demo.py` — generates sample artefacts in `./demo-output/`

## Reporting Bugs

Use the [Bug Report template](https://github.com/JustinNarracott/portfolio-risk-copilot/issues/new?template=bug_report.yml). Include your platform, version, steps to reproduce, and any error output.

**Important:** Never share confidential project data in issues. Describe the shape of your data instead (e.g. "CSV with 200 rows, 8 projects, includes benefits register").

## Suggesting Features

Use the [Feature Request template](https://github.com/JustinNarracott/portfolio-risk-copilot/issues/new?template=feature_request.yml). Explain the problem you're solving and your proposed approach.

## Development Guidelines

### Code Style

- Python 3.11+ with type hints throughout
- Functions and classes should have docstrings
- Use `from __future__ import annotations` for modern type syntax
- Follow existing naming conventions (snake_case for functions/variables, PascalCase for classes)
- Line length: 120 characters (configured in pyproject.toml)

### Testing

- All new features need tests (target 94%+ coverage)
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Use pytest fixtures and parametrise where appropriate
- Run the full suite before submitting: `python -m pytest --cov=src`

### Project Structure

```
src/
├── ingestion/       # CSV/JSON/Excel parsing, column mapping
├── risk_engine/     # 5 risk detectors + aggregation engine
├── scenario/        # What-if parser, dependency graph, simulators
├── artefacts/       # DOCX/PPTX generators
├── benefits/        # Benefits parsing, drift calculation, reports
├── investment/      # ROI analysis, Invest/Hold/Divest logic
├── decisions/       # Decision log generation
├── insights/        # Executive action summary
├── charts/          # matplotlib chart generators
└── cli.py           # CLI entry point and session management
```

### Commit Messages

Use clear, descriptive commit messages:

```
Add scope cut simulator with cascade impact detection

- Implement linear delivery date shift model
- Flag dependent projects with earlier delivery window
- Add 4 unit tests covering 10%, 30%, 50% cuts
```

## Areas for Contribution

### Good First Issues

- Add support for additional PM tool export formats (Monday.com, Wrike, Basecamp)
- Improve risk explanation text quality
- Add more scenario parser patterns (e.g. "reassign 3 people from Alpha to Beta")
- Expand sample data with additional risk scenarios
- Improve chart styling and colour palettes

### Larger Features

- Monte Carlo simulation for delivery forecasting
- Jira/Azure DevOps API integration (MCP server)
- Excel summary artefact (XLSX output)
- PDF artefact generation
- Web UI for non-CLI users
- Additional chart types (Gantt, burndown)

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass: `python -m pytest`
4. Update documentation if adding new commands or features
5. Submit a PR using the [PR template](.github/PULL_REQUEST_TEMPLATE.md) with a clear description of changes

## Security

Found a vulnerability? Please report it responsibly — see [SECURITY.md](.github/SECURITY.md). Do not open a public issue for security concerns.

## Questions?

Open a [Discussion](https://github.com/JustinNarracott/portfolio-risk-copilot/discussions) or reach out to [@JustinNarracott](https://github.com/JustinNarracott).
