# /pmo:ingest

Ingest project data from a folder of CSV, JSON, or Excel exports.

## Usage

```
/pmo:ingest <folder-path>
```

## What to do

1. Look in the folder the user specified for files ending in `.csv`, `.json`, `.xlsx`, or `.xls`.
2. Run the Python ingestion and analysis pipeline:

```bash
cd <plugin-directory>
python -c "
from src.cli import main, _session
from datetime import date
_session.reference_date = date.today()
main(['ingest', '<folder-path>'])
"
```

3. Show the user the summary: how many projects loaded, portfolio RAG status, total risks, and benefits drift.
4. Store the session state — subsequent commands (`/pmo:risks`, `/pmo:brief`, `/pmo:scenario`) depend on data being ingested first.

## Notes

- Supported formats: Jira CSV, Azure DevOps CSV, Smartsheet Excel, generic project CSVs, JSON exports.
- Required columns for project data: project name (or "Project"), task name, task status. Budget, dates, and comments are optional but improve analysis.
- Benefits data can be in a separate file with columns: project name, benefit description, expected value, realised value.
- If files fail to parse, the tool will show which files were skipped and why.

## Examples

```
/pmo:ingest ./project-data
/pmo:ingest ~/Documents/jira-exports
/pmo:ingest C:\Users\Justin\Downloads\portfolio-data
```
