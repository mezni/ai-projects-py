
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from refund_agent.api import app
from refund_agent.models import RefundDecision, RefundStatus

client = TestClient(app)
TEST_API_KEY = "test-only-refund-agent-key"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


def test_liveness_is_public():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_refund_requires_api_key(monkeypatch):
    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

    response = client.post(
        "/refunds",
        json={"customer_message": "Refund order 4821"},
    )

    assert response.status_code == 401


def test_refund_rejects_invalid_api_key(monkeypatch):
    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

    response = client.post(
        "/refunds",
        headers={"X-API-Key": "wrong-key"},
        json={"customer_message": "Refund order 4821"},
    )

    assert response.status_code == 401


def test_refund_returns_decision_with_valid_key(monkeypatch):
    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

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
            headers=AUTH_HEADERS,
            json={"customer_message": "Refund order 4821"},
        )

    assert response.status_code == 200
    assert response.json()["decision"]["status"] == "approved"
    mock_handler.assert_called_once()


def test_readiness_requires_api_key(monkeypatch):
    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

    response = client.get("/health/ready")

    assert response.status_code == 401


def test_metrics_requires_api_key(monkeypatch):
    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

    response = client.get("/metrics")

    assert response.status_code == 401


def test_metrics_returns_data_with_valid_key(monkeypatch):
    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

    response = client.get("/metrics", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert "requests_total" in response.json()


def test_missing_server_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("REFUND_AGENT_API_KEY", raising=False)

    response = client.get("/metrics", headers=AUTH_HEADERS)

    assert response.status_code == 503




def test_refund_endpoint_rate_limit(monkeypatch):
    from fastapi.testclient import TestClient

    from refund_agent.api import app, limiter

    monkeypatch.setenv("REFUND_AGENT_API_KEY", TEST_API_KEY)

    client = TestClient(
        app,
        client=("192.0.2.25", 50000),
    )
    headers = {"X-API-Key": TEST_API_KEY}
    payload = {
        "customer_message": "Please refund order 4821 because it arrived damaged."
    }

    # Use a unique client address for this test.
    limiter.reset()

    for _ in range(10):
        response = client.post(
            "/refunds",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 200

    response = client.post(
        "/refunds",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 429
