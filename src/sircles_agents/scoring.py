from __future__ import annotations

from sircles_agents.models import (
    Disposition,
    EnrichedCompany,
    EnrichedContact,
    LeadScore,
    ScoreBreakdown,
)


def score_lead(contact: EnrichedContact, company: EnrichedCompany) -> LeadScore:
    """
    Convert enriched contact + company data into a transparent lead score.

    This is intentionally deterministic for the take-home:
    - no API calls
    - no hidden prompt behavior
    - easy to test
    - easy to defend in the design note
    """
    breakdown = ScoreBreakdown(
        industry_fit=_score_industry_fit(company),
        company_size_budget=_score_company_size_budget(company),
        growth_signal=_score_growth_signal(company),
        buyer_fit=_score_buyer_fit(contact),
        pain_signal=_score_pain_signal(company),
        risk_penalty=_score_risk_penalty(company),
    )

    total_score = breakdown.total
    confidence = _estimate_confidence(contact, company, total_score)
    proposed_disposition = _propose_disposition(
        total_score=total_score,
        confidence=confidence,
        breakdown=breakdown,
        company=company,
    )

    positive_evidence = _build_positive_evidence(contact, company, breakdown)
    negative_evidence = _build_negative_evidence(contact, company, breakdown)
    uncertainty = _build_uncertainty(company)

    return LeadScore(
        total_score=total_score,
        confidence=confidence,
        proposed_disposition=proposed_disposition,
        breakdown=breakdown,
        positive_evidence=positive_evidence,
        negative_evidence=negative_evidence,
        uncertainty=uncertainty,
    )


def _score_industry_fit(company: EnrichedCompany) -> int:
    """
    Score whether the company resembles a plausible Sircles client.

    B2B SaaS and growth-stage companies are treated as strongest ICP.
    E-commerce can be a good fit but may vary by budget.
    Competing agencies are relevant but risky, so they get industry relevance
    here and are penalized separately through risk_penalty.
    """
    industry = company.industry.lower()

    if "personal" in industry or "portfolio" in industry:
        return 0

    if "saas" in industry or "b2b" in industry:
        return 25

    if "marketing agency" in industry or company.is_competing_agency:
        return 22

    if "e-commerce" in industry or "ecommerce" in industry or "beauty" in industry:
        return 18

    return 10


def _score_company_size_budget(company: EnrichedCompany) -> int:
    """
    Use employee count as a simple budget proxy.

    This is not perfect, but it is defensible for a mocked take-home:
    larger companies are more likely to afford multi-month agency retainers.
    """
    employee_count = company.employee_count

    if employee_count is None:
        return 5

    if employee_count >= 100:
        return 20

    if employee_count >= 50:
        return 16

    if employee_count >= 10:
        return 10

    if employee_count >= 2:
        return 5

    return 0


def _score_growth_signal(company: EnrichedCompany) -> int:
    """
    Growth signals indicate urgency and potential revenue opportunity.
    """
    return min(15, len(company.growth_signals) * 5)


def _score_buyer_fit(contact: EnrichedContact) -> int:
    """
    Convert mocked buyer-fit enrichment into the 0–20 scoring band.
    """
    return round((contact.buyer_fit_score / 100) * 20)


def _score_pain_signal(company: EnrichedCompany) -> int:
    """
    Pain signals indicate why the lead may need an agency now.
    """
    return min(20, len(company.pain_signals) * 7)


def _score_risk_penalty(company: EnrichedCompany) -> int:
    """
    Penalize risks that could waste SDR time or create reputational damage.

    Competing agency risk is treated as severe because a clumsy outreach could
    expose positioning or process to a competitor.
    """
    if company.is_competing_agency:
        return -25

    return -min(30, len(company.risk_signals) * 7)


def _estimate_confidence(
    contact: EnrichedContact,
    company: EnrichedCompany,
    total_score: int,
) -> float:
    """
    Estimate confidence in the scoring decision.

    Confidence is not the same as lead quality.
    A lead can be a bad fit with high confidence, such as the student example.
    """
    data_points = 0

    if company.website:
        data_points += 1
    if company.employee_count is not None:
        data_points += 1
    if company.estimated_annual_revenue:
        data_points += 1
    if company.geography:
        data_points += 1
    if contact.linkedin_url:
        data_points += 1
    if contact.evidence:
        data_points += 1
    if company.evidence:
        data_points += 1

    signal_count = (
        len(company.growth_signals)
        + len(company.pain_signals)
        + len(company.risk_signals)
    )

    if company.is_competing_agency:
        signal_count += 1

    confidence = 0.45
    confidence += min(0.25, data_points * 0.035)
    confidence += min(0.20, signal_count * 0.025)

    ambiguity_penalty = 0.0

    if company.risk_signals:
        ambiguity_penalty += min(0.15, len(company.risk_signals) * 0.04)

    if company.is_competing_agency:
        ambiguity_penalty += 0.10

    combined_text = _combined_company_text(company)
    ambiguous_terms = (
        "may",
        "might",
        "exploratory",
        "exploring",
        "uncertain",
        "not yet clear",
        "figuring out",
        "partnership",
        "ambiguous",
    )

    if any(term in combined_text for term in ambiguous_terms):
        ambiguity_penalty += 0.08

    if not company.website or company.estimated_annual_revenue is None:
        ambiguity_penalty += 0.08

    confidence -= ambiguity_penalty

    # Clear strong-fit leads should be safe to pursue autonomously.
    if total_score >= 75 and not company.risk_signals and not company.is_competing_agency:
        confidence = max(confidence, 0.88)

    # Clear poor-fit leads can also be high-confidence skips.
    if (
        total_score <= 25
        and len(company.risk_signals) >= 2
        and contact.buyer_fit_score <= 20
    ):
        confidence = max(confidence, 0.84)

    return round(_clamp_float(confidence, minimum=0.35, maximum=0.95), 2)


def _propose_disposition(
    total_score: int,
    confidence: float,
    breakdown: ScoreBreakdown,
    company: EnrichedCompany,
) -> Disposition:
    """
    Convert score + confidence into the Lead Intelligence Agent's initial call.

    This is not the final decision. The debate mechanism will challenge it.
    """
    if company.is_competing_agency:
        return Disposition.HUMAN_REVIEW

    if confidence < 0.55:
        return Disposition.HUMAN_REVIEW

    if total_score >= 75 and confidence >= 0.75 and breakdown.risk_penalty >= -7:
        return Disposition.PURSUE

    if total_score >= 50:
        if breakdown.risk_penalty <= -20:
            return Disposition.HUMAN_REVIEW
        return Disposition.NURTURE

    return Disposition.SKIP


def _build_positive_evidence(
    contact: EnrichedContact,
    company: EnrichedCompany,
    breakdown: ScoreBreakdown,
) -> list[str]:
    evidence: list[str] = []

    if breakdown.industry_fit >= 20:
        evidence.append(
            f"Industry fit is strong: {company.industry} scored "
            f"{breakdown.industry_fit}/25."
        )
    elif breakdown.industry_fit >= 15:
        evidence.append(
            f"Industry fit is plausible but not perfect: {company.industry} scored "
            f"{breakdown.industry_fit}/25."
        )

    if breakdown.company_size_budget >= 10:
        evidence.append(
            f"Company size suggests possible retainer budget: "
            f"{company.employee_count} employees scored "
            f"{breakdown.company_size_budget}/20."
        )

    if company.growth_signals:
        evidence.append(
            "Growth signals found: " + "; ".join(company.growth_signals)
        )

    if breakdown.buyer_fit >= 15:
        evidence.append(
            f"Contact has strong buyer fit: {contact.role_title} scored "
            f"{breakdown.buyer_fit}/20."
        )

    if company.pain_signals:
        evidence.append(
            "Pain signals found: " + "; ".join(company.pain_signals)
        )

    return evidence


def _build_negative_evidence(
    contact: EnrichedContact,
    company: EnrichedCompany,
    breakdown: ScoreBreakdown,
) -> list[str]:
    evidence: list[str] = []

    if contact.buyer_fit_score < 40:
        evidence.append(
            f"Contact role has weak buyer fit: {contact.role_title}."
        )

    if company.employee_count is not None and company.employee_count <= 1:
        evidence.append(
            "Company appears too small to be a qualified agency retainer lead."
        )

    if company.risk_signals:
        evidence.append(
            "Risk signals found: " + "; ".join(company.risk_signals)
        )

    if company.is_competing_agency:
        evidence.append(
            "Company appears to be a competing marketing agency, creating conflict and information-leakage risk."
        )

    if breakdown.risk_penalty < 0:
        evidence.append(
            f"Risk penalty applied: {breakdown.risk_penalty} points."
        )

    return evidence


def _build_uncertainty(company: EnrichedCompany) -> list[str]:
    uncertainty: list[str] = []

    if not company.website:
        uncertainty.append("No company website was available in enrichment.")

    if company.employee_count is None:
        uncertainty.append("Employee count is unknown.")

    if not company.estimated_annual_revenue:
        uncertainty.append("Revenue estimate is unavailable.")

    if not company.growth_signals:
        uncertainty.append("No clear growth trigger was found.")

    combined_text = _combined_company_text(company)

    if "budget" in combined_text and (
        "uncertain" in combined_text
        or "not yet clear" in combined_text
        or "figuring out" in combined_text
    ):
        uncertainty.append("Budget or timing is uncertain.")

    if company.is_competing_agency:
        uncertainty.append(
            "The lead may be a competitor or partnership inquiry rather than a normal buying opportunity."
        )

    return uncertainty


def _combined_company_text(company: EnrichedCompany) -> str:
    parts = (
        company.growth_signals
        + company.pain_signals
        + company.risk_signals
        + company.evidence
    )
    return " ".join(parts).lower()


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))