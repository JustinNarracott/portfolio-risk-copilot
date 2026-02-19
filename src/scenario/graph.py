"""
Dependency graph builder.

Extracts inter-project dependency relationships from task comments
and builds a directed graph for scenario impact analysis.

Sprint 2 — Week 4 deliverable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.ingestion.parser import Project


# Keywords that indicate a cross-project dependency
CROSS_PROJECT_KEYWORDS = [
    "depends on",
    "dependent on",
    "blocked by",
    "waiting for",
    "waiting on",
    "requires",
    "contingent on",
    "prerequisite",
]


@dataclass
class DependencyGraph:
    """Directed dependency graph between projects.

    edges: dict mapping project name → set of project names it depends on.
    E.g., {"Beta": {"Alpha"}} means Beta depends on Alpha.
    """

    edges: dict[str, set[str]] = field(default_factory=dict)
    all_projects: set[str] = field(default_factory=set)

    def add_dependency(self, project: str, depends_on: str) -> None:
        """Add a dependency: 'project' depends on 'depends_on'."""
        if project not in self.edges:
            self.edges[project] = set()
        self.edges[project].add(depends_on)

    def get_dependencies(self, project: str) -> set[str]:
        """Get direct dependencies of a project."""
        return self.edges.get(project, set())

    def get_dependents(self, project: str) -> set[str]:
        """Get projects that depend on the given project (reverse lookup)."""
        dependents = set()
        for proj, deps in self.edges.items():
            if project in deps:
                dependents.add(proj)
        return dependents

    def get_all_dependents(self, project: str) -> set[str]:
        """Get all projects that depend on the given project (transitive, downstream).

        Returns all projects that would be affected if this project slips.
        """
        visited: set[str] = set()
        queue = [project]
        while queue:
            current = queue.pop(0)
            for proj, deps in self.edges.items():
                if current in deps and proj not in visited:
                    visited.add(proj)
                    queue.append(proj)
        return visited

    def get_all_dependencies(self, project: str) -> set[str]:
        """Get all projects that the given project depends on (transitive, upstream)."""
        visited: set[str] = set()
        queue = list(self.get_dependencies(project))
        while queue:
            current = queue.pop(0)
            if current not in visited:
                visited.add(current)
                queue.extend(self.get_dependencies(current) - visited)
        return visited

    def has_circular_dependency(self) -> list[str] | None:
        """Detect circular dependencies using DFS.

        Returns:
            A list of project names forming a cycle, or None if no cycle found.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        colour: dict[str, int] = {p: WHITE for p in self.all_projects}
        parent: dict[str, str | None] = {p: None for p in self.all_projects}

        def dfs(node: str) -> list[str] | None:
            colour[node] = GRAY
            for dep in self.edges.get(node, set()):
                if dep not in colour:
                    continue
                if colour[dep] == GRAY:
                    # Found cycle — reconstruct path
                    cycle = [dep, node]
                    current = node
                    while parent.get(current) and parent[current] != dep:
                        current = parent[current]
                        cycle.append(current)
                    cycle.append(dep)
                    return list(reversed(cycle))
                if colour[dep] == WHITE:
                    parent[dep] = node
                    result = dfs(dep)
                    if result:
                        return result
            colour[node] = BLACK
            return None

        for project in self.all_projects:
            if colour.get(project, WHITE) == WHITE:
                result = dfs(project)
                if result:
                    return result
        return None

    def to_dict(self) -> dict:
        """Serialise for JSON output."""
        return {
            "projects": sorted(self.all_projects),
            "edges": {k: sorted(v) for k, v in sorted(self.edges.items())},
        }


def build_dependency_graph(projects: list[Project]) -> DependencyGraph:
    """Build a dependency graph from project data.

    Scans task comments for cross-project dependency keywords and
    matches them against known project names.

    Args:
        projects: List of parsed Project objects.

    Returns:
        DependencyGraph with edges representing inter-project dependencies.
    """
    graph = DependencyGraph()
    project_names = {p.name for p in projects}
    graph.all_projects = project_names

    # Build name lookup for case-insensitive matching
    name_lookup = {name.lower(): name for name in project_names}

    for project in projects:
        for task in project.tasks:
            if not task.comments:
                continue

            # Find cross-project dependency mentions
            mentioned = _find_project_mentions(task.comments, name_lookup, project.name)
            for dep_name in mentioned:
                graph.add_dependency(project.name, dep_name)

    return graph


def _find_project_mentions(
    comments: str,
    name_lookup: dict[str, str],
    current_project: str,
) -> set[str]:
    """Find other project names mentioned after dependency keywords in comments.

    Returns:
        Set of project names that this task depends on.
    """
    mentioned: set[str] = set()
    comments_lower = comments.lower()

    for keyword in CROSS_PROJECT_KEYWORDS:
        pos = 0
        while True:
            pos = comments_lower.find(keyword, pos)
            if pos == -1:
                break

            # Extract text after the keyword (up to sentence boundary)
            after = comments[pos + len(keyword):].strip()
            after = after.lstrip(":- ")

            # Look for a project name in the text after the keyword
            after_lower = after.lower()
            for name_lower, name_original in name_lookup.items():
                if name_original == current_project:
                    continue  # Skip self-references

                # Check if project name appears near the keyword
                name_pos = after_lower.find(name_lower)
                if name_pos != -1 and name_pos < 80:  # Within reasonable distance
                    mentioned.add(name_original)

            pos += len(keyword)

    return mentioned
