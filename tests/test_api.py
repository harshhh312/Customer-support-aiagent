"""
Integration Tests — FastAPI /health and /chat endpoints
Run with:  pytest tests/test_api.py -v

IMPORTANT: The server must be running before executing these tests.
Start it with:  python run.py
Ollama must also be running with llama3 pulled.
"""

import os
import sys
import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chat(email: str, message: str) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/chat",
        json={"email": email, "message": message},
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self):
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_health_content_type_json(self):
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        assert "application/json" in r.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Chat endpoint — structure & validation
# ---------------------------------------------------------------------------

class TestChatEndpointStructure:
    """Tests that check the response shape, not the LLM answer content."""

    def test_returns_200_with_valid_payload(self):
        r = chat("test@example.com", "Hello!")
        assert r.status_code == 200

    def test_response_contains_reply_field(self):
        r = chat("test@example.com", "Hello!")
        body = r.json()
        assert "reply" in body

    def test_reply_is_non_empty_string(self):
        r = chat("test@example.com", "Hello!")
        body = r.json()
        assert isinstance(body["reply"], str)
        assert len(body["reply"]) > 0

    def test_missing_email_returns_422(self):
        r = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "Hello"},
            timeout=10,
        )
        assert r.status_code == 422

    def test_missing_message_returns_422(self):
        r = requests.post(
            f"{BASE_URL}/chat",
            json={"email": "user@example.com"},
            timeout=10,
        )
        assert r.status_code == 422

    def test_empty_body_returns_422(self):
        r = requests.post(f"{BASE_URL}/chat", json={}, timeout=10)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Chat endpoint — semantic scenarios
# These tests verify the LLM actually uses the right tools/knowledge.
# They use soft assertions (keywords) to avoid over-fitting to exact phrasing.
# ---------------------------------------------------------------------------

class TestChatScenarios:
    """End-to-end scenario tests — require Ollama + llama3 running."""

    def test_refund_policy_query(self):
        """Agent should surface the 30-day refund policy from the knowledge base."""
        r = chat("john@example.com", "What is your refund policy?")
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        # Knowledge base says "30 days" and "full refund"
        assert any(kw in reply for kw in ["refund", "30 day", "30-day", "billing"])

    def test_password_reset_query(self):
        """Agent should mention password reset steps from the knowledge base."""
        r = chat("john@example.com", "How do I reset my password?")
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        assert any(kw in reply for kw in ["password", "reset", "forgot", "link", "email"])

    def test_api_access_query(self):
        """Agent should mention API access details from the knowledge base."""
        r = chat("john@example.com", "Does the Pro plan include API access?")
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        assert any(kw in reply for kw in ["api", "pro", "rate limit", "1,000", "1000"])

    def test_billing_ticket_classification(self):
        """Agent should recognise a billing issue."""
        r = chat("john@example.com", "I have a billing problem — I was charged twice this month.")
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        assert any(kw in reply for kw in ["billing", "charge", "payment", "invoice", "refund"])

    def test_technical_issue(self):
        """Agent should respond appropriately to a crash report."""
        r = chat("john@example.com", "My app keeps crashing every time I open it.")
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        assert any(kw in reply for kw in ["crash", "cache", "reinstall", "update", "technical"])

    def test_shipping_query(self):
        """Agent should surface shipping time from the knowledge base."""
        r = chat("john@example.com", "How long does shipping take?")
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        assert any(kw in reply for kw in ["ship", "day", "business", "express", "standard"])

    def test_different_user_emails_work(self):
        """Multiple different users should each get a valid response."""
        emails = ["alice@example.com", "bob@company.org", "charlie+test@mail.net"]
        for email in emails:
            r = chat(email, "Hello, can you help me?")
            assert r.status_code == 200
            assert "reply" in r.json()

    def test_response_is_professional(self):
        """Agent response should not be empty or a raw error traceback."""
        r = chat("john@example.com", "I need help with my account.")
        assert r.status_code == 200
        reply = r.json()["reply"]
        # Should not expose internal Python tracebacks
        assert "Traceback" not in reply
        assert "Exception" not in reply


# ---------------------------------------------------------------------------
# Docs / OpenAPI
# ---------------------------------------------------------------------------

class TestDocs:
    def test_swagger_ui_accessible(self):
        r = requests.get(f"{BASE_URL}/docs", timeout=10)
        assert r.status_code == 200

    def test_openapi_schema_accessible(self):
        r = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert "/chat" in schema["paths"]
        assert "/health" in schema["paths"]
