from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from refund_agent_naive.domain.models import Decision, Order, PolicyResult, Refund, RefundReason
from refund_agent_naive.domain.policy import RefundPolicy
from refund_agent_naive.repositories.base import OrderRepository, RefundRepository


class Outcome(StrEnum):
    REFUNDED = "refunded"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"
    DUPLICATE = "duplicate"
    NOT_FOUND = "not_found"


class RefundResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: Outcome
    message: str
    refund: Refund | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RefundService:
    def __init__(
        self,
        orders: OrderRepository,
        refunds: RefundRepository,
        policy: RefundPolicy,
        today: Callable[[], date] = date.today,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._orders = orders
        self._refunds = refunds
        self._policy = policy
        self._today = today
        self._now = now

    # ---- read paths ----
    def get_order(self, order_id: str, customer_id: str) -> Order | None:
        return self._orders.get_for_customer(order_id, customer_id)

    def check_eligibility(
        self, order_id: str, customer_id: str, amount: Decimal | None = None
    ) -> PolicyResult | None:
        """None means the order was not found for this customer."""
        order = self._orders.get_for_customer(order_id, customer_id)
        if order is None:
            return None
        return self._policy.evaluate(order, amount or order.amount, self._today())

    # ---- write paths ----
    def request_refund(
        self, order_id: str, customer_id: str, amount: Decimal, reason: RefundReason
    ) -> RefundResult:
        order = self._orders.get_for_customer(order_id, customer_id)
        if order is None:
            return RefundResult(outcome=Outcome.NOT_FOUND, message="Order not found.")

        verdict = self._policy.evaluate(order, amount, self._today())
        if verdict.decision is Decision.DENY:
            return RefundResult(outcome=Outcome.DENIED, message=verdict.reason)
        if verdict.decision is Decision.NEEDS_MANAGER:
            return RefundResult(
                outcome=Outcome.PENDING_APPROVAL, message="Manager approval is required."
            )
        return self._execute(order, amount, reason, approved_by="auto")

    def execute_approved(
        self,
        order_id: str,
        customer_id: str,
        amount: Decimal,
        reason: RefundReason,
        manager_id: str,
    ) -> RefundResult:
        """Called after a manager approves. Policy is re-checked because time
        has passed since the original request."""
        order = self._orders.get_for_customer(order_id, customer_id)
        if order is None:
            return RefundResult(outcome=Outcome.NOT_FOUND, message="Order not found.")
        verdict = self._policy.evaluate(order, amount, self._today())
        if verdict.decision is Decision.DENY:
            return RefundResult(outcome=Outcome.DENIED, message=verdict.reason)
        return self._execute(order, amount, reason, approved_by=manager_id)

    # ---- internals ----
    def _execute(
        self, order: Order, amount: Decimal, reason: RefundReason, approved_by: str
    ) -> RefundResult:
        refund = Refund(
            # deterministic = usable as a payment idempotency key
            refund_id=f"refund-{order.order_id}",
            order_id=order.order_id,
            customer_id=order.customer_id,
            amount=amount,
            reason=reason,
            approved_by=approved_by,
            created_at=self._now(),
        )
        stored, created = self._refunds.create_if_absent(refund)
        if not created:
            return RefundResult(
                outcome=Outcome.DUPLICATE,
                message="A refund was already issued for this order.",
                refund=stored,
            )
        # Refund row first, flag second: a crash between them is retry-safe.
        self._orders.mark_refunded(order.order_id)
        return RefundResult(outcome=Outcome.REFUNDED, message="Refund issued.", refund=stored)
