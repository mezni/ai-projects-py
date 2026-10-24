from datetime import date
from decimal import Decimal

from refund_agent.models import (
    Order,
    RefundDecision,
    RefundRequest,
    RefundStatus,
)

RETURN_WINDOW_DAYS = 30
AUTONOMOUS_REFUND_LIMIT = Decimal("100.00")


def evaluate_refund(
    request: RefundRequest,
    order: Order,
    today: date,
) -> RefundDecision:
    if request.order_id != order.order_id:
        return RefundDecision(
            order_id=request.order_id,
            status=RefundStatus.ESCALATED,
            eligible_amount=Decimal("0.00"),
            reason="Request order ID does not match the retrieved order.",
            requires_human_approval=True,
        )

    if order.is_final_sale:
        return RefundDecision(
            order_id=order.order_id,
            status=RefundStatus.REJECTED,
            eligible_amount=Decimal("0.00"),
            reason="Final-sale items are not refundable.",
        )

    days_since_delivery = (today - order.delivery_date).days

    if days_since_delivery < 0:
        return RefundDecision(
            order_id=order.order_id,
            status=RefundStatus.ESCALATED,
            eligible_amount=Decimal("0.00"),
            reason="Delivery date is in the future; verify order data.",
            requires_human_approval=True,
        )

    if days_since_delivery > RETURN_WINDOW_DAYS:
        return RefundDecision(
            order_id=order.order_id,
            status=RefundStatus.REJECTED,
            eligible_amount=Decimal("0.00"),
            reason="The 30-day return window has expired.",
        )

    amount = min(
        request.requested_amount or order.item_price,
        order.item_price,
    )

    if amount > AUTONOMOUS_REFUND_LIMIT:
        return RefundDecision(
            order_id=order.order_id,
            status=RefundStatus.ESCALATED,
            eligible_amount=amount,
            reason="Refund exceeds the $100 autonomous approval limit.",
            requires_human_approval=True,
        )

    return RefundDecision(
        order_id=order.order_id,
        status=RefundStatus.APPROVED,
        eligible_amount=amount,
        reason="Order meets the refund eligibility rules.",
    )
