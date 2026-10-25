import json
from typing import Any

from langchain_core.tools import tool

ORDERS: dict[str, dict[str, Any]] = {
    "4821": {
        "order_id": "4821",
        "item": "Wireless Headphones",
        "amount_usd": 89.99,
        "days_since_purchase": 12,
        "digital": False,
        "condition": "damaged on arrival",
    },
    "4822": {
        "order_id": "4822",
        "item": "Python Crash Course (ebook)",
        "amount_usd": 29.99,
        "days_since_purchase": 3,
        "digital": True,
        "condition": "downloaded",
    },
    "4823": {
        "order_id": "4823",
        "item": "Standing Desk",
        "amount_usd": 349.00,
        "days_since_purchase": 45,
        "digital": False,
        "condition": "used",
    },
    "4824": {
        "order_id": "4824",
        "item": "Mechanical Keyboard",
        "amount_usd": 149.00,
        "days_since_purchase": 5,
        "digital": False,
        "condition": "unused",
    },
}

REFUNDS: dict[str, dict[str, Any]] = {}


@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by ID and return its details as JSON."""
    order = ORDERS.get(order_id)
    if order is None:
        return json.dumps({"error": f"No order found with ID {order_id}."})
    return json.dumps(order)


def _policy_result(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"No order found with ID {order_id}."}

    reasons: list[str] = []

    if order["days_since_purchase"] > 30:
        reasons.append("Purchase is older than 30 days.")
    if order["digital"]:
        reasons.append("Digital products are non-refundable once downloaded.")
    if order["condition"] == "used":
        reasons.append("Item is not unused.")

    eligible = not reasons

    return {
        "order_id": order_id,
        "eligible": eligible,
        "reasons": reasons,
        "requires_human_approval": eligible and order["amount_usd"] > 100,
    }


@tool
def check_refund_policy(order_id: str) -> str:
    """Check whether an order is eligible for a refund and whether it needs approval."""
    return json.dumps(_policy_result(order_id))


@tool
def issue_refund(order_id: str, reason: str) -> str:
    """Issue a refund for an order when policy allows it."""
    policy = _policy_result(order_id)

    if "error" in policy:
        return json.dumps(policy)

    if not policy["eligible"]:
        return json.dumps(
            {
                "order_id": order_id,
                "status": "rejected",
                "reasons": policy["reasons"],
            }
        )

    order = ORDERS[order_id]

    refund = {
        "order_id": order_id,
        "amount_usd": order["amount_usd"],
        "reason": reason,
        "status": "refunded",
    }
    REFUNDS[order_id] = refund
    return json.dumps(refund)
