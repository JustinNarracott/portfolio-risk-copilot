# /pmo:risks

Display the top risks across the ingested portfolio.

## Usage

```
/pmo:risks
```

## What to do

1. Ensure data has been ingested first (via `/pmo:ingest`). If not, ask the user to run ingest first.
2. Run the risk analysis:

```bash
cd <plugin-directory>
python -c "
from src.cli import main
main(['risks'])
"
```

3. Present the output to the user — a ranked list of risks per project with plain-English explanations, severity levels, and suggested mitigations.

## Notes

- Risk categories detected: Blocked Work, Chronic Carry-Over, Burn Rate, Dependencies.
- Severity levels: Critical, High, Medium, Low.
- RAG mapping: Critical/High → Red, Medium → Amber, Low → Green.

## Examples

```
/pmo:risks
/pmo:risks --top 3
/pmo:risks --json
```
