from __future__ import annotations

from collections.abc import Callable

from sircles_agents.models import (
    EnrichedCompany,
    EnrichedContact,
    LeadIntelligenceResult,
    LeadScore,
    RawLead,
)
from sircles_agents.scoring import score_lead
from sircles_agents.tools.mock_enrichment import enrich_company, enrich_contact


class LeadIntelligenceAgent:
    """
    Enriches a raw inbound lead and scores it against the ICP.

    This agent owns the first structured judgment in the workflow:
    - contact enrichment
    - company enrichment
    - transparent ICP scoring
    - initial disposition proposal

    The final disposition is not decided here. The orchestrator will later
    trigger a debate before any outreach is drafted.
    """

    def __init__(
        self,
        contact_enricher: Callable[[RawLead], EnrichedContact] = enrich_contact,
        company_enricher: Callable[[RawLead], EnrichedCompany] = enrich_company,
        scorer: Callable[[EnrichedContact, EnrichedCompany], LeadScore] = score_lead,
    ) -> None:
        self._contact_enricher = contact_enricher
        self._company_enricher = company_enricher
        self._scorer = scorer

    def run(self, raw_lead: RawLead) -> LeadIntelligenceResult:
        """
        Run the Lead Intelligence Agent on one raw lead.

        Returns a structured result that downstream agents can consume without
        needing to know anything about the enrichment or scoring implementation.
        """
        contact = self._contact_enricher(raw_lead)
        company = self._company_enricher(raw_lead)
        score = self._scorer(contact, company)

        return LeadIntelligenceResult(
            raw_lead=raw_lead,
            contact=contact,
            company=company,
            score=score,
        )


def run_lead_intelligence(raw_lead: RawLead) -> LeadIntelligenceResult:
    """
    Convenience function for simple usage and tests.
    """
    return LeadIntelligenceAgent().run(raw_lead)