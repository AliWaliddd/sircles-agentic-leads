from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Disposition(str, Enum):
    """Final or proposed lead disposition."""

    PURSUE = "pursue"
    NURTURE = "nurture"
    SKIP = "skip"
    HUMAN_REVIEW = "human_review"


class DealStage(str, Enum):
    """Mock CRM deal stage."""

    NEW = "new"
    QUALIFIED = "qualified"
    NURTURE = "nurture"
    DISQUALIFIED = "disqualified"
    HUMAN_REVIEW = "human_review"


class AgentName(str, Enum):
    """Named actors in the workflow trace."""

    ORCHESTRATOR = "orchestrator"
    LEAD_INTELLIGENCE = "lead_intelligence_agent"
    PURSUIT_ADVOCATE = "pursuit_advocate_agent"
    RISK_SKEPTIC = "risk_skeptic_agent"
    SDR_OUTREACH = "sdr_outreach_agent"
    CRM_HYGIENE = "crm_hygiene_agent"


class RawLead(BaseModel):
    """
    The raw inbound lead before enrichment.

    This simulates what fetch_new_leads() would return from a lead scanner.
    """

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    first_name: str
    last_name: str
    email: str
    company_name: str
    role_title: str
    source: str = "website_form"
    message: str | None = None


class EnrichedContact(BaseModel):
    """
    Mock contact-level enrichment.

    In a real system, this might come from Apollo, Hunter, Clay, LinkedIn, etc.
    """

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    full_name: str
    email: str
    role_title: str
    seniority: str
    buyer_fit_score: int = Field(ge=0, le=100)
    linkedin_url: str | None = None
    evidence: list[str] = Field(default_factory=list)


class EnrichedCompany(BaseModel):
    """
    Mock company-level enrichment.

    This is where we represent ICP, budget proxy, growth signals, and risk.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str
    website: str | None = None
    industry: str
    employee_count: int | None = Field(default=None, ge=0)
    estimated_annual_revenue: str | None = None
    geography: str | None = None

    growth_signals: list[str] = Field(default_factory=list)
    pain_signals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)

    is_competing_agency: bool = False
    evidence: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """
    Transparent scoring rubric.

    Total score is intentionally explainable instead of hidden in one opaque LLM judgment.
    Positive scoring dimensions add up to 100 before risk penalties.
    """

    model_config = ConfigDict(extra="forbid")

    industry_fit: int = Field(ge=0, le=25)
    company_size_budget: int = Field(ge=0, le=20)
    growth_signal: int = Field(ge=0, le=15)
    buyer_fit: int = Field(ge=0, le=20)
    pain_signal: int = Field(ge=0, le=20)
    risk_penalty: int = Field(ge=-30, le=0)

    @property
    def raw_total(self) -> int:
        return (
            self.industry_fit
            + self.company_size_budget
            + self.growth_signal
            + self.buyer_fit
            + self.pain_signal
            + self.risk_penalty
        )

    @property
    def total(self) -> int:
        """
        Final score is clamped to 0–100.

        This prevents very poor leads from producing negative scores after
        risk penalties while keeping the raw_total available for debugging.
        """
        return max(0, min(100, self.raw_total))

class LeadScore(BaseModel):
    """
    The Lead Intelligence Agent's scoring output.
    """

    model_config = ConfigDict(extra="forbid")

    total_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    proposed_disposition: Disposition
    breakdown: ScoreBreakdown
    positive_evidence: list[str] = Field(default_factory=list)
    negative_evidence: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def total_score_should_match_breakdown(self) -> "LeadScore":
        """
        Keeps the displayed total honest.

        This runs after the full model is created, so it reliably checks the
        score against the full breakdown.
        """
        if self.total_score != self.breakdown.total:
            raise ValueError(
                f"total_score={self.total_score} does not match "
                f"breakdown total={self.breakdown.total}"
            )
        return self


class LeadIntelligenceResult(BaseModel):
    """
    Full output of the Lead Intelligence Agent.
    """

    model_config = ConfigDict(extra="forbid")

    raw_lead: RawLead
    contact: EnrichedContact
    company: EnrichedCompany
    score: LeadScore


class DebatePosition(BaseModel):
    """
    One agent's position in the debate.

    The assignment requires competing recommendations, confidence, and evidence.
    """

    model_config = ConfigDict(extra="forbid")

    agent: AgentName
    recommendation: Disposition
    confidence: float = Field(ge=0.0, le=1.0)
    thesis: str
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class ResolutionDecision(BaseModel):
    """
    The orchestrator's explicit resolution of the debate.

    This captures the winning recommendation, losing/dissenting positions,
    and the reason for the decision.
    """

    model_config = ConfigDict(extra="forbid")

    final_disposition: Disposition
    confidence: float = Field(ge=0.0, le=1.0)
    resolution_rule: str
    rationale: str
    winning_position: DebatePosition | None = None
    dissenting_positions: list[DebatePosition] = Field(default_factory=list)
    requires_human_review: bool = False
    human_review_reason: str | None = None


class OutreachArtifact(BaseModel):
    """
    Drafted outreach.

    This is only produced when the resolved disposition is pursue.
    No actual sending happens.
    """

    model_config = ConfigDict(extra="forbid")

    subject: str
    email_body: str
    linkedin_note: str
    grounded_in: list[str] = Field(default_factory=list)


class CRMRecord(BaseModel):
    """
    Mock HubSpot-style CRM record.
    """

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    contact_name: str
    email: str
    company_name: str
    role_title: str
    disposition: Disposition
    deal_stage: DealStage
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    human_review_flag: bool
    human_review_reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    outreach: OutreachArtifact | None = None


class TraceEvent(BaseModel):
    """
    One readable event in the run trace.
    """

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: AgentName
    action: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)


class FinalRunOutput(BaseModel):
    """
    Final artifact returned by the orchestrator for one lead.
    """

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    final_disposition: Disposition
    lead_intelligence: LeadIntelligenceResult
    debate_positions: list[DebatePosition]
    resolution: ResolutionDecision
    outreach: OutreachArtifact | None
    crm_record: CRMRecord
    trace: list[TraceEvent]