from __future__ import annotations

from collections.abc import Callable

from sircles_agents.models import (
    CRMRecord,
    DealStage,
    Disposition,
    LeadIntelligenceResult,
    OutreachArtifact,
    ResolutionDecision,
)
from sircles_agents.tools.mock_crm import upsert_crm_record


class CRMHygieneAgent:
    """
    Writes a clean, structured mock CRM record.

    This agent does not decide the lead disposition. It records the orchestrator's
    decision, sets the CRM stage, flags human review when needed, and preserves
    the reasoning in notes.
    """

    def __init__(
        self,
        crm_upserter: Callable[[CRMRecord], CRMRecord] = upsert_crm_record,
    ) -> None:
        self._crm_upserter = crm_upserter

    def run(
        self,
        lead_intelligence: LeadIntelligenceResult,
        resolution: ResolutionDecision,
        outreach: OutreachArtifact | None = None,
    ) -> CRMRecord:
        raw_lead = lead_intelligence.raw_lead
        contact = lead_intelligence.contact
        company = lead_intelligence.company
        score = lead_intelligence.score

        human_review_flag = (
            resolution.requires_human_review
            or resolution.final_disposition == Disposition.HUMAN_REVIEW
        )

        record = CRMRecord(
            lead_id=raw_lead.lead_id,
            contact_name=contact.full_name,
            email=contact.email,
            company_name=company.company_name,
            role_title=contact.role_title,
            disposition=resolution.final_disposition,
            deal_stage=_deal_stage_for_disposition(resolution.final_disposition),
            score=score.total_score,
            confidence=resolution.confidence,
            human_review_flag=human_review_flag,
            human_review_reason=resolution.human_review_reason,
            notes=_build_notes(lead_intelligence, resolution, outreach),
            outreach=outreach,
        )

        return self._crm_upserter(record)


def _deal_stage_for_disposition(disposition: Disposition) -> DealStage:
    if disposition == Disposition.PURSUE:
        return DealStage.QUALIFIED

    if disposition == Disposition.NURTURE:
        return DealStage.NURTURE

    if disposition == Disposition.SKIP:
        return DealStage.DISQUALIFIED

    return DealStage.HUMAN_REVIEW


def _build_notes(
    lead_intelligence: LeadIntelligenceResult,
    resolution: ResolutionDecision,
    outreach: OutreachArtifact | None,
) -> list[str]:
    score = lead_intelligence.score
    notes: list[str] = [
        f"Lead score: {score.total_score}/100.",
        f"Lead Intelligence proposed: {score.proposed_disposition.value} "
        f"with confidence {score.confidence}.",
        f"Final resolution: {resolution.final_disposition.value} "
        f"with confidence {resolution.confidence}.",
        f"Resolution rationale: {resolution.rationale}",
    ]

    if resolution.winning_position is not None:
        notes.append(
            "Winning debate position: "
            f"{resolution.winning_position.agent.value} recommended "
            f"{resolution.winning_position.recommendation.value} "
            f"with confidence {resolution.winning_position.confidence}."
        )
    else:
        notes.append(
            "No debate position exactly matched the final disposition; "
            "the orchestrator applied the documented resolution rule."
        )

    if resolution.dissenting_positions:
        dissent_summaries = [
            f"{position.agent.value} recommended {position.recommendation.value} "
            f"with confidence {position.confidence}"
            for position in resolution.dissenting_positions
        ]
        notes.append("Recorded dissent: " + "; ".join(dissent_summaries) + ".")

    if resolution.human_review_reason:
        notes.append(f"Human review reason: {resolution.human_review_reason}")

    if score.positive_evidence:
        notes.append(
            "Positive evidence: " + " | ".join(score.positive_evidence[:3])
        )

    if score.negative_evidence:
        notes.append(
            "Negative evidence: " + " | ".join(score.negative_evidence[:3])
        )

    if score.uncertainty:
        notes.append(
            "Uncertainty: " + " | ".join(score.uncertainty[:3])
        )

    if outreach is not None:
        notes.append("Outreach draft created but not sent.")
    elif resolution.final_disposition == Disposition.PURSUE:
        notes.append("Warning: pursue disposition has no outreach artifact attached.")
    else:
        notes.append("No outreach drafted because final disposition was not pursue.")

    return notes