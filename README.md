# triage

A support agent that reads a customer message, routes it to the right policy, drafts a
reply, and decides what it is allowed to do without a human.

This repository is a **course and a product at the same time**. You build it in seven
stages; six are complete. When all seven exist you have a running service with an
approval gate, an audit trail, and a trajectory eval that scores whole agent runs rather
than final answers.

---

## What it does

```
message  ->  intent  ->  policy passages  ->  draft reply
         ->  proposed actions  ->  approval gate  ->  send or escalate
         ->  every step recorded, replayable
```

## Why this project exists

`ragkit` answered questions. This project *acts*: it can refund, delete, or email. The
moment a system can act, three new problems appear and none of them are about model
quality.

- **Authorisation.** A model can request a refund. It cannot approve one.
- **Auditability.** When a refund goes out at 3am, someone has to reconstruct why.
- **Evaluation of process.** A correct answer reached by an unauthorised action is a
  failure, and a final-answer metric cannot see it.

## Requirements

- Python 3.10 or newer
- No third-party packages for stages 1 to 6

## Quick start

```sh
python3 scripts/status.py
open GUIDE.md
python3 stages/01_classify/test_stage01.py
```

## How to work in this repo

- **You write code in `src/triage/`.** Three modules are stubs with contracts
  (`classify`, `retrieval`, `compose`); everything else is given, including the baselines,
  the checks, and the metrics.
- **`reference/triage/` is a complete implementation.** Read it after you have tried.
- **`stages/NN_name/` holds the lesson and the tests.** The tests are the specification.
- `IMPL=reference python3 stages/01_classify/test_stage01.py` checks the reference.

## Results

| stage | capability | measure | result |
| --- | --- | --- | --- |
| 01 | intent classification | macro-F1, dev and held out | baseline 0.785 / 0.776; reference 1.000 / 1.000 |
| 02 | policy retrieval | intent recall@3, specific rule@1 | baseline 71.6%/31.9%; reference **100%**, specific rule **58.3%** (top-3 87.5%) |
| 03 | drafting | specificity, compliance, focus | **64.7%** specific (66.7% held out), 100% compliant, 100% focused |
| 04 | actions and approval | proposal accuracy, unauthorised actions | **100.0%** proposed, **0** unauthorised |
| 05 | audit trail | completeness, explainability, replay | **100%**, 100%, 74/74 replay |
| 06 | trajectory eval | separation, review rate | mean **8.68**, separation **+2.65**, 27/74 reviewed, 0 unsafe |
| 07 | release safety | canary detection rate | planned |

Read the stage 01 note before trusting the 1.000. It is an artefact of how the reference
was written, and the lesson says so. Stage 02's 100% is intent-level recall on a 24-section
corpus, which is a small search space by design; the specific-rule column is the honest one,
and it is the ceiling stage 03 inherits.

## Layout

```
src/triage/         you implement here
reference/triage/   a complete implementation
stages/NN_name/     one lesson and one test suite per stage
evals/              74 labelled tickets, and the report script
scripts/            status and helpers
GUIDE.md            the course
FIELD-NOTES.md      sourced production practice
NOTES.md            your log
```

## Data

`evals/tickets.jsonl` contains 74 support messages written for this project, split 52
development and 22 held out, across six intents, with a gold policy section for 72 of
them. The corpus is authored rather than vendored, deliberately: the stages need exact,
known ambiguities ("cancel my order" versus "cancel my subscription"), and no public
corpus contains the ones these exercises teach. A vendored corpus is still the better
default for text-heavy projects; see `ragkit` for that pattern. `ragkit` stage 07 also
explains why 22 held-out questions cannot support a precise claim.
