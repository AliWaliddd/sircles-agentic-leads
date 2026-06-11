from __future__ import annotations

from sircles_agents.agents.lead_intelligence import LeadIntelligenceAgent
from sircles_agents.debate import resolve_debate, run_disposition_debate
from sircles_agents.models import AgentName, Disposition
from sircles_agents.tools.mock_lead_scanner import fetch_lead_by_id


def _lead_intelligence_for(lead_id: str):
    raw_lead = fetch_lead_by_id(lead_id)
    return LeadIntelligenceAgent().run(raw_lead)


def test_clear_high_fit_lead_resolves_to_pursue_with_recorded_dissent() -> None:
    lead_intelligence = _lead_intelligence_for("lead_saas_pursue")

    positions = run_disposition_debate(lead_intelligence)
    resolution = resolve_debate(lead_intelligence, positions)

    assert len(positions) == 2
    assert {position.recommendation for position in positions} == {
        Disposition.PURSUE,
        Disposition.NURTURE,
    }

    assert resolution.final_disposition == Disposition.PURSUE
    assert resolution.requires_human_review is False
    assert resolution.winning_position is not None
    assert resolution.winning_position.agent == AgentName.PURSUIT_ADVOCATE
    assert resolution.dissenting_positions
    assert resolution.resolution_rule


def test_clear_poor_fit_lead_resolves_to_skip() -> None:
    lead_intelligence = _lead_intelligence_for("lead_student_skip")

    positions = run_disposition_debate(lead_intelligence)
    resolution = resolve_debate(lead_intelligence, positions)

    assert {position.recommendation for position in positions} == {
        Disposition.NURTURE,
        Disposition.SKIP,
    }

    assert resolution.final_disposition == Disposition.SKIP
    assert resolution.requires_human_review is False
    assert resolution.winning_position is not None
    assert resolution.winning_position.agent == AgentName.RISK_SKEPTIC
    assert resolution.dissenting_positions


def test_moderate_uncertain_lead_resolves_to_nurture() -> None:
    lead_intelligence = _lead_intelligence_for("lead_ecommerce_nurture")

    positions = run_disposition_debate(lead_intelligence)
    resolution = resolve_debate(lead_intelligence, positions)

    assert {position.recommendation for position in positions} == {
        Disposition.NURTURE,
        Disposition.HUMAN_REVIEW,
    }

    assert resolution.final_disposition == Disposition.NURTURE
    assert resolution.requires_human_review is False
    assert resolution.winning_position is not None
    assert resolution.dissenting_positions


def test_competing_agency_triggers_human_review_and_records_dissent() -> None:
    lead_intelligence = _lead_intelligence_for("lead_competitor_ambiguous")

    positions = run_disposition_debate(lead_intelligence)
    resolution = resolve_debate(lead_intelligence, positions)

    assert {position.recommendation for position in positions} == {
        Disposition.NURTURE,
        Disposition.HUMAN_REVIEW,
    }

    assert resolution.final_disposition == Disposition.HUMAN_REVIEW
    assert resolution.requires_human_review is True
    assert resolution.human_review_reason is not None
    assert resolution.winning_position is not None
    assert resolution.winning_position.agent == AgentName.RISK_SKEPTIC
    assert resolution.dissenting_positions