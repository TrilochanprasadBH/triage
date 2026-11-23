# Stage 01 — Routing tickets to the right intent

```sh
python stages/01_classify/test_stage01.py
```

Eleven tests, six of them failing at first.

---

## What you will build

A classifier that maps a customer message to one of six intents: refund, shipping,
billing, account, cancel, other.

## Why this step is next

Everything downstream depends on this label. Stage 02 retrieves policy *for the intent*,
stage 03 drafts a reply *from that policy*, and stage 04 decides which actions are
allowed *for that intent*. A refund question routed to billing gets a plausible reply about
invoices and the customer waits another day.

It is also the cheapest place to learn the habit that dominates the rest of the project:
**measure per class, not overall**.

## The idea

**What classification is.** You have a message and a fixed set of labels. You want a rule
that maps each message to one label. Here the labels are the six intents.

**Why the obvious implementation fails.** The baseline checks the intents in a fixed order
and returns the first one with a matching word:

```python
for intent in ("refund", "shipping", "billing", "account", "cancel"):
    if any(word in message for word in KEYWORDS[intent]):
        return intent
```

That works until a message contains words from two intents. "Please cancel order 8713
before it ships" contains `cancel` and `ships`. Whichever list you check first wins, so the
answer is a property of your code's layout, not of the message. In the baseline the
cancellation class has recall 0.22: eight of nine cancellations are misrouted, almost
entirely to shipping and billing.

The fix is to stop letting order decide and start accumulating evidence:

- score every intent
- give specific phrases more weight than generic words
- take the maximum
- fall back to `other` when everything scores zero

**Specific versus generic.** "auto-renew" can only mean cancellation. "account" appears in
account questions, billing questions and cancellation requests, so it is weak evidence.
Weighting phrases at 2 and generic words at 1 encodes that.

**Count a weak match once, not once per synonym.** This is subtle and it cost a real
error during development. A message saying "the delivery arrived" matches three overlapping
weak words for shipping (`delivery`, `deliver`, `arrived`), scoring 3, and beats a specific
`money back` phrase scoring 2. The customer wanted a refund. The rule is: a weak category
contributes one point if *any* of its words appear, because repetition inside a synonym
list is not additional evidence.

**Why macro-F1 and not accuracy.** Accuracy hides class-level failure. The baseline in this
stage has 78.5% accuracy and 0.22 recall on cancellations: it is right most of the time and
completely broken for one sixth of customers. Macro-F1 averages per-class F1, so a class
that fails counts as much as a class that succeeds.

**Precision and recall, in this context.** For cancellations, recall is the fraction of
real cancellations you caught; precision is the fraction of things you called cancellations
that really were. Missing a cancellation sends a customer who wants to leave into a refund
flow; a false cancellation sends a refund question to the churn team. Both are bad, in
different ways.

**Why the split exists.** The corpus has 52 development tickets and 22 held out. You tune
on development. The held-out number is what you report. The report script deliberately
shows development failures only: if you look at held-out failures and adjust your rules,
the held-out number stops being a test. That is the same discipline `ragkit` stage 07
introduced, applied earlier and more cheaply.

**An honest note about the reference.** `reference/triage/classify.py` scores 1.000 on both
splits. That is not a realistic result; it is what happens when someone writes phrase lists
after reading the whole corpus. A rule set you write from the development split alone will
land around 0.90 to 0.95, and that is the honest version. The lesson is in the method, not
in the perfect score.

## Do this

1. Read `src/triage/classify.py` and the contract in its docstring.
2. Run `python evals/report.py` to see the baseline and its confusions.
3. Read the development misclassifications. Note which are genuine ambiguity and which are
   rule bugs.
4. Write `classify` with weighted scoring.
5. Iterate on development only.
6. Run the tests. The held-out check is the one you cannot tune.

```sh
python evals/report.py --show-errors 8
python stages/01_classify/test_stage01.py
```

## Check yourself

Expected: all eleven tests pass. Development macro-F1 at or above 0.90, held-out at or
above 0.85.

The confusion matrix is the useful output. If `cancel -> shipping` appears, your ordering or
your weighting is wrong. If `refund -> billing` appears, you are counting `charged` as
strong evidence for billing when it is weak.

## If you are stuck

**Hint 1.** Build a `score(message, intent)` function and call it once per intent. Printing
the six scores for a misclassified ticket tells you immediately which rule is too strong.

**Hint 2.** Match on lowercased text, and prefer phrases over single words. "money back" is
one rule; "money" and "back" separately would fire on unrelated messages.

**Hint 3.** Ties are rare once strong phrases exist, but they must be resolved
deterministically. Pick a documented order and keep it.

## What a senior would notice

**Whether the classifier is inspectable.** A keyword model can be read, argued with, and
changed by a support lead. That is worth a point of macro-F1. When you replace it with a
model, keep the evaluation and the confusion matrix; they are how you justify the change.

**Whether `other` is a real class.** It is the fallback for everything unmatched, and its
precision matters: if `other` absorbs 30% of traffic, the pipeline is not routing, it is
guessing. Track that rate in production.

**Whether 22 held-out tickets is enough.** It is not. The interval on a proportion from 22
samples is roughly twenty points wide (`ragkit` stage 07 has the arithmetic). A real
deployment needs hundreds of labelled tickets, and the first month of production traffic is
how you get them.
