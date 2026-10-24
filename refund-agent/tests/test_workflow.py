from datetime import date
from decimal import Decimal

from refund_agent.intent import CustomerIntent, IntentResult
from refund_agent.models import RefundStatus
from refund_agent.workflow import process_refund


def test_process_eligible_refund(monkeypatch):
    monkeypatch.setattr(
        "refund_agent.workflow.extract_intent",
        lambda _: IntentResult(
            intent=CustomerIntent.REFUND_REQUEST,
            order_id="4821",
            summary="Item arrived damaged",
        ),
    )

    decision = process_refund(
        "I want a refund for order 4821.",
        today=date(2026, 10, 24),
    )

    assert decision.order_id == "4821"
    assert decision.status == RefundStatus.APPROVED
    assert decision.eligible_amount == Decimal("49.99")


def test_process_final_sale_order(monkeypatch):
    monkeypatch.setattr(
        "refund_agent.workflow.extract_intent",
        lambda _: IntentResult(
            intent=CustomerIntent.REFUND_REQUEST,
            order_id="4823",
            summary="I want a refund",
        ),
    )

    decision = process_refund(
        "I want a refund for order 4823.",
        today=date(2026, 10, 24),
    )

    assert decision.status == RefundStatus.REJECTED
    assert decision.eligible_amount == Decimal("0.00")


def test_escalate_when_order_id_is_missing(monkeypatch):
    monkeypatch.setattr(
        "refund_agent.workflow.extract_intent",
        lambda _: IntentResult(
            intent=CustomerIntent.REFUND_REQUEST,
            summary="I want a refund",
        ),
    )

    decision = process_refund("I want a refund.")

    assert decision.status == RefundStatus.ESCALATED
    assert decision.requires_human_approval is True


def test_escalate_when_order_does_not_exist(monkeypatch):
    monkeypatch.setattr(
        "refund_agent.workflow.extract_intent",
        lambda _: IntentResult(
            intent=CustomerIntent.REFUND_REQUEST,
            order_id="9999",
            summary="I want a refund",
        ),
    )

    decision = process_refund("Refund order 9999.")

    assert decision.status == RefundStatus.ESCALATED
    assert decision.order_id == "9999"


def test_escalate_non_refund_intent(monkeypatch):
    monkeypatch.setattr(
        "refund_agent.workflow.extract_intent",
        lambda _: IntentResult(
            intent=CustomerIntent.ORDER_INQUIRY,
            order_id="4821",
            summary="Where is my order?",
        ),
    )

    decision = process_refund("Where is my order?")

    assert decision.status == RefundStatus.ESCALATED
    assert decision.requires_human_approval is True
