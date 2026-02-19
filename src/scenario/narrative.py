"""
Scenario narrative generator.

Produces a plain-English, CXO-level summary of a scenario simulation result.
Output is structured as a 1-page impact briefing with before/after comparison
and recommended actions.

Sprint 2 — Week 6 deliverable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.scenario.parser import ActionType, ScenarioAction
from src.scenario.simulator import ScenarioResult, ProjectImpact


@dataclass
class ScenarioNarrative:
    """Structured narrative for a scenario impact summary."""

    title: str = ""
    scenario_description: str = ""
    before_summary: str = ""
    after_summary: str = ""
    impact_analysis: str = ""
    cascade_analysis: str = ""
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Render the full narrative as plain text."""
        sections = [
            f"# Scenario Impact Summary\n",
            f"## Scenario\n{self.scenario_description}\n",
            f"## Before\n{self.before_summary}\n",
            f"## After\n{self.after_summary}\n",
            f"## Impact Analysis\n{self.impact_analysis}\n",
        ]
        if self.cascade_analysis:
            sections.append(f"## Cascade Effects\n{self.cascade_analysis}\n")
        if self.recommendations:
            rec_text = "\n".join(f"- {r}" for r in self.recommendations)
            sections.append(f"## Recommended Actions\n{rec_text}\n")
        if self.warnings:
            warn_text = "\n".join(f"- {w}" for w in self.warnings)
            sections.append(f"## Warnings\n{warn_text}\n")
        return "\n".join(sections)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "scenario_description": self.scenario_description,
            "before_summary": self.before_summary,
            "after_summary": self.after_summary,
            "impact_analysis": self.impact_analysis,
            "cascade_analysis": self.cascade_analysis,
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "full_text": self.full_text,
        }


def generate_narrative(result: ScenarioResult) -> ScenarioNarrative:
    """Generate a plain-English narrative from a scenario simulation result.

    Args:
        result: Output from simulate().

    Returns:
        ScenarioNarrative with structured sections.
    """
    action = result.action
    narrative = ScenarioNarrative()

    # Title
    narrative.title = _build_title(action)
    narrative.scenario_description = _build_description(action)

    # Before/after summaries
    direct_impacts = [i for i in result.impacts if i.impact_type == "direct"]
    cascade_impacts = [i for i in result.impacts if i.impact_type == "cascade"]

    narrative.before_summary = _build_before_summary(action, result.before_state)
    narrative.after_summary = _build_after_summary(action, direct_impacts, result.after_state)
    narrative.impact_analysis = _build_impact_analysis(action, direct_impacts)

    if cascade_impacts:
        narrative.cascade_analysis = _build_cascade_analysis(action, cascade_impacts)

    narrative.recommendations = _build_recommendations(action, result)
    narrative.warnings = result.warnings

    return narrative


# ──────────────────────────────────────────────
# Section builders
# ──────────────────────────────────────────────


def _build_title(action: ScenarioAction) -> str:
    labels = {
        ActionType.BUDGET_INCREASE: f"Budget Increase: {action.project}",
        ActionType.BUDGET_DECREASE: f"Budget Decrease: {action.project}",
        ActionType.SCOPE_CUT: f"Scope Reduction: {action.project}",
        ActionType.DELAY: f"Schedule Delay: {action.project}",
        ActionType.REMOVE: f"Project Removal: {action.project}",
    }
    return labels.get(action.action, f"Scenario: {action.project}")


def _build_description(action: ScenarioAction) -> str:
    if action.description:
        return action.description

    descs = {
        ActionType.BUDGET_INCREASE: f"Increase {action.project} budget by {action.amount:.0%}" if action.amount else f"Increase {action.project} budget by {action.amount_absolute:,.0f}",
        ActionType.BUDGET_DECREASE: f"Decrease {action.project} budget by {action.amount:.0%}" if action.amount else f"Decrease {action.project} budget by {action.amount_absolute:,.0f}",
        ActionType.SCOPE_CUT: f"Cut {action.project} scope by {action.amount:.0%}",
        ActionType.DELAY: f"Delay {action.project} by {action.duration_weeks} weeks",
        ActionType.REMOVE: f"Remove {action.project} from portfolio",
    }
    return descs.get(action.action, str(action))


def _build_before_summary(action: ScenarioAction, before: dict[str, dict]) -> str:
    project = action.project
    state = before.get(project, {})
    if not state:
        return f"{project}: No data available."

    parts = [f"{project} is currently {state.get('status', 'unknown status')}."]

    budget = state.get("budget", 0)
    spend = state.get("actual_spend", 0)
    if budget > 0:
        pct = (spend / budget) * 100
        parts.append(f"Budget: {budget:,.0f} ({pct:.0f}% consumed, {spend:,.0f} spent).")

    start = state.get("start_date")
    end = state.get("end_date")
    if start and end:
        parts.append(f"Timeline: {start} to {end}.")

    tasks = state.get("task_count", 0)
    if tasks > 0:
        parts.append(f"{tasks} tasks in progress.")

    return " ".join(parts)


def _build_after_summary(
    action: ScenarioAction,
    direct_impacts: list[ProjectImpact],
    after: dict[str, dict],
) -> str:
    if not direct_impacts:
        return "No direct impact identified."

    impact = direct_impacts[0]
    parts = []

    for field_name, change_desc in impact.changes.items():
        label = field_name.replace("_", " ").title()
        parts.append(f"{label}: {change_desc}.")

    return " ".join(parts)


def _build_impact_analysis(action: ScenarioAction, direct_impacts: list[ProjectImpact]) -> str:
    if not direct_impacts:
        return "No measurable impact."

    impact = direct_impacts[0]
    project = impact.project_name

    if action.action == ActionType.BUDGET_INCREASE:
        return (
            f"Increasing the budget for {project} extends the financial runway, "
            f"reducing the risk of budget exhaustion before delivery. "
            f"This may allow the team to address scope or resource constraints "
            f"that are currently limiting progress."
        )
    elif action.action == ActionType.BUDGET_DECREASE:
        return (
            f"Decreasing the budget for {project} shortens the financial runway. "
            f"The team may need to reduce scope or find efficiencies to deliver "
            f"within the revised budget. Review whether current commitments "
            f"are achievable with reduced funding."
        )
    elif action.action == ActionType.SCOPE_CUT:
        days = impact.changes.get("days_saved", "0")
        return (
            f"Reducing scope on {project} by {action.amount:.0%} "
            f"is estimated to save {days} days on the delivery timeline. "
            f"This trades feature completeness for earlier delivery. "
            f"Review which deliverables are deferred and whether benefits "
            f"targets are still achievable with reduced scope."
        )
    elif action.action == ActionType.DELAY:
        weeks = action.duration_weeks
        return (
            f"Delaying {project} by {weeks} week{'s' if weeks > 1 else ''} "
            f"shifts the delivery window forward. "
            f"This may impact dependent projects and downstream milestones. "
            f"Benefits realisation will be correspondingly delayed."
        )
    elif action.action == ActionType.REMOVE:
        return (
            f"Removing {project} from the portfolio frees up budget and resources. "
            f"However, any projects dependent on {project} will need "
            f"re-planning or alternative delivery paths. "
            f"Expected benefits from {project} will not be realised."
        )

    return "Impact analysis not available for this scenario type."


def _build_cascade_analysis(action: ScenarioAction, cascade_impacts: list[ProjectImpact]) -> str:
    parts = [f"{len(cascade_impacts)} downstream project{'s' if len(cascade_impacts) > 1 else ''} affected:"]

    for impact in cascade_impacts:
        note = impact.changes.get("note", "")
        reason = impact.changes.get("reason", "")
        delay = impact.changes.get("delay_weeks", "")
        end = impact.changes.get("end_date", "")

        desc = f"**{impact.project_name}**: "
        if delay:
            desc += f"Delayed by {delay} weeks. "
        if end:
            desc += f"New end date: {end.split(' → ')[-1] if ' → ' in end else end}. "
        if reason:
            desc += reason + ". "
        if note:
            desc += note
        parts.append(desc.strip())

    return "\n".join(parts)


def _build_recommendations(action: ScenarioAction, result: ScenarioResult) -> list[str]:
    recs: list[str] = []
    project = action.project
    cascade_count = sum(1 for i in result.impacts if i.impact_type == "cascade")

    if action.action == ActionType.BUDGET_INCREASE:
        recs.append(f"Approve the budget increase for {project} and communicate the revised allocation to the delivery team.")
        recs.append(f"Set a checkpoint in 4 weeks to verify the additional funding is translating into accelerated delivery.")

    elif action.action == ActionType.BUDGET_DECREASE:
        recs.append(f"Confirm the revised budget with the {project} delivery team and agree scope trade-offs.")
        recs.append(f"Identify which deliverables can be deferred to Phase 2 to fit within the reduced budget.")
        if any("over budget" in w.lower() for w in result.warnings):
            recs.append(f"URGENT: {project} is already over budget — immediate intervention required.")

    elif action.action == ActionType.SCOPE_CUT:
        recs.append(f"Agree the deferred scope items with the {project} sponsor and update the benefits register.")
        recs.append(f"Communicate the revised delivery date to stakeholders.")
        if cascade_count > 0:
            recs.append(f"Notify the {cascade_count} dependent project{'s' if cascade_count > 1 else ''} of the earlier delivery window.")

    elif action.action == ActionType.DELAY:
        recs.append(f"Communicate the revised timeline for {project} to all stakeholders.")
        if cascade_count > 0:
            recs.append(f"Assess the cascade impact on {cascade_count} dependent project{'s' if cascade_count > 1 else ''} and update their timelines.")
        recs.append(f"Review whether the delay changes the cost profile (extended team costs, contract implications).")

    elif action.action == ActionType.REMOVE:
        recs.append(f"Formally close {project} and release resources back to the portfolio.")
        recs.append(f"Update the benefits register to remove {project}'s expected benefits.")
        if cascade_count > 0:
            recs.append(f"Urgently re-plan the {cascade_count} project{'s' if cascade_count > 1 else ''} that depend on {project}.")

    return recs
