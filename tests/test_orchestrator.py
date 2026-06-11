from __future__ import annotations

import json

from sircles_agents.agents.crm_hygiene import CRMHygieneAgent
from sircles_agents.models import AgentName, DealStage, Disposition
from sircles_agents.orchestrator import Orchestrator
from sircles_agents.tools.mock_lead_scanner import fetch_lead_by_id


def _test_orchestrator(tmp_path):
    return Orchestrator(
        crm_agent=CRMHygieneAgent(crm_upserter=lambda record: record),
        trace_dir=tmp_path,
    )


def test_orchestrator_runs_full_happy_path_for_clear_pursue(tmp_path) -> None:
    raw_lead = fetch_lead_by_id("lead_saas_pursue")
    orchestrator = _test_orchestrator(tmp_path)

    output = orchestrator.run(raw_lead)

    assert output.lead_id == "lead_saas_pursue"
    assert output.final_disposition == Disposition.PURSUE
    assert output.outreach is not None
    assert output.crm_record.deal_stage == DealStage.QUALIFIED
    assert output.crm_record.human_review_flag is False
    assert len(output.debate_positions) == 2
    assert output.resolution.dissenting_positions

    actors = {event.actor for event in output.trace}
    assert AgentName.ORCHESTRATOR in actors
    assert AgentName.LEAD_INTELLIGENCE in actors
    assert AgentName.PURSUIT_ADVOCATE in actors
    assert AgentName.RISK_SKEPTIC in actors
    assert AgentName.SDR_OUTREACH in actors
    assert AgentName.CRM_HYGIENE in actors

    trace_path = tmp_path / "lead_saas_pursue_trace.json"
    assert trace_path.exists()

    saved_trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert saved_trace["lead_id"] == "lead_saas_pursue"
    assert saved_trace["final_disposition"] == "pursue"


def test_orchestrator_escalates_ambiguous_competitor_without_outreach(tmp_path) -> None:
    raw_lead = fetch_lead_by_id("lead_competitor_ambiguous")
    orchestrator = _test_orchestrator(tmp_path)

    output = orchestrator.run(raw_lead)

    assert output.lead_id == "lead_competitor_ambiguous"
    assert output.final_disposition == Disposition.HUMAN_REVIEW
    assert output.outreach is None
    assert output.crm_record.deal_stage == DealStage.HUMAN_REVIEW
    assert output.crm_record.human_review_flag is True
    assert output.resolution.human_review_reason is not None
    assert len(output.debate_positions) == 2
    assert output.resolution.dissenting_positions

    actions = {event.action for event in output.trace}
    assert "outreach_skipped" in actions
    assert "debate_resolved" in actions
    assert "crm_record_upserted" in actions

    trace_path = tmp_path / "lead_competitor_ambiguous_trace.json"
    assert trace_path.exists()

    saved_trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert saved_trace["lead_id"] == "lead_competitor_ambiguous"
    assert saved_trace["final_disposition"] == "human_review"