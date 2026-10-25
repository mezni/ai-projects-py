
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from refund_agent.api import app
from refund_agent.models import RefundDecision, RefundStatus

client = TestClient(app)


def test_liveness_endpoint():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint():
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_endpoint():
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.json()
    assert "requests_total" in body
    assert "outcomes" in body
    assert "latency_ms" in body


def test_create_refund_returns_decision_and_customer_response():
    decision = RefundDecision(
        order_id="4821",
        status=RefundStatus.APPROVED,
        eligible_amount=Decimal("49.99"),
        reason="Order meets the refund eligibility rules.",
    )

    with patch(
        "refund_agent.api.handle_customer_message",
        return_value=(
            decision,
            "Your refund request has been approved.",
        ),
    ) as mock_handler:
        response = client.post(
            "/refunds",
            json={
                "customer_message": (
                    "Please refund order 4821."
                )
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["status"] == "approved"
    assert body["decision"]["order_id"] == "4821"
    assert body["customer_response"] == (
        "Your refund request has been approved."
    )
    mock_handler.assert_called_once()


def test_create_refund_rejects_empty_message():
    response = client.post(
        "/refunds",
        json={"customer_message": ""},
    )

    assert response.status_code == 422


def test_create_refund_rejects_missing_message():
    response = client.post("/refunds", json={})

    assert response.status_code == 422
