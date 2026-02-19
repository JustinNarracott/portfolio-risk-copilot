# /pmo:brief

Generate stakeholder-specific briefing documents (DOCX/PPTX).

## Usage

```
/pmo:brief <type> [--output-dir <path>]
```

## Available types

| Type | Output | Description |
|------|--------|-------------|
| `board` | board-briefing.docx + board-briefing.pptx | 1-page exec summary with dashboard chart, top risks, decisions |
| `steering` | steering-committee-pack.docx | 2-3 page pack with charts, risk analysis, benefits section, talking points |
| `project` | project-status-pack.docx | Per-project RAG status, risks, and actions |
| `benefits` | benefits-report.docx | Benefits realisation, drift analysis, waterfall chart |
| `investment` | investment-summary.docx | ROI analysis, Invest/Hold/Divest recommendations, bubble chart |
| `dashboard` | portfolio-dashboard.docx | 2-page CXO dashboard with KPI cards, composite chart, RAG table |
| `decisions` | decision-log.docx | Decision audit trail with options and recommendations |
| `all` | All 8 documents above | Full artefact suite |

## What to do

1. Ensure data has been ingested first (via `/pmo:ingest`).
2. Run the briefing generator:

```bash
cd <plugin-directory>
python -c "
from src.cli import main
main(['brief', '<type>', '--output-dir', '<output-dir>'])
"
```

3. Present the generated files to the user. Open or share the output directory.

## Notes

- If no `--output-dir` is specified, files are created in the current working directory.
- All DOCX files include publication-quality matplotlib charts (RAG donut, budget bars, risk heatmap, benefits waterfall, ROI bubble chart, composite dashboard).
- Charts degrade gracefully to text if matplotlib is not installed.
- Branding can be customised with `--logo`, `--colour`, `--font` flags.

## Examples

```
/pmo:brief board
/pmo:brief steering --output-dir ~/Desktop/board-pack
/pmo:brief all --output-dir ./output
/pmo:brief dashboard
```
