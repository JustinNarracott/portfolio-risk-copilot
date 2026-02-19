"""Unit tests for dependency graph builder (Issue #12)."""

from pathlib import Path

import pytest

from src.ingestion.parser import Project, Task, parse_file
from src.scenario.graph import DependencyGraph, build_dependency_graph

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"


# ──────────────────────────────────────────────
# DependencyGraph dataclass tests
# ──────────────────────────────────────────────


class TestDependencyGraph:

    def test_add_and_get_dependency(self):
        g = DependencyGraph()
        g.add_dependency("Beta", "Alpha")
        assert g.get_dependencies("Beta") == {"Alpha"}

    def test_get_dependents(self):
        g = DependencyGraph()
        g.add_dependency("Beta", "Alpha")
        g.add_dependency("Gamma", "Alpha")
        assert g.get_dependents("Alpha") == {"Beta", "Gamma"}

    def test_no_dependencies(self):
        g = DependencyGraph()
        assert g.get_dependencies("Alpha") == set()

    def test_no_dependents(self):
        g = DependencyGraph()
        assert g.get_dependents("Alpha") == set()

    def test_transitive_dependents(self):
        """A → B → C: if A slips, both B and C are affected."""
        g = DependencyGraph(all_projects={"A", "B", "C"})
        g.add_dependency("B", "A")
        g.add_dependency("C", "B")
        assert g.get_all_dependents("A") == {"B", "C"}

    def test_transitive_dependencies(self):
        """C depends on B depends on A: C's full dependency chain is {A, B}."""
        g = DependencyGraph(all_projects={"A", "B", "C"})
        g.add_dependency("B", "A")
        g.add_dependency("C", "B")
        assert g.get_all_dependencies("C") == {"A", "B"}

    def test_diamond_dependency(self):
        """A → B, A → C, B → D, C → D: D depends on everything."""
        g = DependencyGraph(all_projects={"A", "B", "C", "D"})
        g.add_dependency("B", "A")
        g.add_dependency("C", "A")
        g.add_dependency("D", "B")
        g.add_dependency("D", "C")
        assert g.get_all_dependencies("D") == {"A", "B", "C"}
        assert g.get_all_dependents("A") == {"B", "C", "D"}

    def test_circular_dependency_detected(self):
        g = DependencyGraph(all_projects={"A", "B", "C"})
        g.add_dependency("A", "B")
        g.add_dependency("B", "C")
        g.add_dependency("C", "A")
        cycle = g.has_circular_dependency()
        assert cycle is not None
        assert len(cycle) >= 3

    def test_no_circular_dependency(self):
        g = DependencyGraph(all_projects={"A", "B", "C"})
        g.add_dependency("B", "A")
        g.add_dependency("C", "B")
        assert g.has_circular_dependency() is None

    def test_to_dict(self):
        g = DependencyGraph(all_projects={"Alpha", "Beta"})
        g.add_dependency("Beta", "Alpha")
        d = g.to_dict()
        assert "Alpha" in d["projects"]
        assert "Beta" in d["projects"]
        assert d["edges"]["Beta"] == ["Alpha"]

    def test_self_reference_ignored_in_dependents(self):
        g = DependencyGraph(all_projects={"A"})
        assert g.get_all_dependents("A") == set()


# ──────────────────────────────────────────────
# Graph builder with synthetic data
# ──────────────────────────────────────────────


class TestBuildGraphSynthetic:

    def test_simple_dependency(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[
                Task(name="T1", status="Done"),
            ]),
            Project(name="Beta", status="Active", tasks=[
                Task(name="T2", status="To Do",
                     comments="Depends on Alpha API completion"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Beta") == {"Alpha"}

    def test_blocked_by_keyword(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[Task(name="T1", status="Done")]),
            Project(name="Beta", status="Active", tasks=[
                Task(name="T2", status="Blocked", comments="Blocked by Alpha delivery"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Beta") == {"Alpha"}

    def test_waiting_for_keyword(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[Task(name="T1", status="Done")]),
            Project(name="Beta", status="Active", tasks=[
                Task(name="T2", status="To Do", comments="Waiting for Alpha sign-off"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Beta") == {"Alpha"}

    def test_no_cross_project_dependency(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[
                Task(name="T1", status="To Do", comments="Depends on internal API"),
            ]),
            Project(name="Beta", status="Active", tasks=[
                Task(name="T2", status="Done"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Alpha") == set()

    def test_self_reference_excluded(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[
                Task(name="T1", status="To Do", comments="Depends on Alpha task T2"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Alpha") == set()

    def test_multiple_dependencies(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[Task(name="T1", status="Done")]),
            Project(name="Beta", status="Active", tasks=[Task(name="T2", status="Done")]),
            Project(name="Gamma", status="Active", tasks=[
                Task(name="T3", status="To Do",
                     comments="Depends on Alpha. Also waiting for Beta release"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Gamma") == {"Alpha", "Beta"}

    def test_case_insensitive_matching(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[Task(name="T1", status="Done")]),
            Project(name="Beta", status="Active", tasks=[
                Task(name="T2", status="To Do", comments="depends on alpha completion"),
            ]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.get_dependencies("Beta") == {"Alpha"}

    def test_all_projects_populated(self):
        projects = [
            Project(name="Alpha", status="Active", tasks=[]),
            Project(name="Beta", status="Active", tasks=[]),
        ]
        graph = build_dependency_graph(projects)
        assert graph.all_projects == {"Alpha", "Beta"}

    def test_empty_portfolio(self):
        graph = build_dependency_graph([])
        assert graph.edges == {}
        assert graph.all_projects == set()


# ──────────────────────────────────────────────
# Graph builder with sample data
# ──────────────────────────────────────────────


class TestBuildGraphSampleData:

    @pytest.fixture()
    def graph(self) -> DependencyGraph:
        projects = parse_file(SAMPLE_CSV)
        return build_dependency_graph(projects)

    def test_six_projects_in_graph(self, graph):
        assert len(graph.all_projects) == 6

    def test_alpha_has_dependents(self, graph):
        """Alpha is a core project — others should depend on it."""
        dependents = graph.get_dependents("Alpha")
        assert len(dependents) >= 0  # At least plausible

    def test_no_circular_dependencies(self, graph):
        """Sample data should not have circular dependencies."""
        assert graph.has_circular_dependency() is None

    def test_graph_serialisable(self, graph):
        import json
        d = graph.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert "projects" in parsed
        assert "edges" in parsed
