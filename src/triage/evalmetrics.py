"""Multi-class metrics, given so that the stage can focus on the classifier.

Accuracy is not enough here. The classes are balanced by construction, but the failure
that matters is not "how many were right"; it is "which classes get confused with which".
That is what precision, recall and the confusion matrix show.

Macro-F1 is the mean of per-class F1. It weights a rare class as heavily as a common one,
which is the correct choice when every intent has similar operational cost: a misrouted
account question is as expensive as a misrouted refund.
"""

from __future__ import annotations

from collections import Counter


def confusion(
    labels: list[str], predictions: list[str], intents: tuple[str, ...]
) -> dict[tuple[str, str], int]:
    """Count (truth, predicted) pairs, including the zero cells."""
    counts = Counter(zip(labels, predictions))
    return {(truth, predicted): counts.get((truth, predicted), 0)
            for truth in intents for predicted in intents}


def per_class(
    labels: list[str], predictions: list[str], intents: tuple[str, ...]
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for intent in intents:
        true_positive = sum(
            1 for truth, predicted in zip(labels, predictions)
            if truth == intent and predicted == intent
        )
        predicted_positive = sum(1 for predicted in predictions if predicted == intent)
        actual_positive = sum(1 for truth in labels if truth == intent)

        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / actual_positive if actual_positive else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        out[intent] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": actual_positive,
        }
    return out


def macro_f1(
    labels: list[str], predictions: list[str], intents: tuple[str, ...]
) -> float:
    scores = per_class(labels, predictions, intents)
    return sum(scores[intent]["f1"] for intent in intents) / len(intents)


def accuracy(labels: list[str], predictions: list[str]) -> float:
    if not labels:
        return 0.0
    return sum(1 for a, b in zip(labels, predictions) if a == b) / len(labels)
