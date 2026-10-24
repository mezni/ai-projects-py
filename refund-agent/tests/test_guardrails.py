from datetime import date
from decimal import Decimal

from refund_agent.guardrails import apply_guardrails
from refund_agent.models import (
    Order,
    RefundDecision,
    RefundRequest,
    RefundStatus,
)


def test_unverified_damage_requires_human_review():
    request = RefundRequest(
        order_id="4821",
        reason="Item arrived damaged",
    )
    order = Order(
        order_id="4821",
        delivery_date=date(2026, 10, 20),
        item_price=Decimal("49.99"),
        is_damaged=True,
        damage_evidence_verified=False,
    )
    decision = RefundDecision(
        order_id="4821",
        status=RefundStatus.APPROVED,
        eligible_amount=Decimal("49.99"),
        reason="Policy approved the refund.",
    )

    result = apply_guardrails(request, order, decision)

    assert result.status == RefundStatus.ESCALATED
    assert result.eligible_amount == Decimal("0.00")
    assert result.requires_human_approval is True
    assert "evidence" in result.reason.lower()


def test_amount_above_limit_requires_human_approval():
    request = RefundRequest(
        order_id="4824",
        reason="Item is unwanted",
    )
    order = Order(
        order_id="4824",
        delivery_date=date(2026, 10, 20),
        item_price=Decimal("150.00"),
    )
    decision = RefundDecision(
        order_id="4824",
        status=RefundStatus.APPROVED,
        eligible_amount=Decimal("150.00"),
        reason="Policy approved the refund.",
    )

    result = apply_guardrails(request, order, decision)

    assert result.status == RefundStatus.ESCALATED
    assert result.requires_human_approval is True


def test_policy_rejection_is_preserved():
    request = RefundRequest(
        order_id="4823",
        reason="Item is unwanted",
    )
    order = Order(
        order_id="4823",
        delivery_date=date(2026, 10, 20),
        item_price=Decimal("49.99"),
        is_final_sale=True,
        is_damaged=True,
        damage_evidence_verified=False,
    )
    decision = RefundDecision(
        order_id="4823",
        status=RefundStatus.REJECTED,
        eligible_amount=Decimal("0.00"),
        reason="Final-sale items are not refundable.",
    )

    result = apply_guardrails(request, order, decision)

    assert result.status == RefundStatus.REJECTED
    assert result.reason == "Final-sale items are not refundable."


def test_existing_escalation_requires_human_approval():
    request = RefundRequest(
        order_id="4824",
        reason="Unusual refund request",
    )
    order = Order(
        order_id="4824",
        delivery_date=date(2026, 10, 20),
        item_price=Decimal("49.99"),
    )
    decision = RefundDecision(
        order_id="4824",
        status=RefundStatus.ESCALATED,
        eligible_amount=Decimal("0.00"),
        reason="Manual review required.",
        requires_human_approval=False,
    )

    result = apply_guardrails(request, order, decision)

    assert result.status == RefundStatus.ESCALATED
    assert result.requires_human_approval is True