from datetime import UTC, datetime
from decimal import Decimal

from refund_agent_naive.domain.models import Refund, RefundReason
from refund_agent_naive.services.refund_service import Outcome

R = RefundReason.DEFECTIVE


def test_small_refund_is_issued_and_order_flagged(service, orders):
    res = service.request_refund("A1001", "c1", Decimal("20.00"), R)
    assert res.outcome is Outcome.REFUNDED
    assert res.refund.approved_by == "auto"
    assert orders.get_for_customer("A1001", "c1").refunded is True


def test_second_request_is_denied_as_already_refunded(service):
    service.request_refund("A1001", "c1", Decimal("20.00"), R)
    res = service.request_refund("A1001", "c1", Decimal("20.00"), R)
    assert res.outcome is Outcome.DENIED


def test_large_refund_is_pending_and_not_stored(service, refunds):
    res = service.request_refund("A1002", "c1", Decimal("349.00"), R)
    assert res.outcome is Outcome.PENDING_APPROVAL
    _, created = refunds.create_if_absent(
        Refund(
            refund_id="x",
            order_id="A1002",
            customer_id="c1",
            amount=Decimal("1"),
            reason=R,
            approved_by="auto",
            created_at=datetime.now(UTC),
        )
    )
    assert created is True  # nothing had been stored


def test_expired_window_denied(service):
    assert service.request_refund("A1003", "c1", Decimal("10"), R).outcome is Outcome.DENIED


def test_foreign_order_not_found(service):
    assert service.request_refund("B2001", "c1", Decimal("10"), R).outcome is Outcome.NOT_FOUND


def test_execute_approved_records_manager(service):
    res = service.execute_approved("A1002", "c1", Decimal("349.00"), R, "mgr-7")
    assert res.outcome is Outcome.REFUNDED
    assert res.refund.approved_by == "mgr-7"


def test_execute_approved_still_enforces_policy(service):
    res = service.execute_approved("A1003", "c1", Decimal("40.00"), R, "mgr-7")
    assert res.outcome is Outcome.DENIED


def test_existing_refund_row_yields_duplicate(service, refunds):
    refunds.create_if_absent(
        Refund(
            refund_id="refund-A1001",
            order_id="A1001",
            customer_id="c1",
            amount=Decimal("10"),
            reason=R,
            approved_by="auto",
            created_at=datetime.now(UTC),
        )
    )
    res = service.request_refund("A1001", "c1", Decimal("10"), R)
    assert res.outcome is Outcome.DUPLICATE
