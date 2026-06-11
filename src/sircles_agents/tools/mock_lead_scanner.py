from __future__ import annotations

import json
from pathlib import Path

from sircles_agents.models import RawLead


_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "leads.json"


def _load_fixture() -> dict:
    with _FIXTURE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def fetch_new_leads() -> list[RawLead]:
    """
    Mock lead scanner.

    In production this could read from website forms, LinkedIn inbound,
    a CRM inbox, or another lead source. For the take-home, it returns
    deterministic fixture data.
    """
    data = _load_fixture()
    return [RawLead(**lead) for lead in data["raw_leads"]]


def fetch_lead_by_id(lead_id: str) -> RawLead:
    """
    Convenience helper for running one lead from the CLI.
    """
    leads = fetch_new_leads()

    for lead in leads:
        if lead.lead_id == lead_id:
            return lead

    available_ids = ", ".join(lead.lead_id for lead in leads)
    raise ValueError(f"Unknown lead_id '{lead_id}'. Available lead IDs: {available_ids}")