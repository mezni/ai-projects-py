import json
from decimal import Decimal

import pytest

from refund_agent.approval import resolve_human_review
from refund_agent.models import RefundDecision, RefundStatus


def pending_decision(
    amount: str = "149.99",
) -> RefundDecision:
    return RefundDecision(
        order_id="4824",
        status=RefundStatus.ESCALATED,
        eligible_amount=Decimal(amount),
        reason="Refund exceeds the autonomous approval limit.",
        requires_human_approval=True,
    )


def test_human_can_approve_pending_refund(tmp_path):
    audit_path = tmp_path / "refund_audit.jsonl"

    result = resolve_human_review(
        decision=pending_decision(),
        reviewer_id="reviewer-123",
        approved=True,
        reason="Reviewed and authorized.",
        audit_path=audit_path,
    )

    assert result.status == RefundStatus.APPROVED
    assert result.eligible_amount == Decimal("149.99")
    assert result.requires_human_approval is False

    event = json.loads(audit_path.read_text().strip())
    assert event["reviewer_id"] == "reviewer-123"
    assert event["approved"] is True
    assert event["new_status"] == "approved"


def test_human_can_reject_pending_refund(tmp_path):
    audit_path = tmp_path / "refund_audit.jsonl"

    result = resolve_human_review(
        decision=pending_decision(),
        reviewer_id="reviewer-456",
        approved=False,
        reason="Request does not meet policy.",
        audit_path=audit_path,
    )

    assert result.status == RefundStatus.REJECTED
    assert result.eligible_amount == Decimal("0.00")
    assert result.requires_human_approval is False


def test_cannot_review_non_escalated_decision(tmp_path):
    decision = RefundDecision(
        order_id="4821",
        status=RefundStatus.APPROVED,
        eligible_amount=Decimal("49.99"),
        reason="Already approved.",
    )

    with pytest.raises(ValueError, match="Only escalated refunds"):
        resolve_human_review(
            decision=decision,
            reviewer_id="reviewer-123",
            approved=True,
            reason="Review",
            audit_path=tmp_path / "audit.jsonl",
        )


def test_reviewer_and_reason_are_required(tmp_path):
    with pytest.raises(ValueError, match="Reviewer ID is required"):
        resolve_human_review(
            decision=pending_decision(),
            reviewer_id=" ",
            approved=True,
            reason="Reviewed",
            audit_path=tmp_path / "audit.jsonl",
        )

    with pytest.raises(ValueError, match="reason"):
        resolve_human_review(
            decision=pending_decision(),
            reviewer_id="reviewer-123",
            approved=True,
            reason=" ",
            audit_path=tmp_path / "audit.jsonl",
        )


def test_cannot_approve_zero_amount(tmp_path):
    with pytest.raises(ValueError, match="no eligible amount"):
        resolve_human_review(
            decision=pending_decision("0.00"),
            reviewer_id="reviewer-123",
            approved=True,
            reason="Reviewed",
            audit_path=tmp_path / "audit.jsonl",
        )


def test_each_review_appends_an_audit_event(tmp_path):
    audit_path = tmp_path / "refund_audit.jsonl"

    for reviewer in ("reviewer-1", "reviewer-2"):
        resolve_human_review(
            decision=pending_decision(),
            reviewer_id=reviewer,
            approved=False,
            reason="Rejected after review.",
            audit_path=audit_path,
        )

    events = [json.loads(line) for line in audit_path.read_text().splitlines()]

    assert len(events) == 2
