from datetime import date
from decimal import Decimal

from refund_agent.models import (
    Order,
    RefundRequest,
    RefundStatus,
)
from refund_agent.policy import evaluate_refund


def make_order(
    *,
    delivery_date: date = date(2026, 10, 1),
    item_price: Decimal = Decimal("49.99"),
    is_final_sale: bool = False,
) -> Order:
    return Order(
        order_id="4821",
        delivery_date=delivery_date,
        item_price=item_price,
        is_final_sale=is_final_sale,
    )


def make_request(
    amount: Decimal | None = None,
) -> RefundRequest:
    return RefundRequest(
        order_id="4821",
        reason="Item arrived damaged",
        requested_amount=amount,
    )


def test_approves_eligible_refund():
    decision = evaluate_refund(
        make_request(),
        make_order(),
        today=date(2026, 10, 20),
    )

    assert decision.status == RefundStatus.APPROVED
    assert decision.eligible_amount == Decimal("49.99")


def test_rejects_final_sale_item():
    decision = evaluate_refund(
        make_request(),
        make_order(is_final_sale=True),
        today=date(2026, 10, 20),
    )

    assert decision.status == RefundStatus.REJECTED
    assert decision.eligible_amount == Decimal("0.00")


def test_rejects_expired_return_window():
    decision = evaluate_refund(
        make_request(),
        make_order(),
        today=date(2026, 11, 1),
    )

    assert decision.status == RefundStatus.REJECTED


def test_escalates_refund_above_limit():
    decision = evaluate_refund(
        make_request(Decimal("150.00")),
        make_order(item_price=Decimal("200.00")),
        today=date(2026, 10, 20),
    )

    assert decision.status == RefundStatus.ESCALATED
    assert decision.requires_human_approval is True


def test_caps_refund_at_item_price():
    decision = evaluate_refund(
        make_request(Decimal("80.00")),
        make_order(item_price=Decimal("49.99")),
        today=date(2026, 10, 20),
    )

    assert decision.eligible_amount == Decimal("49.99")


def test_escalates_when_order_id_does_not_match():
    decision = evaluate_refund(
        RefundRequest(
            order_id="9999",
            reason="Item arrived damaged",
        ),
        make_order(),
        today=date(2026, 10, 20),
    )

    assert decision.status == RefundStatus.ESCALATED
    assert decision.requires_human_approval is True


def test_accepts_request_on_day_30():
    decision = evaluate_refund(
        make_request(),
        make_order(),
        today=date(2026, 10, 31),
    )

    assert decision.status == RefundStatus.APPROVED
