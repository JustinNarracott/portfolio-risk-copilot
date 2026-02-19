"""
Scenario simulators.

Applies scenario actions to project data and calculates impact.
Supports budget changes, scope cuts, delays, and project removal.

Sprint 2 — Week 5 deliverable.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta

from src.ingestion.parser import Project
from src.scenario.graph import DependencyGraph
from src.scenario.parser import ActionType, ScenarioAction


@dataclass
class ProjectImpact:
    """Impact of a scenario on a single project."""

    project_name: str
    impact_type: str          # "direct" or "cascade"
    changes: dict[str, str] = field(default_factory=dict)  # field → "before → after" description

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "impact_type": self.impact_type,
            "changes": self.changes,
        }


@dataclass
class ScenarioResult:
    """Full result of running a scenario simulation."""

    action: ScenarioAction
    before_state: dict[str, dict] = field(default_factory=dict)  # project → snapshot
    after_state: dict[str, dict] = field(default_factory=dict)
    impacts: list[ProjectImpact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": {
                "type": self.action.action.value,
                "project": self.action.project,
                "description": self.action.description,
            },
            "before_state": self.before_state,
            "after_state": self.after_state,
            "impacts": [i.to_dict() for i in self.impacts],
            "warnings": self.warnings,
        }


def simulate(
    action: ScenarioAction,
    projects: list[Project],
    graph: DependencyGraph,
    reference_date: date | None = None,
) -> ScenarioResult:
    """Run a scenario simulation and return the impact.

    Args:
        action: Parsed scenario action.
        projects: List of current project data.
        graph: Dependency graph between projects.
        reference_date: Date for calculations (defaults to today).

    Returns:
        ScenarioResult with before/after states and impacts.
    """
    if reference_date is None:
        reference_date = date.today()

    # Find the target project
    project_map = {p.name: p for p in projects}
    target_name = _resolve_project_name(action.project, project_map)

    if target_name is None:
        result = ScenarioResult(action=action)
        result.warnings.append(
            f"Project '{action.project}' not found in portfolio. "
            f"Available projects: {', '.join(sorted(project_map.keys()))}"
        )
        return result

    # Snapshot before state
    before = {p.name: _snapshot(p) for p in projects}

    # Apply the scenario
    if action.action == ActionType.REMOVE:
        return _simulate_remove(action, target_name, projects, graph, before)
    elif action.action in (ActionType.BUDGET_INCREASE, ActionType.BUDGET_DECREASE):
        return _simulate_budget(action, target_name, project_map, graph, before, reference_date)
    elif action.action == ActionType.SCOPE_CUT:
        return _simulate_scope_cut(action, target_name, project_map, graph, before)
    elif action.action == ActionType.DELAY:
        return _simulate_delay(action, target_name, project_map, graph, before)
    else:
        result = ScenarioResult(action=action, before_state=before)
        result.warnings.append(f"Unsupported action type: {action.action}")
        return result


# ──────────────────────────────────────────────
# Simulators
# ──────────────────────────────────────────────


def _simulate_budget(
    action: ScenarioAction,
    target_name: str,
    project_map: dict[str, Project],
    graph: DependencyGraph,
    before: dict[str, dict],
    reference_date: date,
) -> ScenarioResult:
    """Simulate a budget increase or decrease."""
    project = project_map[target_name]
    old_budget = project.budget

    if action.amount_absolute > 0:
        change_amount = action.amount_absolute
    else:
        change_amount = old_budget * action.amount

    if action.action == ActionType.BUDGET_INCREASE:
        new_budget = old_budget + change_amount
    else:
        new_budget = max(0, old_budget - change_amount)

    # Calculate runway impact
    old_runway = _calc_runway_weeks(project, reference_date)
    new_runway = _calc_runway_weeks_with_budget(project, new_budget, reference_date)

    impacts = [ProjectImpact(
        project_name=target_name,
        impact_type="direct",
        changes={
            "budget": f"{old_budget:,.0f} → {new_budget:,.0f}",
            "runway_weeks": f"{old_runway} → {new_runway}",
        },
    )]

    # Build after state
    after = copy.deepcopy(before)
    after[target_name]["budget"] = new_budget
    after[target_name]["runway_weeks"] = new_runway

    result = ScenarioResult(
        action=action,
        before_state=before,
        after_state=after,
        impacts=impacts,
    )

    # Warnings
    if new_budget < project.actual_spend:
        result.warnings.append(
            f"New budget ({new_budget:,.0f}) is below actual spend "
            f"({project.actual_spend:,.0f}) — project is already over budget."
        )

    if action.action == ActionType.BUDGET_DECREASE and new_runway is not None and old_runway is not None:
        if new_runway < old_runway:
            result.warnings.append(
                f"Budget decrease reduces runway from {old_runway} to {new_runway} weeks."
            )

    return result


def _simulate_scope_cut(
    action: ScenarioAction,
    target_name: str,
    project_map: dict[str, Project],
    graph: DependencyGraph,
    before: dict[str, dict],
) -> ScenarioResult:
    """Simulate a scope reduction."""
    project = project_map[target_name]
    cut_pct = action.amount

    # Linear model: scope cut → proportional delivery date shift
    old_end = project.end_date
    new_end = None
    days_saved = 0

    if project.start_date and project.end_date:
        total_days = (project.end_date - project.start_date).days
        days_saved = int(total_days * cut_pct)
        new_end = project.end_date - timedelta(days=days_saved)

    impacts = [ProjectImpact(
        project_name=target_name,
        impact_type="direct",
        changes={
            "scope": f"100% → {(1 - cut_pct) * 100:.0f}%",
            "end_date": f"{_fmt_date(old_end)} → {_fmt_date(new_end)}",
            "days_saved": str(days_saved),
        },
    )]

    # Cascade: dependent projects may benefit from earlier delivery
    dependents = graph.get_all_dependents(target_name)
    for dep_name in sorted(dependents):
        impacts.append(ProjectImpact(
            project_name=dep_name,
            impact_type="cascade",
            changes={
                "note": f"Dependency on {target_name} delivers {days_saved} days earlier.",
            },
        ))

    # Build after state
    after = copy.deepcopy(before)
    after[target_name]["scope_pct"] = (1 - cut_pct) * 100
    if new_end:
        after[target_name]["end_date"] = new_end.isoformat()

    return ScenarioResult(
        action=action,
        before_state=before,
        after_state=after,
        impacts=impacts,
    )


def _simulate_delay(
    action: ScenarioAction,
    target_name: str,
    project_map: dict[str, Project],
    graph: DependencyGraph,
    before: dict[str, dict],
) -> ScenarioResult:
    """Simulate a project delay."""
    project = project_map[target_name]
    delay_days = action.duration_weeks * 7

    old_end = project.end_date
    new_end = None
    if project.end_date:
        new_end = project.end_date + timedelta(days=delay_days)

    old_start = project.start_date
    new_start = None
    if project.start_date:
        new_start = project.start_date + timedelta(days=delay_days)

    impacts = [ProjectImpact(
        project_name=target_name,
        impact_type="direct",
        changes={
            "start_date": f"{_fmt_date(old_start)} → {_fmt_date(new_start)}",
            "end_date": f"{_fmt_date(old_end)} → {_fmt_date(new_end)}",
            "delay_weeks": str(action.duration_weeks),
        },
    )]

    # Cascade delays on dependent projects
    dependents = graph.get_all_dependents(target_name)
    for dep_name in sorted(dependents):
        dep_project = project_map.get(dep_name)
        if dep_project:
            dep_old_end = dep_project.end_date
            dep_new_end = dep_old_end + timedelta(days=delay_days) if dep_old_end else None
            impacts.append(ProjectImpact(
                project_name=dep_name,
                impact_type="cascade",
                changes={
                    "end_date": f"{_fmt_date(dep_old_end)} → {_fmt_date(dep_new_end)}",
                    "delay_weeks": str(action.duration_weeks),
                    "reason": f"Cascade delay from {target_name}",
                },
            ))

    # Build after state
    after = copy.deepcopy(before)
    if new_end:
        after[target_name]["end_date"] = new_end.isoformat()
    if new_start:
        after[target_name]["start_date"] = new_start.isoformat()
    for dep_name in dependents:
        dep = project_map.get(dep_name)
        if dep and dep.end_date:
            after[dep_name]["end_date"] = (dep.end_date + timedelta(days=delay_days)).isoformat()

    result = ScenarioResult(
        action=action,
        before_state=before,
        after_state=after,
        impacts=impacts,
    )

    if dependents:
        result.warnings.append(
            f"Delay on {target_name} cascades to {len(dependents)} dependent "
            f"project{'s' if len(dependents) > 1 else ''}: {', '.join(sorted(dependents))}."
        )

    return result


def _simulate_remove(
    action: ScenarioAction,
    target_name: str,
    projects: list[Project],
    graph: DependencyGraph,
    before: dict[str, dict],
) -> ScenarioResult:
    """Simulate removing a project from the portfolio."""
    project_map = {p.name: p for p in projects}
    project = project_map[target_name]

    impacts = [ProjectImpact(
        project_name=target_name,
        impact_type="direct",
        changes={
            "status": f"{project.status} → Removed",
            "budget_freed": f"{project.budget:,.0f}",
            "remaining_budget": f"{max(0, project.budget - project.actual_spend):,.0f}",
        },
    )]

    # Flag dependent projects that lose a dependency
    dependents = graph.get_dependents(target_name)
    for dep_name in sorted(dependents):
        impacts.append(ProjectImpact(
            project_name=dep_name,
            impact_type="cascade",
            changes={
                "note": f"Dependency on {target_name} is broken — project may need re-planning.",
            },
        ))

    # Build after state (remove target)
    after = copy.deepcopy(before)
    after[target_name]["status"] = "Removed"

    result = ScenarioResult(
        action=action,
        before_state=before,
        after_state=after,
        impacts=impacts,
    )

    if dependents:
        result.warnings.append(
            f"Removing {target_name} breaks dependencies for: {', '.join(sorted(dependents))}. "
            f"These projects may need re-scoping or alternative delivery paths."
        )

    return result


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _snapshot(project: Project) -> dict:
    """Capture current project state as a dict."""
    return {
        "name": project.name,
        "status": project.status,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "budget": project.budget,
        "actual_spend": project.actual_spend,
        "scope_pct": 100.0,
        "task_count": len(project.tasks),
    }


def _calc_runway_weeks(project: Project, ref_date: date) -> int | None:
    """Calculate remaining runway in weeks based on current burn rate."""
    if project.budget <= 0 or project.actual_spend <= 0:
        return None
    if project.start_date is None:
        return None

    elapsed_days = max(1, (ref_date - project.start_date).days)
    daily_burn = project.actual_spend / elapsed_days
    remaining_budget = project.budget - project.actual_spend

    if daily_burn <= 0 or remaining_budget <= 0:
        return 0

    remaining_days = remaining_budget / daily_burn
    return int(remaining_days / 7)


def _calc_runway_weeks_with_budget(project: Project, new_budget: float, ref_date: date) -> int | None:
    """Calculate runway with a modified budget."""
    if new_budget <= 0 or project.actual_spend <= 0:
        return None
    if project.start_date is None:
        return None

    elapsed_days = max(1, (ref_date - project.start_date).days)
    daily_burn = project.actual_spend / elapsed_days
    remaining_budget = new_budget - project.actual_spend

    if daily_burn <= 0 or remaining_budget <= 0:
        return 0

    remaining_days = remaining_budget / daily_burn
    return int(remaining_days / 7)


def _resolve_project_name(name: str, project_map: dict[str, Project]) -> str | None:
    """Resolve a project name (case-insensitive)."""
    if name in project_map:
        return name

    name_lower = name.lower()
    for pname in project_map:
        if pname.lower() == name_lower:
            return pname

    return None


def _fmt_date(d: date | None) -> str:
    return d.isoformat() if d else "N/A"
