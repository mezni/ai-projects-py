
from typing import Any

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from refund_agent.agent import handle_customer_message
from refund_agent.health import liveness_check, readiness_check
from refund_agent.metrics import agent_metrics
from refund_agent.models import RefundDecision
from refund_agent.security import require_api_key
from refund_agent.input_validation import CustomerMessage
from refund_agent.review_api import router as review_router

app.include_router(review_router)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Refund Agent API",
    version="0.1.0",
    description="API for processing and evaluating refund requests.",
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


class RefundMessage(BaseModel):
    customer_message: str = Field(
        min_length=1,
        max_length=5000,
        description="The customer's refund-related message.",
    )

    @field_validator("customer_message")
    @classmethod
    def validate_customer_message(cls, value: str) -> str:
        validated = CustomerMessage(text=value)
        return validated.text


class RefundResponse(BaseModel):
    decision: RefundDecision
    customer_response: str


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return liveness_check()


@app.get(
    "/health/ready",
    dependencies=[Depends(require_api_key)],
)
def health_ready() -> dict[str, str]:
    return readiness_check()


@app.get(
    "/metrics",
    dependencies=[Depends(require_api_key)],
)
def get_metrics() -> dict[str, Any]:
    return agent_metrics.snapshot()


@app.post(
    "/refunds",
    response_model=RefundResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
def create_refund(
    request: Request,
    payload: RefundMessage,
) -> RefundResponse:
    decision, customer_response = handle_customer_message(
        customer_message=payload.customer_message,
    )

    return RefundResponse(
        decision=decision,
        customer_response=customer_response,
    )
