from __future__ import annotations

from pathlib import Path
from typing import Any

from sircles_agents.agents.crm_hygiene import CRMHygieneAgent
from sircles_agents.agents.lead_intelligence import LeadIntelligenceAgent
from sircles_agents.agents.outreach import SDROutreachAgent
from sircles_agents.debate import resolve_debate, run_disposition_debate
from sircles_agents.models import (
    AgentName,
    Disposition,
    FinalRunOutput,
    LeadIntelligenceResult,
    OutreachArtifact,
    RawLead,
    ResolutionDecision,
    TraceEvent,
)


class Orchestrator:
    """
    Team lead for the agentic workflow.

    Owns the sequence, shared state, debate trigger, resolution, handoffs,
    CRM write, and readable trace.

    Required flow:
    intake -> enrich -> debate disposition -> resolve & record
    -> outreach if pursue -> CRM -> final artifacts + trace
    """

    def __init__(
        self,
        lead_intelligence_agent: LeadIntelligenceAgent | None = None,
        outreach_agent: SDROutreachAgent | None = None,
        crm_agent: CRMHygieneAgent | None = None,
        trace_dir: Path | str = "traces",
    ) -> None:
        self.lead_intelligence_agent = lead_intelligence_agent or LeadIntelligenceAgent()
        self.outreach_agent = outreach_agent or SDROutreachAgent()
        self.crm_agent = crm_agent or CRMHygieneAgent()
        self.trace_dir = Path(trace_dir)

    def run(self, raw_lead: RawLead, write_trace: bool = True) -> FinalRunOutput:
        trace: list[TraceEvent] = []

        self._add_trace(
            trace=trace,
            actor=AgentName.ORCHESTRATOR,
            action="intake_received",
            summary=(
                f"Received inbound lead {raw_lead.lead_id} from {raw_lead.source}."
            ),
            data={
                "lead_id": raw_lead.lead_id,
                "company_name": raw_lead.company_name,
                "role_title": raw_lead.role_title,
                "message": raw_lead.message,
            },
        )

        lead_intelligence = self.lead_intelligence_agent.run(raw_lead)

        self._trace_lead_intelligence(trace, lead_intelligence)

        debate_positions = run_disposition_debate(lead_intelligence)

        for position in debate_positions:
            self._add_trace(
                trace=trace,
                actor=position.agent,
                action="debate_position_submitted",
                summary=(
                    f"{position.agent.value} recommended "
                    f"{position.recommendation.value} with confidence "
                    f"{position.confidence}."
                ),
                data=position.model_dump(mode="json"),
            )

        resolution = resolve_debate(lead_intelligence, debate_positions)

        self._trace_resolution(trace, resolution)

        outreach: OutreachArtifact | None = None

        if resolution.final_disposition == Disposition.PURSUE:
            outreach = self.outreach_agent.run(lead_intelligence, resolution)

            self._add_trace(
                trace=trace,
                actor=AgentName.SDR_OUTREACH,
                action="outreach_drafted",
                summary=(
                    "Drafted first-touch email and LinkedIn note because "
                    "the final disposition was pursue."
                ),
                data=outreach.model_dump(mode="json"),
            )
        else:
            self._add_trace(
                trace=trace,
                actor=AgentName.ORCHESTRATOR,
                action="outreach_skipped",
                summary=(
                    "Outreach was not drafted because final disposition was "
                    f"{resolution.final_disposition.value}."
                ),
                data={
                    "final_disposition": resolution.final_disposition.value,
                    "requires_human_review": resolution.requires_human_review,
                    "human_review_reason": resolution.human_review_reason,
                },
            )

        crm_record = self.crm_agent.run(
            lead_intelligence=lead_intelligence,
            resolution=resolution,
            outreach=outreach,
        )

        self._add_trace(
            trace=trace,
            actor=AgentName.CRM_HYGIENE,
            action="crm_record_upserted",
            summary=(
                f"CRM record written with stage {crm_record.deal_stage.value} "
                f"and disposition {crm_record.disposition.value}."
            ),
            data=crm_record.model_dump(mode="json"),
        )

        final_output = FinalRunOutput(
            lead_id=raw_lead.lead_id,
            final_disposition=resolution.final_disposition,
            lead_intelligence=lead_intelligence,
            debate_positions=debate_positions,
            resolution=resolution,
            outreach=outreach,
            crm_record=crm_record,
            trace=trace,
        )

        if write_trace:
            self.write_trace(final_output)

        return final_output

    def write_trace(self, output: FinalRunOutput) -> Path:
        """
        Save a full JSON run trace for reviewer inspection.

        This helps satisfy the deliverable requiring a run trace for at least
        two cases.
        """
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.trace_dir / f"{output.lead_id}_trace.json"

        with output_path.open("w", encoding="utf-8") as file:
            file.write(output.model_dump_json(indent=2))

        return output_path

    @staticmethod
    def _add_trace(
        trace: list[TraceEvent],
        actor: AgentName,
        action: str,
        summary: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        trace.append(
            TraceEvent(
                actor=actor,
                action=action,
                summary=summary,
                data=data or {},
            )
        )

    def _trace_lead_intelligence(
        self,
        trace: list[TraceEvent],
        lead_intelligence: LeadIntelligenceResult,
    ) -> None:
        score = lead_intelligence.score
        company = lead_intelligence.company

        self._add_trace(
            trace=trace,
            actor=AgentName.LEAD_INTELLIGENCE,
            action="lead_enriched_and_scored",
            summary=(
                f"Enriched {lead_intelligence.contact.full_name} at "
                f"{company.company_name}; proposed "
                f"{score.proposed_disposition.value} with score "
                f"{score.total_score}/100 and confidence {score.confidence}."
            ),
            data={
                "contact": lead_intelligence.contact.model_dump(mode="json"),
                "company": company.model_dump(mode="json"),
                "score": score.model_dump(mode="json"),
            },
        )

    def _trace_resolution(
        self,
        trace: list[TraceEvent],
        resolution: ResolutionDecision,
    ) -> None:
        dissent = [
            {
                "agent": position.agent.value,
                "recommendation": position.recommendation.value,
                "confidence": position.confidence,
                "thesis": position.thesis,
            }
            for position in resolution.dissenting_positions
        ]

        self._add_trace(
            trace=trace,
            actor=AgentName.ORCHESTRATOR,
            action="debate_resolved",
            summary=(
                f"Resolved debate to {resolution.final_disposition.value} "
                f"with confidence {resolution.confidence}."
            ),
            data={
                "resolution": resolution.model_dump(mode="json"),
                "recorded_dissent": dissent,
            },
        )