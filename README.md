# Sircles Agentic Lead Workflow

Technical take-home implementation for the Sircles AI Agentic Engineer Internship.

This project implements a small, deterministic team of AI-style agents that handles an inbound-lead-to-first-touch workflow for a marketing agency. The focus is not just automation, but judgment: which leads are worth pursuing, how confident the system is, and when a human should step in.

The workflow follows the required sequence:

```text
intake → enrich → debate disposition → resolve & record → outreach if pursue → CRM → artifacts + trace

---

## Submission checklist

Required deliverables covered:

- Source code runnable from the README
- Mock tools for lead scanning, enrichment, and CRM upsert
- Four sample leads covering pursue, skip, nurture, and ambiguous human-review cases
- Architecture diagram showing agents, debate, orchestrator, and handoffs
- Debate-first mechanism before outreach
- Recorded dissent and escalation path
- JSON run traces for a clear pursue case and an ambiguous competitor case
- Tests for the resolution rule, agent contracts, outreach safety, CRM behavior, orchestrator, and CLI
- One-page design note in `design_note.md`