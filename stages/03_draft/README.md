# Stage 03 — Drafting a reply

```sh
python stages/03_draft/test_stage03.py
```

Thirteen tests, five failing at first.

---

## What you will build

A function that turns a ticket and the retrieved policy sections into a reply a customer
could read: the rule quoted, a next step, the source cited, and no promise the company did
not make.

## Why this step is next

Stage 01 gave you a label. Stage 02 gave you rules. Neither is a reply.

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

| | specific | rule quoted | compliant | focused |
| --- | --- | --- | --- | --- |
| baseline: generic reply | 0.0% | 0.0% | 100% | 100% |
| **cited draft, dev** | **63.5%** | **63.5%** | **100%** | **100%** |
| cited draft, held out | 63.6% | 63.6% | 100% | 100% |

Two of the four numbers are absolute and two are not, and that is the honest shape of the
result.

**Compliance and focus are 100% by construction.** The drafter only ever quotes a section
it was given, and only from the ticket's domain. Those properties are guaranteed by the
code, not measured hopefully.

**Specificity is 63.5%, and the ceiling is 85.1%.** That ceiling is stage 02's specific
rule@3: the drafter can only quote a rule that was retrieved. The chooser converts 74.6% of
the available golds into a correct citation. The remaining gap is lexical selection among
candidates that talk about the same intent.

**Some of the misses are not errors.** "My package is stuck in transit" is labelled
`s1` (tracking) and the system cited `s2` (lost parcels). Both are defensible readings of
the policy. That is a labelling problem, not a system problem, and it is why real eval sets
need adjudication rather than one person's first judgment.

## Do this

1. Read `src/triage/compose.py`.
2. Handle the empty-candidate case: escalate, with no citation and no invented rule.
3. Choose a section from the candidates: prefer the ticket's intent, then weighted overlap
   with the title, then body overlap, then the original order.
4. Quote its first sentence verbatim.
5. Add a next step the customer can act on.
6. Run the tests, then the report.

```sh
python evals/report_draft.py --show-errors 6
python stages/03_draft/test_stage03.py
```

## Check yourself

Expected: all thirteen tests pass. Compliance and focus at 100%, specificity at or above
55%, and rule-quoted tracking specificity exactly, because a quotation is what it measures.

If compliance fails, search your template for the forbidden list in `checks.py`. The most
common accident is "immediately", which reads as helpful and is a promise.

## If you are stuck

**Hint 1.** Read three drafts by hand before writing anything. `python -c` with a single
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
