# triage

A support agent that reads a customer message, routes it to the right policy, drafts a
reply, and decides what it is allowed to do without a human.

This repository is a **course and a product at the same time**. You build it in seven
stages. At the end you have a running service with an approval gate, an audit trail, and
a trajectory eval that scores whole agent runs rather than final answers.

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
python scripts/status.py
open GUIDE.md
python stages/01_classify/test_stage01.py
```

## How to work in this repo

- **You write code in `src/triage/`.** Every function starts with `raise
  NotImplementedError` and a docstring stating the contract.
- **`reference/triage/` is a complete implementation.** Read it after you have tried.
- **`stages/NN_name/` holds the lesson and the tests.** The tests are the specification.
- `IMPL=reference python stages/01_classify/test_stage01.py` checks the reference.

## Results

| stage | capability | measure | result |
| --- | --- | --- | --- |
| 01 | intent classification | macro-F1, dev and held out | baseline 0.785 / 0.776; reference 1.000 / 1.000 |
| 02 | policy retrieval | recall@3 | not yet measured |
| 03 | drafting | policy compliance rate | not yet measured |
| 04 | actions and approval | unauthorised actions | not yet measured |
| 05 | audit trail | replay fidelity | not yet measured |
| 06 | trajectory eval | rubric agreement | not yet measured |
| 07 | release safety | canary detection rate | not yet measured |

Read the stage 01 note before trusting the 1.000. It is an artefact of how the reference
was written, and the lesson says so.

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
development and 22 held out, across six intents. They are a teaching set, not a
benchmark. `ragkit` stage 07 explains why 22 held-out questions cannot support a precise
claim.
