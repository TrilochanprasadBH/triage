# Stage 02 — Retrieving the policy that applies

```sh
python stages/02_policy/test_stage02.py
```

Sixteen tests, thirteen failing at first.

---

## What you will build

An index over 24 policy sections, and a search that turns a ticket into the three rules
most likely to apply.

## Why this step is next

Stage 01 produced a label. A label is not a decision. To tell a customer "you can still
cancel, but only until dispatch", you need the rule that says so, and you need to be able
to quote it.

That is the difference between a classifier and an assistant: every claim it makes is
traceable to a written policy. Stage 03 drafts from these sections, and stage 06 scores
whether the draft stayed inside them.

## The idea

**You already know the answer to half the problem.** Stage 01 decided this is a
cancellation. You do not need to rediscover that from the message text. Every section
carries its own intent tag, and a refund rule almost never applies to a shipping question.

That is metadata pre-filtering, and it is one of the cheapest quality gains available in
retrieval. It is also the thing most implementations forget: they embed documents and
search text, and they throw away structured fields they were given for free.

**Why not filter outright.** A hard filter to `section.intent == ticket.intent` looks
tempting and is wrong in two situations. The classifier is not perfect, so an
occasionally wrong intent would make the right rule unreachable. And some messages
genuinely span domains: "cancel the order I was charged for" is a cancellation that needs
a billing rule. A prior lets strong text evidence override the label; a filter does not.

So the intent contributes a fixed additive boost, and text similarity does the rest.

**Why additive, not multiplicative.** Multiplying a BM25 score by a constant amplifies
sections that already score highly, which compounds an existing advantage. Adding a
constant treats the prior as a fixed amount of evidence, which is what it is.

**Prefix matching.** "Cancel my subscription" failed during development because the policy
says "cancellation" and the message says "cancel". Those are the same word to a reader and
different tokens to a search engine. Matching any section token that starts with a query
token of five characters or more fixes the family: cancel, cancellation, cancelling;
deliver, delivery, delivered.

The length floor matters. Two or three characters match far too much: "ord" would match
"order", "ordinary" and "coordinate".

## The measurement

74 tickets, 24 sections, gold label is "a section tagged with the ticket's intent".

| configuration | recall@3 | intent coherence |
| --- | --- | --- |
| baseline: shared words, no idf, no intent | 71.6% | 31.9% |
| text only: BM25 + prefix matching, no intent | 81.0% | 36.7% |
| **intent prior (3.0) + BM25 + prefixes** | **100%** | **75.7%** |

And the sweep on the boost, which is the interesting part:

| boost | recall@3 | coherence |
| --- | --- | --- |
| 0.0 | 81% | 36.7% |
| 1.5 | 93% | 55.0% |
| 3.0 (default) | 100% | 75.7% |
| 6.0 | 100% | 87.2% |
| 12.0 | 100% | 91.7% |

Three things to notice.

**Text alone was already better than the baseline** (81% vs 71.6%), from idf and length
normalisation alone. The prior bought the remaining nineteen points.

**Recall saturates at 3.0 and coherence keeps climbing.** That is the trade-off: past a
point, more prior means fewer cross-domain sections, which is good for drafting (the
model cannot quote the wrong rule) and bad if your classifier is wrong.

**Coherence never reaches 100%.** Some messages contain no vocabulary from their own
intent, so the only sections that score at all are from another domain. That is a property
of the corpus, and it is why the boost stays a prior rather than becoming a filter.

## Do this

1. Read `src/triage/retrieval.py`.
2. Implement `PolicyIndex.__init__`: term counts, lengths, document frequencies.
3. Implement `idf`.
4. Implement `search`: BM25 over the message, prefix fallback, intent boost, sorted output.
5. Run the report and the tests.
6. Change `INTENT_BOOST` to 0 and to 12 and run the report twice. Look at what each does.

```sh
python evals/report_policy.py --show-errors 4
python stages/02_policy/test_stage02.py
```

## Check yourself

Expected: all sixteen tests pass, recall@3 at or above 0.90, coherence at or above 0.65.

If recall is high but coherence is near 30%, you have not applied the intent. If both are
low, check that you are indexing the title as well as the text: the title carries the rule
name.

## If you are stuck

**Hint 1.** Build the index in one pass: for each section, tokenise `title + text`, store
the counts, and increment a document-frequency counter per distinct term.

**Hint 2.** Apply the prefix fallback only when the exact term has no match, and only for
tokens of five characters or more. Doing it always is slower and noisier.

**Hint 3.** Sort with `(-score, section.id)` so ties are deterministic. The tests compare
exact output on repeated runs.

## What a senior would notice

**Whether the boost is documented as a trade-off.** `3.0` is not a law. The sweep in this
lesson shows what it buys and what it costs, and a comment next to the constant should
carry that reasoning, not just the number.

**Whether structured metadata is used for anything else.** Intent is one field. A real
policy store also has effective dates, jurisdictions, and plan tiers. Every one of them is
a cheap pre-filter and every one of them is usually ignored.

**Whether retrieval is evaluated separately from the answer.** Recall@3 here is a
retrieval number: it says the right rule was available, not that the reply used it. Stage
03 measures the reply, and the two failures need different fixes. That separation is the
same one `ragkit` stage 07 insisted on.
