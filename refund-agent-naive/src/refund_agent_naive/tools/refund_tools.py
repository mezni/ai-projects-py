from decimal import Decimal
from typing import Annotated, Any

from langchain.tools import ToolRuntime, tool
from langchain_core.tools import BaseTool
from pydantic import Field

from refund_agent_naive.context import AgentContext
from refund_agent_naive.domain.models import RefundReason
from refund_agent_naive.services.refund_service import RefundService

Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


def build_refund_tools(service: RefundService) -> list[BaseTool]:
    @tool
    def get_order(order_id: str, runtime: ToolRuntime[AgentContext]) -> dict[str, Any]:
        """Look up one of the current customer's orders: amount, category,
        delivery date and whether it was already refunded."""
        order = service.get_order(order_id, runtime.context.customer_id)
        if order is None:
            return {"error": "Order not found."}
        return {
            "order_id": order.order_id,
            "category": order.category,
            "amount": str(order.amount),
            "delivered_on": order.delivered_on.isoformat(),
            "refunded": order.refunded,
        }

    @tool
    def check_refund_eligibility(
        order_id: str,
        runtime: ToolRuntime[AgentContext],
        amount: Money | None = None,
    ) -> dict[str, Any]:
        """Check whether an order (and optionally a specific amount) can be
        refunded under company policy. Call this before issue_refund."""
        verdict = service.check_eligibility(order_id, runtime.context.customer_id, amount)
        if verdict is None:
            return {"error": "Order not found."}
        return {
            "decision": verdict.decision.value,
            "reason": verdict.reason,
            "max_refund": str(verdict.max_refund),
        }

    @tool
    def issue_refund(
        order_id: str,
        amount: Money,
        reason: RefundReason,
        runtime: ToolRuntime[AgentContext],
    ) -> dict[str, Any]:
        """Issue a refund for the current customer's order. Policy is enforced
        here regardless of earlier checks. Large amounts need manager approval."""
        result = service.request_refund(order_id, runtime.context.customer_id, amount, reason)
        return {"outcome": result.outcome.value, "message": result.message}

    @tool
    def escalate_to_human(summary: str, runtime: ToolRuntime[AgentContext]) -> dict[str, Any]:
        """Hand off to a human agent when the request is outside policy, the
        customer disputes a decision, or you are unsure."""
        # Stub: wire to your ticketing system in a later step.
        return {"outcome": "escalated", "message": "A human agent will follow up."}

    return [get_order, check_refund_eligibility, issue_refund, escalate_to_human]