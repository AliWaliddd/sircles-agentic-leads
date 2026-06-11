from __future__ import annotations

import json
from pathlib import Path

from sircles_agents.models import CRMRecord


_CRM_OUTPUT_PATH = Path.cwd() / "traces" / "mock_crm_records.json"


def _read_existing_records() -> list[dict]:
    if not _CRM_OUTPUT_PATH.exists():
        return []

    with _CRM_OUTPUT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_records(records: list[dict]) -> None:
    _CRM_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _CRM_OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)


def upsert_crm_record(record: CRMRecord) -> CRMRecord:
    """
    Mock HubSpot upsert.

    This writes a structured CRM record to traces/mock_crm_records.json.
    If the lead already exists, it replaces that record. This mimics an
    idempotent CRM upsert without using a live API.
    """
    existing_records = _read_existing_records()
    record_as_dict = record.model_dump(mode="json")

    updated_records: list[dict] = []
    replaced = False

    for existing_record in existing_records:
        if existing_record.get("lead_id") == record.lead_id:
            updated_records.append(record_as_dict)
            replaced = True
        else:
            updated_records.append(existing_record)

    if not replaced:
        updated_records.append(record_as_dict)

    _write_records(updated_records)

    return record