# /pmo:scenario

Run a what-if scenario simulation and show the portfolio impact.

## Usage

```
/pmo:scenario "<scenario description>"
```

## What to do

1. Ensure data has been ingested first (via `/pmo:ingest`).
2. Run the scenario simulation:

```bash
cd <plugin-directory>
python -c "
from src.cli import main
main(['scenario', '<scenario description>'])
"
```

3. Present the impact summary: before/after comparison of delivery dates, budget, dependent project effects, and benefits at risk.

## Supported scenarios

- **Budget changes**: "increase Project Beta budget by 20%", "cut Alpha budget to £200k"
- **Scope changes**: "cut Project Beta scope by 30%", "reduce Gamma scope by half"
- **Delays**: "delay Project Alpha by 3 months", "delay Gamma by 1 quarter"
- **Removal**: "remove Project Delta", "cancel the HR system project"

## Examples

```
/pmo:scenario "delay Alpha - Platform Rebuild by 3 months"
/pmo:scenario "cut Beta scope by 30%"
/pmo:scenario "increase Gamma budget by 50%"
/pmo:scenario "remove Lambda - HR System"
```
