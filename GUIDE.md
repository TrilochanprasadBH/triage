# Guide

Seven stages. Each has a lesson in `stages/NN_name/README.md` and tests that define what
done means.

Read this page once. Then work one stage at a time.

---

## 1. How to work

For each stage:

1. Read the lesson, all of it, before writing code.
2. Run the tests and read the failures; they describe the contract.
3. Implement in `src/triage/`.
4. Run the tests until they pass.
5. Run the eval, and record the number in `README.md`.
6. Write three lines in `NOTES.md`.

If you are stuck for more than 30 minutes, read `reference/`. Diff it against yours, then
close it and rewrite your version from memory.

## 2. The stages

| stage | you build | the idea it teaches | ends with |
| --- | --- | --- | --- |
| 01 | intent classifier | classification is evidence accumulation, not first match | macro-F1 0.785 baseline → 1.000 reference, both splits |
| 02 | policy retrieval | a decision needs a citation to the rule it follows | recall@3 100%, coherence 76% |
| 03 | reply drafting | a draft is a claim, and claims have compliance rules | 100% compliant, 64.7% specific, ceiling 88% |
| 04 | actions and approval | the model may request; only a human may approve | zero unauthorised actions |
| 05 | audit trail | if it cannot be replayed, it did not happen | replay reproduces every decision |
| 06 | trajectory eval | score the process, not only the answer | agreement with a hidden rubric |
| 07 | release safety | a canary is how a bad prompt is caught on 1% instead of 100% | regression detected in the canary |

## 3. What you should be able to say after each stage

**After 01:** "Macro-F1 went from 0.785 to 1.000, and I report the held-out number
separately because a rule set tuned on one split is not a classifier."

**After 02:** "Every decision cites a policy passage. The intent I already knew was worth
eighteen points of recall@3 as a metadata prior, and it never became a hard filter because
my classifier is not perfect."

**After 03:** "Compliance is guaranteed in code. Specificity is 64.7% against a retrieval
ceiling of 88%, so I know the next hour belongs in retrieval, not in templates."

**After 04:** "Refunds and deletions require approval from outside the model. The model
asks; the code decides."

**After 05:** "Given a trace id I can replay the run and get the same decision, which is
what makes an incident reviewable."

**After 06:** "Trajectory scoring has a precedence order: safety overrides, outcome
scores, process penalises, floor at zero."

**After 07:** "A canary on a small share of traffic catches a regression before it reaches
everyone, and the rollback is one config value." *(Stage 07 is planned; this sentence is the
target, not a measured result.)*

## 4. The rules

**Never tune on the held-out split.** The report shows development errors only, on
purpose. If you look at held-out failures and adjust, the number stops being a test.

**Never let the model authorise an action.** Confirmation comes from a human, or from a
policy that a human wrote, never from the model's own output.

**Prefer the boring mechanism.** A decision list you can read beats a model you cannot
explain, until it measurably does not. Stage 01 is that comparison.

**Measure both errors.** Blocking a good action and allowing a bad one cost different
things; report them separately.

## 5. When you finish

Stages 01 to 03 are complete: classification, policy retrieval, and cited drafting. Stages
04 to 07 add the approval gate, the audit trail, the trajectory eval, and the canary. When
they exist, the finished system answers the part of the interview that `ragkit` cannot:
what happens when the software is allowed to *do* something.
