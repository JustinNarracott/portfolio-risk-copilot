"""E2E integration tests for Sprint 2: scenario pipeline (Issues #16, #17).

Tests the full pipeline: parse scenario → build graph → simulate → generate narrative.
Acceptance criteria from PID:
  - Input "cut Project Beta scope by 30%" → receive 1-page impact summary
  - Summary shows delivery date shift, dependent project delays, benefits at risk
  - Scenario run completes in <60 seconds for 10-20 projects
"""

import json
import time
from datetime import date
from pathlib import Path

import pytest

from src.ingestion.parser import parse_file
from src.scenario.graph import build_dependency_graph
from src.scenario.narrative import ScenarioNarrative, generate_narrative
from src.scenario.parser import ActionType, ScenarioAction, parse_scenario
from src.scenario.simulator import ScenarioResult, simulate

SAMPLE_CSV = Path(__file__).parent.parent.parent / "sample-data" / "jira-export-sample.csv"
REF_DATE = date(2026, 2, 19)


# ──────────────────────────────────────────────
# Narrative generator unit tests (Issue #16)
# ──────────────────────────────────────────────


class TestNarrativeGenerator:

    @pytest.fixture()
    def scope_cut_result(self) -> ScenarioResult:
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("cut Beta scope by 30%")
        return simulate(action, projects, graph, REF_DATE)

    @pytest.fixture()
    def budget_increase_result(self) -> ScenarioResult:
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("increase Gamma budget by 50%")
        return simulate(action, projects, graph, REF_DATE)

    @pytest.fixture()
    def delay_result(self) -> ScenarioResult:
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("delay Alpha by 1 quarter")
        return simulate(action, projects, graph, REF_DATE)

    @pytest.fixture()
    def remove_result(self) -> ScenarioResult:
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("remove Delta")
        return simulate(action, projects, graph, REF_DATE)

    def test_scope_cut_has_all_sections(self, scope_cut_result):
        narrative = generate_narrative(scope_cut_result)
        assert narrative.title
        assert narrative.scenario_description
        assert narrative.before_summary
        assert narrative.after_summary
        assert narrative.impact_analysis
        assert len(narrative.recommendations) >= 2

    def test_budget_increase_narrative(self, budget_increase_result):
        narrative = generate_narrative(budget_increase_result)
        assert "Gamma" in narrative.title
        assert "runway" in narrative.impact_analysis.lower()
        assert len(narrative.recommendations) >= 2

    def test_delay_narrative(self, delay_result):
        narrative = generate_narrative(delay_result)
        assert "Alpha" in narrative.title
        assert "delay" in narrative.impact_analysis.lower()

    def test_remove_narrative(self, remove_result):
        narrative = generate_narrative(remove_result)
        assert "Delta" in narrative.title
        assert "Removal" in narrative.title
        assert "benefits" in narrative.impact_analysis.lower()

    def test_full_text_renders(self, scope_cut_result):
        narrative = generate_narrative(scope_cut_result)
        text = narrative.full_text
        assert "# Scenario Impact Summary" in text
        assert "## Before" in text
        assert "## After" in text
        assert "## Impact Analysis" in text
        assert "## Recommended Actions" in text

    def test_narrative_to_dict(self, scope_cut_result):
        narrative = generate_narrative(scope_cut_result)
        d = narrative.to_dict()
        assert "title" in d
        assert "full_text" in d
        assert "recommendations" in d

    def test_narrative_cxo_language(self, scope_cut_result):
        """Narrative should be CXO-level — no code, no jargon."""
        narrative = generate_narrative(scope_cut_result)
        text = narrative.full_text
        assert "def " not in text
        assert "import " not in text
        # Should contain business language
        assert any(word in text.lower() for word in ["delivery", "stakeholder", "budget", "scope"])


# ──────────────────────────────────────────────
# Full E2E pipeline (Issue #17)
# ──────────────────────────────────────────────


class TestEndToEndScenarioPipeline:

    def test_scope_cut_full_pipeline(self):
        """PID acceptance: 'cut Project Beta scope by 30%' → impact summary."""
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("cut Beta scope by 30%")
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)

        # Should have impact summary
        assert narrative.title
        assert "scope" in narrative.impact_analysis.lower()
        assert "days" in narrative.impact_analysis.lower()
        assert len(narrative.recommendations) >= 2

    def test_budget_increase_full_pipeline(self):
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("increase Gamma budget by 50%")
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)
        assert "Gamma" in narrative.title

    def test_delay_full_pipeline(self):
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("delay Alpha by 1 quarter")
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)
        assert "Alpha" in narrative.title

    def test_remove_full_pipeline(self):
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("remove Delta")
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)
        assert "Removal" in narrative.title

    def test_completes_under_60_seconds(self):
        """PID acceptance: scenario run completes in <60 seconds."""
        start = time.time()

        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)

        # Run multiple scenarios
        scenarios = [
            "cut Beta scope by 30%",
            "increase Gamma budget by 50%",
            "delay Alpha by 1 quarter",
            "remove Delta",
            "decrease Epsilon budget by 20%",
        ]
        for text in scenarios:
            action = parse_scenario(text)
            result = simulate(action, projects, graph, REF_DATE)
            narrative = generate_narrative(result)
            assert narrative.title

        elapsed = time.time() - start
        assert elapsed < 60.0, f"Pipeline took {elapsed:.2f}s (limit: 60s)"

    def test_full_pipeline_json_serialisable(self):
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = parse_scenario("cut Beta scope by 30%")
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)

        # Both result and narrative should serialise
        json_str = json.dumps({
            "result": result.to_dict(),
            "narrative": narrative.to_dict(),
        })
        parsed = json.loads(json_str)
        assert "result" in parsed
        assert "narrative" in parsed

    def test_unknown_project_handled_gracefully(self):
        projects = parse_file(SAMPLE_CSV)
        graph = build_dependency_graph(projects)
        action = ScenarioAction(action=ActionType.REMOVE, project="NonExistent")
        result = simulate(action, projects, graph, REF_DATE)
        narrative = generate_narrative(result)
        # Should still produce a narrative, with warnings
        assert any("not found" in w.lower() for w in result.warnings)
