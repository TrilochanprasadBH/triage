# Stage 02 — Retrieving the policy that applies

```sh
python3 stages/02_policy/test_stage02.py
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
cancellation, and it does so with 0.785 macro-F1 at worst and 1.000 at best. You do not
need to rediscover the domain from the message text. Every section
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

**The two formulas you need.** Term weight is inverse document frequency:

```
idf(term) = log(1 + (N - df + 0.5) / (df + 0.5))
```

and a section's score is BM25 over the message, with `k1 = 1.5`, `b = 0.75`:

```
score += idf(term) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * length / average_length))
```

where `tf` is how often the term occurs in the section, `length` is the section's term
count, and `average_length` is the corpus mean.

**Titles count three times.** A section's title is the rule's name: "Duplicate charges",
"Lost parcels", "Invoice corrections". The title's terms are added to the body's counts
`TITLE_WEIGHT` times, and the weighted length grows by the same factor. That single change
lifts the specific rule to rank 1 from 54.2% to 58.3% over the 72 comparable tickets, which
is why stage 03 inherits a usable ceiling.

**Prefix matching.** "Cancel my subscription" failed during development because the policy
says "cancellation" and the message says "cancel". Those are the same word to a reader and
different tokens to a search engine. Matching any section token that starts with a query
token of five characters or more fixes the family: cancel, cancellation, cancelling;
deliver, delivery, delivered.

The length floor matters. Two or three characters match far too much: "ord" would match
"order", "ordinary" and "coordinate".

## The measurement

74 tickets, 24 sections, gold label is "a section tagged with the ticket's intent".

| configuration | intent recall@3 | coherence | specific rule@1 | specific rule@3 |
| --- | --- | --- | --- | --- |
| baseline: shared words, no idf, no intent | 71.6% | 31.9% | 31.9% | 50.0% |
| text only: BM25 + prefixes + titles, no intent | 82% | 38.1% | 44.4% | — |
| **intent prior (3.0) + BM25 + prefixes** | **100%** | **73.9%** | **58.3%** | **87.5%** |

And the sweep on the boost, which is the interesting part:

| boost | intent recall@3 | coherence | specific rule@1 |
| --- | --- | --- | --- |
| 0.0 | 82% | 38.1% | 44.4% |
| 1.5 | 93% | 53.7% | 52.8% |
| 3.0 (default) | 100% | 73.9% | 58.3% |
| 6.0 | 100% | 86.7% | 61.1% |
| 12.0 | 100% | 91.7% | 61.1% |

Three things to notice.

**Text alone was already better than the baseline** (82% vs 71.6%), from idf, length
normalisation and title weighting. The prior bought the remaining eighteen points.

**Recall saturates at 3.0 and coherence keeps climbing.** That is the trade-off: past a
point, more prior means fewer cross-domain sections, which is good for drafting (the
model cannot quote the wrong rule) and bad if your classifier is wrong.

**Coherence never reaches 100%.** Some messages contain no vocabulary from their own
intent, so the only sections that score at all are from another domain. That is a property
of the corpus, and it is why the boost stays a prior rather than becoming a filter.

**Intent recall of 100% is a coarse claim, and the last two columns show it.** The right
*domain* is retrieved every time; the right *specific rule* is at rank 1 only 58.3% of the
time, and in the top three 87.5%. That distinction matters immediately in stage 03: a
drafter can only quote a rule that was retrieved, so 87.5% is the ceiling for draft
specificity. Reporting only the intent number would have hidden the actual constraint.

Two tickets are excluded from the specific-rule columns: their governing rule lives in
another domain (a renewal question answered by the auto-renew rule, a deletion request
answered by the data-deletion rule). Stage 03 forbids cross-domain citations, so those two
cannot be won by construction. `evals/check_labels.py` verifies the remaining labels and
reports the exclusion.

## Field notes

From `FIELD-NOTES.md`:

- **Oracle's production RAG evaluation posts** insist retrieval be evaluated separately
  from generation, and that exact identifiers be tested explicitly. The two recall columns here
  are that instruction: intent recall says the domain was found, specific recall says the
  rule was, and only the second one bounds what stage 03 can quote.
- **AWS's agentic lens** recommends using hybrid retrieval and metadata filters "where the
  corpus and query mix justify them, rather than stacked by default". The intent prior is
  exactly that: a metadata field that costs nothing and is worth eighteen points here.
- **PostHog's decision models** make the same argument one level up: a cheap classifier in
  front of retrieval, with its output used as a filter.

## Do this

1. Read `src/triage/retrieval.py`.
2. Implement `PolicyIndex.__init__`: term counts, lengths, document frequencies.
3. Implement `idf`.
4. Implement `search`: BM25 over the message, prefix fallback, intent boost, sorted output.
5. Run the report and the tests.
6. Change `INTENT_BOOST` to 0 and to 12 and run the report twice. Look at what each does.
   The constant is at the top of `retrieval.py` with the trade-off in a comment.

```sh
python3 evals/report_policy.py --show-errors 4
python3 stages/02_policy/test_stage02.py
```

## Check yourself

Expected: all sixteen tests pass (the first run shows three errors, which block the other
thirteen), intent recall@3 at or above 0.90, coherence at or above 0.65.

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
