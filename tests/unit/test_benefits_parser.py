"""Unit tests for benefits register parser (Issue #29)."""

from datetime import date
from pathlib import Path

import pytest

from src.benefits.parser import (
    Benefit, BenefitCategory, BenefitConfidence, BenefitStatus, parse_benefits,
)

SAMPLE = Path(__file__).parent.parent.parent / "sample-data" / "benefit-tracker-sample.csv"


class TestParseBenefits:

    def test_parses_sample_file(self):
        benefits = parse_benefits(SAMPLE)
        assert len(benefits) == 6

    def test_projects_linked(self):
        benefits = parse_benefits(SAMPLE)
        projects = {b.project_name for b in benefits}
        assert "Alpha" in projects
        assert "Gamma" in projects

    def test_expected_values_parsed(self):
        benefits = parse_benefits(SAMPLE)
        alpha = [b for b in benefits if b.project_name == "Alpha"][0]
        assert alpha.expected_value == 500000

    def test_realised_values_parsed(self):
        benefits = parse_benefits(SAMPLE)
        gamma = [b for b in benefits if b.project_name == "Gamma"][0]
        assert gamma.realised_value == 150000

    def test_status_mapped(self):
        benefits = parse_benefits(SAMPLE)
        gamma = [b for b in benefits if b.project_name == "Gamma"][0]
        assert gamma.status == BenefitStatus.PARTIAL

    def test_category_mapped(self):
        benefits = parse_benefits(SAMPLE)
        alpha = [b for b in benefits if b.project_name == "Alpha"][0]
        assert alpha.category == BenefitCategory.REVENUE

    def test_target_date_parsed(self):
        benefits = parse_benefits(SAMPLE)
        alpha = [b for b in benefits if b.project_name == "Alpha"][0]
        assert alpha.target_date == date(2026, 9, 30)

    def test_owner_parsed(self):
        benefits = parse_benefits(SAMPLE)
        alpha = [b for b in benefits if b.project_name == "Alpha"][0]
        assert alpha.owner == "Alice Chen"

    def test_notes_parsed(self):
        benefits = parse_benefits(SAMPLE)
        alpha = [b for b in benefits if b.project_name == "Alpha"][0]
        assert "Q2 launch" in alpha.notes

    def test_realisation_pct(self):
        benefits = parse_benefits(SAMPLE)
        gamma = [b for b in benefits if b.project_name == "Gamma"][0]
        assert gamma.realisation_pct == pytest.approx(0.5, abs=0.01)

    def test_zero_expected_realisation_pct(self):
        benefits = parse_benefits(SAMPLE)
        epsilon = [b for b in benefits if b.project_name == "Epsilon"][0]
        assert epsilon.realisation_pct == 0.0

    def test_unrealised_value(self):
        benefits = parse_benefits(SAMPLE)
        gamma = [b for b in benefits if b.project_name == "Gamma"][0]
        assert gamma.unrealised_value == 150000

    def test_is_at_risk(self):
        benefits = parse_benefits(SAMPLE)
        epsilon = [b for b in benefits if b.project_name == "Epsilon"][0]
        assert epsilon.is_at_risk is True

    def test_confidence_auto_derived(self):
        benefits = parse_benefits(SAMPLE)
        epsilon = [b for b in benefits if b.project_name == "Epsilon"][0]
        assert epsilon.confidence == BenefitConfidence.LOW

    def test_benefit_ids_unique(self):
        benefits = parse_benefits(SAMPLE)
        ids = [b.benefit_id for b in benefits]
        assert len(ids) == len(set(ids))

    def test_to_dict(self):
        benefits = parse_benefits(SAMPLE)
        d = benefits[0].to_dict()
        assert "benefit_id" in d
        assert "expected_value" in d
        assert "realisation_pct" in d
