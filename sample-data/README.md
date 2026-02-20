# Sample Data

These files contain realistic PMO data with deliberate risk patterns baked in for testing.

## Files

### `portfolio-export.csv`
69 tasks across 11 projects — the primary test dataset representing a realistic enterprise portfolio. Includes platform rebuilds, mobile launches, compliance programmes, office relocations, security upgrades, and an on-hold HR system.

### `benefits-register.csv`
21 benefits across 11 projects with varied realisation states. Includes on-track, at-risk, and delayed benefits for testing drift detection and investment analysis.

### `jira-export-sample.csv`
50 tasks across 6 projects in Jira export format. Contains the following known risk patterns:

| Project | Known Risks | Pattern Type |
|---------|------------|--------------|
| **Alpha** | Payment gateway blocked 3+ weeks; multiple dependency chains | Blocked work, Dependencies |
| **Gamma** | Core migration carried over 4 sprints; 92.5% budget spent with 2+ months remaining | Chronic carry-over, Burn rate |
| **Epsilon** | 96.7% budget consumed; audit repeatedly extended; multiple items on hold | Burn rate, Blocked work, Carry-over |
| **Beta** | Vendor selection blocked by procurement; dependency chains | Blocked work, Dependencies |
| **Delta** | Minor carry-over from Sprint 4; generally healthy | Low risk (control case) |
| **Zeta** | Early stage, low spend, no blockers | Low risk (control case) |

### `benefit-tracker-sample.csv`
Benefit register for the 6 Jira-export projects. Key items:

### `jira-export-sample.json`
Same 6-project dataset as the CSV, in JSON format. Useful for testing JSON ingestion path.
- **Gamma**: Partial benefit realisation (50%) — remainder at risk due to delays
- **Epsilon**: No direct financial benefit but £2M non-compliance penalty risk
- **Zeta**: Highest expected benefit (£1M) but highest uncertainty

## Expected Risk Engine Output

When the risk engine processes these files, the top risks should include:

1. **Gamma — Burn rate critical**: 92.5% budget spent with >2 months remaining
2. **Epsilon — Burn rate critical**: 96.7% budget spent with >1 month remaining
3. **Gamma — Chronic carry-over**: Core migration carried over 4 consecutive sprints
4. **Alpha — Blocked work**: Payment gateway blocked 3+ weeks (critical priority)
5. **Epsilon — Blocked work**: Staff training on hold, multiple dependencies on audit completion

Use these expected outputs to validate your risk engine implementation.
