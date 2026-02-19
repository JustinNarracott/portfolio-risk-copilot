# Sample Data

These files contain realistic PMO data with deliberate risk patterns baked in for testing.

## Files

### `jira-export-sample.csv`
50 tasks across 6 projects. Contains the following known risk patterns:

| Project | Known Risks | Pattern Type |
|---------|------------|--------------|
| **Alpha** | Payment gateway blocked 3+ weeks; multiple dependency chains | Blocked work, Dependencies |
| **Gamma** | Core migration carried over 4 sprints; 92.5% budget spent with 2+ months remaining | Chronic carry-over, Burn rate |
| **Epsilon** | 96.7% budget consumed; audit repeatedly extended; multiple items on hold | Burn rate, Blocked work, Carry-over |
| **Beta** | Vendor selection blocked by procurement; dependency chains | Blocked work, Dependencies |
| **Delta** | Minor carry-over from Sprint 4; generally healthy | Low risk (control case) |
| **Zeta** | Early stage, low spend, no blockers | Low risk (control case) |

### `benefit-tracker-sample.csv`
Benefit register for all 6 projects. Key items:
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
