from __future__ import annotations

import pytest

from sircles_agents.agents.crm_hygiene import CRMHygieneAgent
from sircles_agents.agents.lead_intelligence import LeadIntelligenceAgent
from sircles_agents.agents.outreach import SDROutreachAgent
from sircles_agents.debate import resolve_debate, run_disposition_debate
from sircles_agents.models import DealStage, Disposition
from sircles_agents.tools.mock_lead_scanner import fetch_lead_by_id


def _resolved_lead(lead_id: str):
    raw_lead = fetch_lead_by_id(lead_id)
    lead_intelligence = LeadIntelligenceAgent().run(raw_lead)
    positions = run_disposition_debate(lead_intelligence)
    resolution = resolve_debate(lead_intelligence, positions)
    return lead_intelligence, resolution


def test_outreach_agent_drafts_only_for_pursue_leads() -> None:
    lead_intelligence, resolution = _resolved_lead("lead_saas_pursue")

    assert resolution.final_disposition == Disposition.PURSUE

    outreach = SDROutreachAgent().run(lead_intelligence, resolution)

    assert outreach.subject
    assert outreach.email_body
    assert outreach.linkedin_note
    assert outreach.grounded_in
    assert "Northstar Analytics" in outreach.email_body


def test_outreach_agent_refuses_non_pursue_leads() -> None:
    lead_intelligence, resolution = _resolved_lead("lead_competitor_ambiguous")

    assert resolution.final_disposition != Disposition.PURSUE

    with pytest.raises(ValueError):
        SDROutreachAgent().run(lead_intelligence, resolution)


def test_crm_hygiene_creates_qualified_record_for_pursue_lead() -> None:
    lead_intelligence, resolution = _resolved_lead("lead_saas_pursue")
    outreach = SDROutreachAgent().run(lead_intelligence, resolution)

    crm_agent = CRMHygieneAgent(crm_upserter=lambda record: record)
    record = crm_agent.run(lead_intelligence, resolution, outreach)

    assert record.lead_id == "lead_saas_pursue"
    assert record.disposition == Disposition.PURSUE
    assert record.deal_stage == DealStage.QUALIFIED
    assert record.human_review_flag is False
    assert record.outreach is not None
    assert record.notes


def test_crm_hygiene_flags_competing_agency_for_human_review() -> None:
    lead_intelligence, resolution = _resolved_lead("lead_competitor_ambiguous")

    crm_agent = CRMHygieneAgent(crm_upserter=lambda record: record)
    record = crm_agent.run(lead_intelligence, resolution, outreach=None)

    assert record.lead_id == "lead_competitor_ambiguous"
    assert record.disposition == Disposition.HUMAN_REVIEW
    assert record.deal_stage == DealStage.HUMAN_REVIEW
    assert record.human_review_flag is True
    assert record.human_review_reason is not None
    assert record.outreach is None
    assert any("Recorded dissent" in note for note in record.notes)