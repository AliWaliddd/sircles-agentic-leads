# Design Note — Sircles Agentic Lead Workflow

## Framing the business problem

For a marketing agency like Sircles, inbound lead handling is not just an operations problem. A strong lead can become a multi-month retainer, while a careless first touch can waste team time, damage reputation, or permanently turn away a prospect. Because of that, the system should not simply maximize the number of leads pursued. It should make a careful judgment about fit, upside, risk, and confidence before any outreach is drafted.

I designed the workflow as a small team of specialized agents: a Lead Intelligence Agent, a Pursuit Advocate, a Risk Skeptic, an SDR Outreach Agent, a CRM Hygiene Agent, and an Orchestrator. The key design principle is “debate first.” Before outreach is drafted, two agents must produce competing recommendations, and the Orchestrator must resolve the disagreement explicitly.

## 1. Cost of being wrong

A false `pursue` has visible and hidden costs. It wastes SDR time, creates noisy CRM data, and can harm the agency’s reputation if the message feels irrelevant or careless. In the worst case, pursuing a competitor or strategically risky lead could expose positioning, sales process, or internal thinking.

A false `skip` is also expensive because the agency may lose a prospect that could become a high-value retainer. However, the asymmetry depends on the lead type. For a clear poor-fit lead, such as a student asking for free personal advice, the cost of a false pursue is higher than the cost of skipping. For a plausible but uncertain company, the safer middle path is usually `nurture` or `human_review`, not a forced skip.

This shaped the disposition logic: the system pursues only when score and confidence are high and risk is low. It skips only when poor fit is clear. Ambiguous or risky cases are either nurtured or escalated to a human.

## 2. What makes a lead worth pursuing

The scoring model is intentionally transparent rather than hidden in a single opaque LLM judgment. Leads are scored out of 100 using five positive dimensions and one risk penalty:

| Signal                      | Max Points |
| --------------------------- | ---------: |
| Industry fit                |         25 |
| Company size / budget proxy |         20 |
| Growth signal               |         15 |
| Buyer fit                   |         20 |
| Pain signal                 |         20 |
| Risk penalty                |    -30 max |

A strong pursue lead is one that fits the agency’s ICP, has enough company size to plausibly support a retainer, shows growth or urgency, has a buyer or strong champion as the contact, and expresses a marketing pain that Sircles can credibly help with. For example, the B2B SaaS VP of Growth lead scores highly because the company is growing, the role is commercially relevant, and the message mentions positioning, demand generation, and outbound campaigns.

Negative signals reduce or block pursuit. These include weak buyer fit, no company budget, vague buying intent, or competitor risk. A competing marketing agency may look relevant on the surface, but it is not treated like a normal lead because the risk profile is different.

## 3. Confidence to action

Confidence is separate from lead quality. A lead can be a poor fit with high confidence, or a promising lead with low confidence. The system estimates confidence based on the amount and clarity of enrichment data, the number of supporting signals, and the amount of ambiguity or risk.

The action policy is:

* `pursue`: high score, high confidence, and low risk
* `nurture`: moderate fit or upside, but not enough urgency for autonomous outreach
* `skip`: clear poor fit with enough confidence
* `human_review`: competitor risk, low confidence, or risk that should not be resolved automatically

The debate mechanism adds another safety layer. The Pursuit Advocate argues the commercial upside, while the Risk Skeptic argues the downside. The Orchestrator applies a deterministic resolution rule with hard risk vetoes. For example, the ambiguous competitor case is escalated to `human_review` even though the advocate sees possible partnership value.

## 4. Where this earns its keep

The system earns its keep by reducing the time spent triaging obvious leads and by making the reasoning behind each decision visible. A human team should not need to manually inspect every student inquiry, tiny no-budget request, or clearly qualified growth-stage SaaS lead. The system can handle the obvious cases and preserve human attention for the risky or ambiguous ones.

The biggest revenue impact is faster response to strong leads. If Sircles can identify and draft grounded first-touch outreach for qualified inbound leads quickly, the team has a better chance of starting valuable sales conversations. The biggest cost-saving impact is avoiding bad-fit follow-up and keeping the CRM clean.

If this worked well, I would next automate follow-up sequencing for qualified but unresponsive leads, add a lightweight human-review queue, and introduce learning from outcomes such as booked calls, closed-won deals, and disqualified reasons.

## Tradeoffs made

I used a deterministic mock LLM client instead of live LLM API calls. This makes the project easier to run, test, and defend without API keys. The downside is that the natural language generation and judgment are less flexible than a real LLM-based system. However, the architecture keeps a clear LLM interface, so a real provider could later replace the mock client without changing the agent contracts.

I also used a simple scoring rubric rather than a complex machine-learning model. This is appropriate for the take-home because the goal is to demonstrate business reasoning, debate, handoffs, and traceability, not to optimize a black-box predictor.

## What I would do with two more weeks

With more time, I would add:

1. A human-review dashboard showing the lead, debate positions, evidence, and recommended action.
2. Outcome tracking so the scoring weights can be adjusted based on real conversion data.
3. More realistic enrichment uncertainty, including conflicting data from multiple providers.
4. Provider-backed LLM outreach with stricter grounding checks, tone controls, and evaluation against real examples.
5. Integration tests around a larger fixture set covering edge cases such as vendors, job seekers, existing customers, and strategic partners.
6. A feedback loop where human overrides are recorded and used to improve future resolution rules.

## Where it breaks at scale

The current system is intentionally small and deterministic. At scale, several issues would appear. First, mocked enrichment is too clean; real data is incomplete, stale, duplicated, and sometimes contradictory. Second, the scoring rubric would need calibration against actual Sircles outcomes. Third, outreach quality would need stronger safeguards around hallucination, tone, brand voice, and compliance. Fourth, the system would need deduplication across contacts and companies so the same account is not handled inconsistently. Finally, human-review volume could become a bottleneck if escalation rules are too conservative.

The current design is therefore best understood as a reliable first slice: it demonstrates the end-to-end workflow, debate-first decision-making, recorded dissent, safe escalation, structured CRM handoff, and traceability.
