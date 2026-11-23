"""Stage 01 — routing tickets to the right intent.

Read `stages/01_classify/README.md` first.

You implement one function. The reader of this file is the rest of the pipeline: stage 02
retrieves policy for the intent you return, stage 03 drafts a reply from it, and stage 04
decides which actions are allowed. A wrong intent here is a wrong policy there.

Return one of the six labels in `triage.tickets.INTENTS`.
"""

from __future__ import annotations

from .tickets import Ticket


def classify(ticket: Ticket) -> str:
    """Return the intent of one ticket.

    Contract:
      - return exactly one of: refund, shipping, billing, account, cancel, other
      - fall back to "other" when nothing matches
      - be deterministic: the same message always produces the same label
      - do not read `ticket.intent`; that field is the answer key and is absent in
        production

    The baseline in `baselines.py` is a first-match keyword scan and it scores 0.785 macro-F1 on the development split. Two failure modes to design against:

      1. **Order dependence.** A message can contain words from several intents
         ("please cancel order 8713 before it ships"). Choosing the first list that
         matches makes the answer a function of your code's layout.
      2. **Generic words.** "account", "charge" and "price" appear across intents and
         carry little information. Specific phrases such as "auto-renew" or
         "two-factor" carry a lot.

    A scoring approach rather than an ordering approach fixes both: count matches per
    intent, give specific phrases more weight than generic words, and take the maximum.
    """
    raise NotImplementedError("stage 01: implement classify")
