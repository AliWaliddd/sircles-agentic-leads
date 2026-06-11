from __future__ import annotations

import json
from pathlib import Path

from sircles_agents.models import EnrichedCompany, EnrichedContact, RawLead


_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "leads.json"


def _load_fixture() -> dict:
    with _FIXTURE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def enrich_contact(raw_lead: RawLead) -> EnrichedContact:
    """
    Mock contact enrichment.

    This stands in for Apollo, Clay, Hunter, LinkedIn, or similar enrichment
    tools without calling external APIs.
    """
    data = _load_fixture()
    contact_data = data["contact_enrichments"].get(raw_lead.lead_id)

    if contact_data is None:
        raise ValueError(f"No contact enrichment fixture found for lead_id={raw_lead.lead_id}")

    return EnrichedContact(**contact_data)


def enrich_company(raw_lead: RawLead) -> EnrichedCompany:
    """
    Mock company enrichment.

    This stands in for company-level enrichment from Apollo, Clay, or similar
    data providers.
    """
    data = _load_fixture()
    company_data = data["company_enrichments"].get(raw_lead.company_name)

    if company_data is None:
        raise ValueError(
            f"No company enrichment fixture found for company_name={raw_lead.company_name}"
        )

    return EnrichedCompany(**company_data)