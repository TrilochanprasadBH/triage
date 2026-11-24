"""A baseline scorer, given: everything is fine.

It returns 7 for every run. That is not a strawman; it is what a scorecard built from
"did anything crash" looks like, and it is why the report measures separation rather than
the average.

A constant scorer has a perfect mean and no signal.
"""

from __future__ import annotations

from .scoring import Score
from .tickets import Ticket


def always_seven(record: dict, ticket: Ticket) -> Score:
    return Score(score=7, breakdown={"constant": 7}, reasons=())
