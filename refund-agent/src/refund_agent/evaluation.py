import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from refund_agent.intent import CustomerIntent, IntentResult
from refund_agent.models import RefundStatus
from refund_agent.workflow import process_refund


def load_cases(path: Path) -> list[dict]:
    """Load evaluation cases from a JSONL file."""
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def run_evaluation(
    cases: list[dict],
) -> dict:
    """Evaluate workflow decisions using known, fixed intents."""

    results = []

    for case in cases:
        intent_result = IntentResult(
            intent=CustomerIntent(case["intent"]),
            order_id=case["order_id"],
            summary=case["summary"],
        )

        # Isolate workflow/policy behavior from LLM variability.
        with patch(
            "refund_agent.workflow.extract_intent",
            return_value=intent_result,
        ):
            decision = process_refund(
                case["customer_message"],
                today=date(2026, 10, 24),
            )

        expected = case["expected_status"]
        actual = decision.status.value

        results.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": actual,
                "passed": expected == actual,
            }
        )

    total = len(results)
    passed = sum(result["passed"] for result in results)

    # A false approval occurs when a case expected to be rejected
    # or escalated is actually approved.
    false_approvals = sum(
        result["actual"] == "approved" and result["expected"] != "approved"
        for result in results
    )

    expected_escalations = [
        result for result in results if result["expected"] == "escalated"
    ]
    correctly_escalated = sum(
        result["actual"] == "escalated" for result in expected_escalations
    )

    escalation_recall = (
        correctly_escalated / len(expected_escalations) if expected_escalations else 1.0
    )

    return {
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": passed / total if total else 0.0,
        "false_approvals": false_approvals,
        "escalation_recall": escalation_recall,
        "results": results,
    }
