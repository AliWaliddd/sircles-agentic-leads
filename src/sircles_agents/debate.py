from __future__ import annotations

from sircles_agents.models import (
    AgentName,
    DebatePosition,
    Disposition,
    LeadIntelligenceResult,
    ResolutionDecision,
)


RESOLUTION_RULE = (
    "Confidence-weighted arbitration with hard risk vetoes: "
    "competitor/conflict risk or low confidence escalates to human review; "
    "clear high-score, high-confidence leads can be pursued; "
    "clear poor-fit leads are skipped; moderate-fit leads are nurtured."
)


class PursuitAdvocateAgent:
    """
    Debate participant that argues the best commercial case for the lead.

    This agent is intentionally opportunity-seeking. It focuses on the cost of
    false skips: missing a lead that could become a multi-month retainer.
    """

    def run(self, lead_intelligence: LeadIntelligenceResult) -> DebatePosition:
        contact = lead_intelligence.contact
        company = lead_intelligence.company
        score = lead_intelligence.score

        if company.is_competing_agency:
            recommendation = Disposition.NURTURE
            confidence = 0.58
            thesis = (
                "There may be partnership or referral value, but the lead should "
                "not receive normal sales outreach because the company appears to "
                "be a competing agency."
            )
        elif score.total_score >= 75:
            recommendation = Disposition.PURSUE
            confidence = min(0.95, max(0.80, score.confidence + 0.05))
            thesis = (
                "This lead matches the ICP strongly enough to justify autonomous "
                "first-touch outreach."
            )
        elif score.total_score >= 50:
            recommendation = Disposition.NURTURE
            confidence = max(0.60, score.confidence)
            thesis = (
                "The lead has enough upside to keep warm, but the current evidence "
                "does not justify fully autonomous sales outreach."
            )
        else:
            recommendation = Disposition.NURTURE
            confidence = 0.42
            thesis = (
                "The lead is weak, but a low-cost nurture path avoids completely "
                "discarding a possible future opportunity."
            )

        evidence_for = list(score.positive_evidence)
        if contact.evidence:
            evidence_for.extend(contact.evidence)
        if company.evidence:
            evidence_for.extend(company.evidence)

        return DebatePosition(
            agent=AgentName.PURSUIT_ADVOCATE,
            recommendation=recommendation,
            confidence=round(confidence, 2),
            thesis=thesis,
            evidence_for=evidence_for,
            evidence_against=list(score.negative_evidence),
            risk_notes=list(company.risk_signals),
        )


class RiskSkepticAgent:
    """
    Debate participant that argues against careless pursuit.

    This agent focuses on the cost of false pursues: wasted team time,
    reputational damage, bad-fit outreach, and exposing process to competitors.
    """

    def run(self, lead_intelligence: LeadIntelligenceResult) -> DebatePosition:
        contact = lead_intelligence.contact
        company = lead_intelligence.company
        score = lead_intelligence.score

        if company.is_competing_agency:
            recommendation = Disposition.HUMAN_REVIEW
            confidence = 0.90
            thesis = (
                "This should be reviewed by a human because the company appears "
                "to be a competing agency and the inquiry may be partnership, "
                "research, or competitive intelligence rather than buying intent."
            )
        elif score.total_score <= 30:
            recommendation = Disposition.SKIP
            confidence = max(0.85, score.confidence)
            thesis = (
                "The lead is far outside the retainer ICP, so pursuing it would "
                "likely waste SDR time."
            )
        elif score.breakdown.risk_penalty <= -14:
            recommendation = Disposition.HUMAN_REVIEW
            confidence = max(0.70, score.confidence)
            thesis = (
                "The lead has commercial upside, but risk signals are strong "
                "enough that a human should review before any outreach."
            )
        elif score.total_score >= 75:
            recommendation = Disposition.NURTURE
            confidence = 0.52
            thesis = (
                "The lead is attractive, but the safer opposing position is to "
                "verify the opportunity before outreach. This creates a real "
                "challenge for the resolver rather than rubber-stamping pursuit."
            )
        elif score.total_score >= 50:
            recommendation = Disposition.HUMAN_REVIEW
            confidence = max(0.65, score.confidence)
            thesis = (
                "The lead is plausible but has enough uncertainty around budget, "
                "timing, or urgency that autonomous outreach may be premature."
            )
        else:
            recommendation = Disposition.SKIP
            confidence = 0.75
            thesis = (
                "The lead does not show enough evidence of fit, budget, or buying "
                "intent to justify sales follow-up."
            )

        evidence_against = list(score.negative_evidence)
        if score.uncertainty:
            evidence_against.extend(score.uncertainty)

        return DebatePosition(
            agent=AgentName.RISK_SKEPTIC,
            recommendation=recommendation,
            confidence=round(confidence, 2),
            thesis=thesis,
            evidence_for=evidence_against,
            evidence_against=list(score.positive_evidence),
            risk_notes=list(company.risk_signals),
        )


def run_disposition_debate(
    lead_intelligence: LeadIntelligenceResult,
) -> list[DebatePosition]:
    """
    Run the required debate before any consequential outreach action.

    The two agents are deliberately asymmetric:
    - Pursuit Advocate argues the upside case.
    - Risk Skeptic argues the caution case.

    This creates genuine competing recommendations instead of one agent simply
    agreeing with itself.
    """
    return [
        PursuitAdvocateAgent().run(lead_intelligence),
        RiskSkepticAgent().run(lead_intelligence),
    ]


def resolve_debate(
    lead_intelligence: LeadIntelligenceResult,
    positions: list[DebatePosition],
) -> ResolutionDecision:
    """
    Resolve the debate into one disposition.

    The resolution is intentionally deterministic and explainable so it can be
    tested and defended in the design note.
    """
    if not positions:
        raise ValueError("Cannot resolve debate without at least one position.")

    company = lead_intelligence.company
    score = lead_intelligence.score

    requires_human_review = False
    human_review_reason: str | None = None

    if company.is_competing_agency:
        final_disposition = Disposition.HUMAN_REVIEW
        requires_human_review = True
        human_review_reason = (
            "Company appears to be a competing agency; normal autonomous "
            "outreach could create reputational or information-leakage risk."
        )
        rationale = (
            "Hard risk veto overrode the opportunity case. The lead may have "
            "partnership value, but it should not receive normal automated "
            "sales outreach."
        )

    elif score.confidence < 0.55:
        final_disposition = Disposition.HUMAN_REVIEW
        requires_human_review = True
        human_review_reason = (
            "Lead intelligence confidence is below the autonomous action threshold."
        )
        rationale = (
            "The system lacked enough confidence to choose pursue, nurture, or skip "
            "safely."
        )

    elif (
        score.total_score >= 75
        and score.confidence >= 0.75
        and score.breakdown.risk_penalty >= -7
    ):
        final_disposition = Disposition.PURSUE
        rationale = (
            "The lead has a high ICP score, strong confidence, and no meaningful "
            "risk penalty. The advocate's pursue case outweighs the skeptic's "
            "caution."
        )

    elif score.total_score <= 30 and score.confidence >= 0.75:
        final_disposition = Disposition.SKIP
        rationale = (
            "The lead is a clear poor fit with high confidence. The cost of a false "
            "pursue is higher than the small chance of future opportunity."
        )

    elif score.total_score >= 50:
        if score.breakdown.risk_penalty <= -20:
            final_disposition = Disposition.HUMAN_REVIEW
            requires_human_review = True
            human_review_reason = (
                "Moderate lead quality combined with significant risk signals."
            )
            rationale = (
                "The lead has some upside, but risk is too high for autonomous "
                "outreach."
            )
        else:
            final_disposition = Disposition.NURTURE
            rationale = (
                "The lead has plausible fit but not enough urgency or confidence "
                "for autonomous first-touch outreach."
            )

    else:
        final_disposition = Disposition.SKIP
        rationale = (
            "The lead does not show enough fit, budget, or buying intent to justify "
            "pursuit."
        )

    winning_position = _select_winning_position(final_disposition, positions)
    dissenting_positions = [
        position for position in positions if position is not winning_position
    ]

    return ResolutionDecision(
        final_disposition=final_disposition,
        confidence=_resolution_confidence(final_disposition, score.confidence, positions),
        resolution_rule=RESOLUTION_RULE,
        rationale=rationale,
        winning_position=winning_position,
        dissenting_positions=dissenting_positions,
        requires_human_review=requires_human_review,
        human_review_reason=human_review_reason,
    )


def _select_winning_position(
    final_disposition: Disposition,
    positions: list[DebatePosition],
) -> DebatePosition | None:
    matching_positions = [
        position for position in positions if position.recommendation == final_disposition
    ]

    if matching_positions:
        return max(matching_positions, key=lambda position: position.confidence)

    return None


def _resolution_confidence(
    final_disposition: Disposition,
    lead_intelligence_confidence: float,
    positions: list[DebatePosition],
) -> float:
    matching_confidences = [
        position.confidence
        for position in positions
        if position.recommendation == final_disposition
    ]

    if not matching_confidences:
        return round(lead_intelligence_confidence, 2)

    combined = matching_confidences + [lead_intelligence_confidence]
    return round(sum(combined) / len(combined), 2)