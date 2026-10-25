from collections.abc import Callable
from typing import Any

from refund_agent.intent import IntentResult


def evaluate_intent_cases(
    cases: list[dict[str, Any]],
    extractor: Callable[[str], IntentResult],
) -> dict[str, Any]:
    results = []

    for case in cases:
        actual = extractor(case["customer_message"])

        expected_intent = case["expected_intent"]
        expected_order_id = case["expected_order_id"]
        expected_reason = case["expected_reason"]

        actual_intent = actual.intent.value
        actual_order_id = actual.order_id
        actual_reason = actual.reason.value

        intent_correct = actual_intent == expected_intent
        order_id_correct = actual_order_id == expected_order_id
        reason_correct = actual_reason == expected_reason

        # A critical error is either a false refund classification
        # or an invented order ID where none was expected.
        false_refund_classification = (
            expected_intent != "refund_request" and actual_intent == "refund_request"
        )
        invented_order_id = expected_order_id is None and actual_order_id is not None

        results.append(
            {
                "id": case["id"],
                "expected_intent": expected_intent,
                "actual_intent": actual_intent,
                "intent_correct": intent_correct,
                "expected_order_id": expected_order_id,
                "actual_order_id": actual_order_id,
                "order_id_correct": order_id_correct,
                "expected_reason": expected_reason,
                "actual_reason": actual_reason,
                "reason_correct": reason_correct,
                "false_refund_classification": false_refund_classification,
                "invented_order_id": invented_order_id,
            }
        )

    total = len(results)

    def accuracy(field: str) -> float:
        if total == 0:
            return 0.0
        return sum(row[field] for row in results) / total

    critical_errors = sum(
        row["false_refund_classification"] or row["invented_order_id"]
        for row in results
    )

    return {
        "total_cases": total,
        "intent_accuracy": accuracy("intent_correct"),
        "order_id_accuracy": accuracy("order_id_correct"),
        "reason_accuracy": accuracy("reason_correct"),
        "critical_errors": critical_errors,
        "results": results,
    }
