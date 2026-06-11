from __future__ import annotations

import pytest

from sircles_agents.agents.lead_intelligence import LeadIntelligenceAgent
from sircles_agents.models import Disposition, LeadIntelligenceResult
from sircles_agents.tools.mock_lead_scanner import fetch_lead_by_id


@pytest.mark.parametrize(
    ("lead_id", "expected_disposition", "expected_min_score", "expected_max_score"),
    [
        ("lead_saas_pursue", Disposition.PURSUE, 90, 100),
        ("lead_student_skip", Disposition.SKIP, 0, 10),
        ("lead_ecommerce_nurture", Disposition.NURTURE, 50, 70),
        ("lead_competitor_ambiguous", Disposition.HUMAN_REVIEW, 30, 50),
    ],
)
def test_lead_intelligence_returns_expected_disposition_band(
    lead_id: str,
    expected_disposition: Disposition,
    expected_min_score: int,
    expected_max_score: int,
) -> None:
    agent = LeadIntelligenceAgent()
    raw_lead = fetch_lead_by_id(lead_id)

    result = agent.run(raw_lead)

    assert isinstance(result, LeadIntelligenceResult)
    assert result.raw_lead.lead_id == lead_id
    assert result.contact.lead_id == lead_id
    assert result.score.proposed_disposition == expected_disposition
    assert expected_min_score <= result.score.total_score <= expected_max_score
    assert 0.0 <= result.score.confidence <= 1.0


def test_lead_intelligence_output_contains_required_handoff_fields() -> None:
    agent = LeadIntelligenceAgent()
    raw_lead = fetch_lead_by_id("lead_saas_pursue")

    result = agent.run(raw_lead)

    assert result.raw_lead.email
    assert result.contact.full_name
    assert result.company.company_name
    assert result.company.industry
    assert result.score.positive_evidence
    assert result.score.breakdown.total == result.score.total_score