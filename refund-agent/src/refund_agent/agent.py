
import logging
import time
from datetime import date
from decimal import Decimal

from openai import APIError

from refund_agent.models import RefundDecision, RefundStatus
from refund_agent.observability import (
    elapsed_milliseconds,
    log_refund_event,
    new_request_id,
    request_id_context,
)
from refund_agent.responses import format_refund_response
from refund_agent.workflow import process_refund

logger = logging.getLogger(__name__)


def handle_customer_message(
    customer_message: str,
    today: date | None = None,
) -> tuple[RefundDecision, str]:
    request_id = new_request_id()
    token = request_id_context.set(request_id)
    start = time.perf_counter()

    log_refund_event("refund_request_started")

    try:
        decision = process_refund(
            customer_message=customer_message,
            today=today,
        )
    except APIError as exc:
        logger.error(
            "refund_request_dependency_failed",
            extra={"error_type": type(exc).__name__},
        )
        decision = RefundDecision(
            order_id="unknown",
            status=RefundStatus.ESCALATED,
            eligible_amount=Decimal("0.00"),
            reason=(
                "The refund service is temporarily unavailable. "
                "Human review is required."
            ),
            requires_human_approval=True,
        )
    except Exception:
        # Log the exception type, but not the customer message or
        # exception text, which may contain sensitive information.
        logger.exception("refund_request_unexpected_failure")
        decision = RefundDecision(
            order_id="unknown",
            status=RefundStatus.ESCALATED,
            eligible_amount=Decimal("0.00"),
            reason=(
                "The request could not be processed safely. "
                "Human review is required."
            ),
            requires_human_approval=True,
        )

    try:
        response = format_refund_response(decision)
        log_refund_event(
            "refund_request_completed",
            order_id=decision.order_id,
            status=decision.status.value,
            duration_ms=elapsed_milliseconds(start),
        )
        return decision, response
    finally:
        request_id_context.reset(token)
