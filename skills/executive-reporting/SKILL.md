# Executive Reporting & Artefact Generation

## Document types and when to use them

| Document | Audience | When to generate |
|----------|----------|-----------------|
| **Portfolio Dashboard** | CXO / Board | First document to generate — the single at-a-glance view |
| **Board Briefing** | Board / ExCo | Monthly or quarterly board meeting — 1 page only |
| **Steering Committee Pack** | Steering committee | Fortnightly/monthly steering — full narrative with analysis |
| **Project Status Pack** | Project sponsors | Per-project detail for sponsor 1-on-1s |
| **Benefits Report** | CFO / Value team | When tracking benefit realisation against business case |
| **Investment Summary** | CFO / Portfolio board | Portfolio rebalancing decisions — which projects to fund/cut |
| **Decision Log** | Governance / Audit | Running record of portfolio decisions and rationale |

## Charts included

All documents embed publication-quality charts automatically:

- **RAG donut** — project health distribution
- **Budget vs Spend bars** — highlights overspend in red
- **Risk heatmap** — severity × category matrix
- **Benefits waterfall** — Expected → Realised → At Risk → Adjusted
- **Benefits drift bars** — per-project with 15%/30% threshold lines
- **ROI bubble chart** — ROI vs Risk, bubble size = budget, colour = Invest/Hold/Divest
- **Portfolio dashboard composite** — 2×2 grid combining donut, budget, heatmap, drift

## Best practices

- Always run `/pmo:ingest` before generating artefacts.
- For the fullest output, ensure both project data AND benefits data are in the ingest folder.
- If the user asks for "a report" or "a briefing" without specifying type, default to `dashboard` for CXOs or `steering` for PMO leads.
- Generated files are standard DOCX/PPTX — fully editable in Word/PowerPoint/Google Docs.
