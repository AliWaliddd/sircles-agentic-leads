from __future__ import annotations

from sircles_agents.llm import LLMClient, MockLLMClient
from sircles_agents.models import (
    Disposition,
    LeadIntelligenceResult,
    OutreachArtifact,
    ResolutionDecision,
)


class SDROutreachAgent:
    """
    Drafts personalized first-touch outreach for qualified pursue leads.

    Important safety rule:
    This agent refuses to run unless the resolved disposition is pursue.
    That prevents accidental outreach for nurture, skip, or human-review leads.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or MockLLMClient()

    def run(
        self,
        lead_intelligence: LeadIntelligenceResult,
        resolution: ResolutionDecision,
    ) -> OutreachArtifact:
        if resolution.final_disposition != Disposition.PURSUE:
            raise ValueError(
                "SDR Outreach Agent can only draft outreach when final disposition is pursue."
            )

        raw_lead = lead_intelligence.raw_lead
        contact = lead_intelligence.contact
        company = lead_intelligence.company

        primary_growth_signal = _first_or_default(
            company.growth_signals,
            "your team appears to be in a growth phase",
        )
        primary_pain_signal = _first_or_default(
            company.pain_signals,
            "improving marketing performance",
        )

        growth_phrase = _sentence_fragment(primary_growth_signal)
        pain_phrase = _pain_phrase_for_email(primary_pain_signal)
        pain_topic = _pain_topic_for_linkedin(primary_pain_signal)

        fallback_subject = f"{raw_lead.first_name}, growth support for {company.company_name}"

        fallback_email_body = (
            f"Hi {raw_lead.first_name},\n\n"
            f"I noticed that {company.company_name} is working through a growth moment: "
            f"{growth_phrase}.\n\n"
            f"Your note about {pain_phrase} stood out because those are exactly "
            f"the kinds of situations where a focused agency partner can help clarify positioning, "
            f"prioritize campaigns, and turn early demand signals into a repeatable acquisition motion.\n\n"
            f"Given your role as {contact.role_title}, I thought it may be useful to compare notes "
            f"on what you are trying to solve and whether Sircles could help.\n\n"
            f"Would you be open to a short conversation next week?\n\n"
            f"Best,\n"
            f"Sircles Team"
        )

        fallback_linkedin_note = (
            f"Hi {raw_lead.first_name}, saw that {company.company_name} is focused on "
            f"{pain_topic}. Thought it could be useful to connect and compare notes on growth strategy."
        )

        grounding_metadata = {
            "lead_id": raw_lead.lead_id,
            "contact_role": contact.role_title,
            "company": company.company_name,
            "industry": company.industry,
            "growth_signal": primary_growth_signal,
            "pain_signal": primary_pain_signal,
            "final_disposition": resolution.final_disposition.value,
        }

        subject_response = self._llm_client.complete(
            prompt_name="sdr_email_subject",
            system_prompt=(
                "Write a concise first-touch sales email subject for a qualified "
                "marketing agency lead. Stay grounded in the provided facts."
            ),
            user_prompt=str(grounding_metadata),
            fallback=fallback_subject,
            metadata=grounding_metadata,
        )

        email_response = self._llm_client.complete(
            prompt_name="sdr_email_body",
            system_prompt=(
                "Write a personalized first-touch email for a marketing agency. "
                "Use only the provided facts, avoid overclaiming, and do not send anything."
            ),
            user_prompt=str(grounding_metadata),
            fallback=fallback_email_body,
            metadata=grounding_metadata,
        )

        linkedin_response = self._llm_client.complete(
            prompt_name="sdr_linkedin_note",
            system_prompt=(
                "Write a short LinkedIn connection note for a qualified marketing "
                "agency lead. Keep it concise and grounded."
            ),
            user_prompt=str(grounding_metadata),
            fallback=fallback_linkedin_note,
            metadata=grounding_metadata,
        )

        grounded_in = [
            f"Contact role: {contact.role_title}",
            f"Company industry: {company.industry}",
            f"Company size: {company.employee_count} employees",
            f"Growth signal: {primary_growth_signal}",
            f"Pain signal: {primary_pain_signal}",
            f"Resolved disposition: {resolution.final_disposition.value}",
        ]

        return OutreachArtifact(
            subject=subject_response.text,
            email_body=email_response.text,
            linkedin_note=linkedin_response.text,
            grounded_in=grounded_in,
            llm_provider=email_response.provider,
            llm_model=email_response.model,
        )


def _first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def _clean_fragment(value: str) -> str:
    return value.strip().rstrip(".").strip()


def _lower_first(value: str) -> str:
    if not value:
        return value
    return value[0].lower() + value[1:]


def _sentence_fragment(value: str) -> str:
    return _lower_first(_clean_fragment(value))


def _pain_phrase_for_email(value: str) -> str:
    """
    Convert short enrichment bullets into a grammatically usable phrase.

    Example:
    "Needs positioning support." -> "needing positioning support"
    """
    fragment = _clean_fragment(value)
    lower = fragment.lower()

    if lower.startswith("needs "):
        return "needing " + fragment[6:]

    if lower.startswith("wants "):
        return "wanting " + fragment[6:]

    return _lower_first(fragment)


def _pain_topic_for_linkedin(value: str) -> str:
    """
    Convert short enrichment bullets into a concise LinkedIn topic.

    Example:
    "Needs positioning support." -> "positioning support"
    """
    fragment = _clean_fragment(value)
    lower = fragment.lower()

    if lower.startswith("needs "):
        return _lower_first(fragment[6:])

    if lower.startswith("wants "):
        return _lower_first(fragment[6:])

    return _lower_first(fragment)