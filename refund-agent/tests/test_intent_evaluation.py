from refund_agent.intent import (
    CustomerIntent,
    IntentResult,
    RefundReason,
)
from refund_agent.intent_evaluation import evaluate_intent_cases


def test_evaluator_reports_correct_extraction():
    cases = [
        {
            "id": "test-1",
            "customer_message": "Refund order 4821",
            "expected_intent": "refund_request",
            "expected_order_id": "4821",
            "expected_reason": "damaged_item",
        },
        {
            "id": "test-2",
            "customer_message": "Where is order 4822?",
            "expected_intent": "order_inquiry",
            "expected_order_id": "4822",
            "expected_reason": "other",
        },
    ]

    outputs = {
        "Refund order 4821": IntentResult(
            intent=CustomerIntent.REFUND_REQUEST,
            order_id="4821",
            reason=RefundReason.DAMAGED_ITEM,
            summary="Refund request",
        ),
        "Where is order 4822?": IntentResult(
            intent=CustomerIntent.ORDER_INQUIRY,
            order_id="4822",
            reason=RefundReason.OTHER,
            summary="Order inquiry",
        ),
    }

    report = evaluate_intent_cases(cases, lambda message: outputs[message])

    assert report["total_cases"] == 2
    assert report["intent_accuracy"] == 1.0
    assert report["order_id_accuracy"] == 1.0
    assert report["reason_accuracy"] == 1.0
    assert report["critical_errors"] == 0


def test_evaluator_detects_false_refund_and_invented_order_id():
    cases = [
        {
            "id": "test-3",
            "customer_message": "Where is my delivery?",
            "expected_intent": "order_inquiry",
            "expected_order_id": None,
            "expected_reason": "other",
        }
    ]

    wrong_output = IntentResult(
        intent=CustomerIntent.REFUND_REQUEST,
        order_id="9999",
        reason=RefundReason.OTHER,
        summary="Refund request",
    )

    report = evaluate_intent_cases(cases, lambda _: wrong_output)

    assert report["intent_accuracy"] == 0.0
    assert report["order_id_accuracy"] == 0.0
    assert report["critical_errors"] == 1
    assert report["results"][0]["false_refund_classification"] is True
    assert report["results"][0]["invented_order_id"] is True
