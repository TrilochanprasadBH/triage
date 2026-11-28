# Field notes

What production teams published, what it means for an agent that can act, and what we did
not build.

Same rules as `ragkit/FIELD-NOTES.md`: cite what you read, include results that contradict
the vendor, and end each entry with the deliberate omission.

---

## Classification and gating

### 1. Decision models — PostHog (November 2026)

**Source.** posthog.com/newsletter/decision-models

**What they did.** Used small calibrated classifiers instead of LLMs for narrow
questions: up to 444.6x cheaper and 193.6x faster. Gated expensive calls with two yes/no
questions, which cut false flags to about a tenth of a single question; 98.7% of
items skipped the LLM entirely. Also used them as model routers. Thresholds were set by
error cost: 0.4 where a false negative was dangerous, 0.85 where a false positive
annoyed a user. A failure worth knowing: ranking PR-review findings with a decision model
gave AUC 0.52, no better than chance, so open-ended ranking stayed with an LLM.

**What it means.** Routing and gating are classification problems, and narrow questions
beat compound ones. Two narrow checks outperform one broad check on both cost and error
rate.

**In this project.** Stage 01 is the narrow classifier at the front of the pipeline. Not
built: a hosted decision model, so the classifier is a keyword rule set with the same
interface.

### 2. Building effective agents — Anthropic (December 2024)

**Source.** anthropic.com/engineering/building-effective-agents

**What they did.** Distinguished workflows from agents, and found the successful
implementations used simple composable patterns. Emphasised the agent-computer interface:
tool documentation and testing matter as much as prompting.

**What it means.** A ticket pipeline is a workflow until it demonstrably needs to make its
own decisions. Stages 01 to 03 are a fixed path; stage 04 is where choice enters, and only
for the actions that need it.

**In this project.** The pipeline is a workflow with one decision point (which action to
propose), rather than a free-running agent.

---

## Acting safely

### 3. Cloud agents runtime — PostHog (2026)

**Source.** posthog.com/blog/cloud-agents-runtime

**What they did.** Ran agent tasks in sandboxes with the allowlist enforced in the
network layer on every run: "Once the agent boots, a blocked domain stays blocked down at
the network level, however nicely the prompt asks."

**What it means.** The strongest guardrail is the one the model cannot negotiate with. A
prompt instruction is a request; an allowlist in the tool layer is a constraint.

**In this project.** Stage 04 puts the approval gate in the tool registry, not in the
prompt. The model may propose any action; the registry decides what runs.

### 4. Well-Architected Agentic AI Lens — AWS

**Source.** docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens

**What they did.** Recommended explicit human-in-the-loop escalation for ambiguous or
high-consequence actions, deterministic validation of structured output, and per-stage
latency and cost budgets.

**What it means.** Escalation is a designed path, not an error path. A system that only
has "answer" and "crash" will eventually answer when it should have escalated.

**In this project.** `needs_approval` is a first-class outcome in stage 04, scored as a
success when the action is dangerous.

### 5. Eight learnings from a year of agents — PostHog (November 2025)

**Source.** posthog.com/blog/8-learnings-from-1-year-of-agents-posthog-ai

**What they did.** Reported that graph orchestration suited free-form work badly; moved to
a single loop with one message history and a `todo_write` tool whose only job is to restate
what remains. Also argued against framework lock-in.

**What it means.** State that helps the model track its own progress beats structure that
constrains its path.

**In this project.** Stage 05's audit trail is the same idea, recorded by the system rather
than the model: the log is the source of truth, not the model's summary of what it did.

---

## Evaluating process

### 6. Multi-agent research system — Anthropic (June 2025)

**Source.** anthropic.com/research/multi-agent-research-system

**What they did.** Argued that agent evaluation cannot compare against a prescribed
sequence of steps, because valid runs take different routes; the right frame is whether
the outcome was good and the process reasonable.

**What it means.** Trajectory scoring needs a rubric with precedence, not an expected path.

**In this project.** Stage 06 implements the rubric: safety overrides, outcome scores,
process penalties, floor at zero.

### 7. Multi-agents: what is actually working — Cognition (April 2026)

**Source.** cognition.com/blog/multi-agents-working

**What they did.** After arguing against multi-agent systems in 2025, reported that a
narrow class works: several agents contributing intelligence while **writes stay
single-threaded**.

**What it means.** Parallelism is safe for reading and review, dangerous for acting.

**In this project.** Not built. `scout` is where sub-agents appear, and only for research
that reads.

### 8. Production RAG evaluation — Oracle developers blog (July 2026)

**Source.** blogs.oracle.com/developers/production-rag-evaluation-keyword-vector-sql-or-hybrid-search
**What they did.** Two posts on evaluating RAG that runs in production. Their rule is
"production RAG evaluation separates retrieval quality from answer quality", and their
takeaway list for retrieval is "test freshness, tenant isolation, metadata filters, exact
identifiers, citations, and abstention alongside average retrieval metrics" — a high
average retrieval score "is not enough if the system fails exact identifiers".
**What it means.** Retrieval has its own failure modes and its own metrics; a single
blended score hides them. The average is the number that flatters and the exact-identifier
failure is the one customers hit.
**In this project.** Stage 02 reports intent recall and specific-rule recall separately
for exactly this reason: the domain is found every time, the exact rule is at rank 1 only
58.3% of the time, and only the second number bounds what stage 03 can quote. Not built:
freshness, tenant isolation, and abstention checks; the escalation path in stage 03 is the
abstention shape, but no ticket in the corpus exercises it.

---

## Releasing changes

### 9. Prompt CI/CD — Braintrust (September 2026)

**Source.** braintrust.dev/articles/how-to-build-a-prompt-ci-cd-pipeline
**What they did.** Described a release pipeline for prompt changes: each candidate version
is evaluated against the current production version on a fixed dataset, with quality,
latency, and cost measured in the same run. Release-critical scorers have hard thresholds
that block promotion; secondary scores get tolerance bands. The rollback trigger is set
before rollout begins, a staged rollout limits initial exposure, and confirmed production
failures are promoted back into the evaluation dataset as regression cases. They cite
Notion running regression evaluations before introducing model changes, with 70 engineers
shipping frontier models within hours.
**What it means.** A prompt or template change is a release, and the discipline is the
same as code: a pinned version, a measured comparison against the incumbent, a threshold
decided in advance, and a path back.
**In this project.** Stage 07 is the decision core of that pipeline, offline: a stable
assignment, a control arm, a tolerance derived from the standard error, and one executable
decision. Not built: environments, online scoring on live traffic, and the
production-to-dataset feedback loop; each needs infrastructure this repository does not
ship.


---

## What we deliberately did not build

| technique | why not here | when you would |
| --- | --- | --- |
| Hosted decision model for intent | needs a network call | queue volume where a classifier pays for itself |
| Embedding-based intent matching | 74 tickets do not justify it | thousands of intents, or heavy slang |
| Multi-agent ticket routing | one classifier is enough | separate teams with separate policies |
| Automated refunds without approval | unsafe by design | small amounts under a written limit, with audit |
