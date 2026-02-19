# Contributing to Portfolio Risk Copilot

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/portfolio-risk-copilot.git`
3. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run tests: `python -m pytest`

## Development Guidelines

### Code Style

- Python 3.11+ with type hints throughout
- Functions and classes should have docstrings
- Use `from __future__ import annotations` for modern type syntax
- Follow existing naming conventions (snake_case for functions/variables, PascalCase for classes)

### Testing

- All new features need tests (target 95%+ coverage)
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Use pytest fixtures and parametrise where appropriate
- Run the full suite before submitting: `python -m pytest --cov=src`

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

- Add support for additional PM tool export formats
- Improve risk explanation text quality
- Add more scenario parser patterns
- Expand sample data with additional risk scenarios

### Larger Features

- Monte Carlo simulation for delivery forecasting
- Jira/Azure DevOps API integration
- Additional artefact templates (Excel summary, PDF)
- Web UI for non-CLI users

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass: `python -m pytest`
4. Update documentation if adding new commands or features
5. Submit a PR with a clear description of changes

## Questions?

Open an issue or reach out to [@JustinNarracott](https://github.com/JustinNarracott).
