# Stage 03 — Drafting a reply

```sh
python3 stages/03_draft/test_stage03.py
```

Thirteen tests, five failing at first.

---

## What you will build

A function that turns a ticket and the retrieved policy sections into a reply a customer
could read: the rule quoted, a next step, the source cited, and no promise the company did
not make.

## Why this step is next

Stage 01 gave you a label at 0.785 macro-F1, and stage 02 gave you the specific rule at rank
one 58.3% of the time. Neither is a reply.

This is also the first stage where the pipeline produces something a customer sees, which
changes what "correct" means. A classifier can be wrong and nobody notices. A draft that
says "we will refund you today" is a commitment your company has to honour.

## The idea

**Four properties, four numbers.** A draft can fail in ways that have nothing to do with
each other:

| property | question | failure |
| --- | --- | --- |
| specific citation | did it quote the rule that governs this ticket | quotes the general rule for the domain |
| rule quoted | does the reply state that rule | paraphrases, or says nothing concrete |
| compliance | does it avoid promises the policy does not make | invents a guarantee |
| focus | are its citations from the right domain | quotes a billing rule at a refund question |

Blending these into one "quality score" would hide which one broke. A reply that is
compliant and empty scores 100% on compliance, which is exactly what the baseline
demonstrates.

**Quote the rule, do not paraphrase it.** A quotation can be checked against the policy by
the next person who reads the draft. A paraphrase drifts: "within 30 days" becomes "about a
month", and nobody can tell which rule the reply came from.

**Choosing among candidates is the real work.** Retrieval returns three sections ordered by
text similarity to the whole message. That ordering optimises for "which text overlaps
most", not for "which rule applies". A general rule for the same domain often outranks the
specific one, because it is longer and shares more words.

The fix has two parts. Retrieval now weights section titles three-fold, because the title
*is* the rule's name ("Duplicate charges", "Lost parcels"), and the drafter re-scores the
candidates with the same idea: title overlap counts three times body overlap, and the
ticket's intent is preferred.

**Escalate rather than improvise.** With no candidates, the honest reply is that a human
will take it. The tempting alternative is a generic acknowledgement, which is what the
baseline does, and it is why the baseline scores zero on rule coverage.

**Templates are a feature, not a shortcut.** Each intent gets a fixed opening, the rule, and
a concrete next step. The variability that matters is which rule is quoted, not how
creatively the greeting is worded. Consistency is also what makes the compliance check
possible.

## The measurement

74 tickets, 24 sections, gold is the specific section that governs each ticket.

| | specific | rule quoted | compliant | focused | escalated |
| --- | --- | --- | --- | --- | --- |
| baseline: generic reply (dev) | 0.0% | 0.0% | 100% | 100% | 0/51 |
| **cited draft, dev** | **64.7%** (CI 51–76) | **64.7%** | **100%** | **100%** | 0/51 |
| cited draft, held out | 66.7% (CI 45–83) | 66.7% | 100% | 100% | 0/21 |

72 of 74 tickets are scored. Two are excluded because their governing rule lives in another
domain, and this stage forbids cross-domain citations; `evals/check_labels.py` reports the
exclusion.

Two of the four numbers are absolute and two are not, and that is the honest shape of the
result.

**Compliance is 100% by construction; focus is 100% on this corpus.** The drafter only
quotes sections it was given, and the templates contain no banned phrase, so compliance is a
property of the code. Focus is weaker than it looks: `choose` prefers an in-domain candidate
but does not require one, and the draft cites exactly one section, so focus holds here only
because retrieval always puts an in-domain candidate in the top three. At fewer than three
results, or with a classifier that misfires, the guarantee lapses.

**Specificity is 64.7%, against a ceiling of 88.2% on the same split.** The ceiling is
stage 02's specific rule@3 for these 51 tickets. The chooser converts 73.3% of the golds it
is given into a correct citation; the rest of the gap is lexical selection among candidates
that all talk about the same intent.

**Escalation is exercised 0 times.** Every ticket retrieves at least one section, so the
escalation path is covered only by unit tests. That is a gap in the corpus, not in the code,
and the honest fix is two or three tickets with no vocabulary in common with any policy.

**Some of the misses are not errors.** "My package is stuck in transit" is labelled
`s1` (tracking) and the system cited `s2` (lost parcels). Both are defensible readings of
the policy. That is a labelling problem, not a system problem, and it is why real eval sets
need adjudication rather than one person's first judgment.

## Field notes

From `FIELD-NOTES.md`:

- **AWS's agentic lens** recommends deterministic validation of structured output and
  explicit human escalation for ambiguous actions. The compliance list and the escalation
  path are that instruction, implemented as code rather than as a prompt.
- **PostHog's decision models** are the reason the drafting step is a template rather than a
  model call: for a question with a known answer shape, a deterministic composer is cheaper,
  testable, and impossible to talk into an overpromise.
- Compliance as a banned-phrase list is a blunt instrument. It catches the failures this
  corpus produces and would miss a novel overpromise. A model-based check is the next step,
  and it belongs in an eval, not in the draft path.

## Do this

1. Read `src/triage/compose.py`.
2. Handle the empty-candidate case: escalate, with no citation and no invented rule.
3. Choose a section from the candidates: prefer the ticket's intent, then weighted overlap
   with the title, then body overlap, then the original order.
4. Quote its first sentence verbatim.
5. Add a next step the customer can act on.
6. Run the tests, then the report.

```sh
python3 evals/report_draft.py --show-errors 6
python3 stages/03_draft/test_stage03.py
```

## Check yourself

Expected: all thirteen tests pass (the first run shows five errors, which block the rest).
Compliance and focus at 100%, specificity at or above 55%, and rule-quoted equal to
specificity — both 64.7% — because a quotation is exactly what that check measures.

If compliance fails, search your template for the forbidden list in `checks.py`. The most
common accident is "immediately", which reads as helpful and is a promise.

## If you are stuck

**Hint 1.** Read three drafts by hand before writing anything. `python3 -c` with a single
ticket is enough; the failures are visible in the text.

**Hint 2.** `quotes_rule` compares the normalised first sentence as a substring. If it
fails, you paraphrased, or you quoted a different section than you cited.

**Hint 3.** Sort candidates with a tuple key whose first element is the intent match. Ties
then fall back to overlap and to retrieval order, deterministically.

## What a senior would notice

**Whether compliance is enforced or hoped for.** The check is a list of banned phrases in
code. A system that relies on the model "being careful" has no compliance guarantee, only a
compliance aspiration.

**Whether the template is owned by support, not engineering.** The words in these templates
are policy decisions. They belong to the people who own the policy, and the code should
make them easy to change without a deploy.

**Whether a quotation is what the customer sees.** Our draft quotes the policy verbatim,
which is checkable and slightly stiff. The production version usually rewrites the rule in
the customer's language and keeps the citation. That is a product decision, and it should be
made by looking at real replies, not by preference.
