import json
from datetime import UTC, datetime
from pathlib import Path

from refund_agent.models import RefundDecision, RefundStatus


def resolve_human_review(
    decision: RefundDecision,
    reviewer_id: str,
    approved: bool,
    reason: str,
    audit_path: Path = Path("data/refund_audit.jsonl"),
) -> RefundDecision:
    """Resolve a pending refund review and record the decision."""

    reviewer_id = reviewer_id.strip()
    reason = reason.strip()

    if decision.status != RefundStatus.ESCALATED:
        raise ValueError("Only escalated refunds can be reviewed.")

    if not decision.requires_human_approval:
        raise ValueError("This refund is not awaiting human approval.")

    if not reviewer_id:
        raise ValueError("Reviewer ID is required.")

    if not reason:
        raise ValueError("A reason for the review decision is required.")

    if approved and decision.eligible_amount <= 0:
        raise ValueError("Cannot approve a refund with no eligible amount.")

    resolved_status = RefundStatus.APPROVED if approved else RefundStatus.REJECTED
    resolved_amount = (
        decision.eligible_amount if approved else decision.eligible_amount * 0
    )

    resolved_decision = decision.model_copy(
        update={
            "status": resolved_status,
            "eligible_amount": resolved_amount,
            "reason": (f"Human review by {reviewer_id}: {reason}"),
            "requires_human_approval": False,
        }
    )

    event = {
        "event_type": "human_review_resolved",
        "timestamp": datetime.now(UTC).isoformat(),
        "order_id": decision.order_id,
        "reviewer_id": reviewer_id,
        "approved": approved,
        "reason": reason,
        "previous_status": decision.status.value,
        "new_status": resolved_decision.status.value,
        "eligible_amount": str(resolved_decision.eligible_amount),
    }

    audit_path.parent.mkdir(parents=True, exist_ok=True)

    with audit_path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(event) + "\n")

    return resolved_decision
