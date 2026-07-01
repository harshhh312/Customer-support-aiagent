"""
Unit Tests — Tools, Memory & RAG
Run with:  pytest tests/test_tools.py -v
These tests do NOT require the server or Ollama to be running.
"""

import json
import os
import sys
import pytest

# Make sure the app package is importable from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class TestClassifyTicket:
    """Tests for the classify_ticket tool (keyword-based logic)."""

    def _classify(self, title: str, description: str) -> dict:
        from app.tools import classify_ticket
        result = classify_ticket.invoke({"title": title, "description": description})
        return json.loads(result)

    def test_billing_keyword_in_title(self):
        result = self._classify("Billing issue", "I was overcharged this month.")
        assert result["category"] == "billing"
        assert result["priority"] == "high"

    def test_invoice_keyword_in_description(self):
        result = self._classify("Help needed", "My invoice is wrong.")
        assert result["category"] == "billing"
        assert result["priority"] == "high"

    def test_bug_keyword_in_title(self):
        result = self._classify("Bug report", "App freezes on launch.")
        assert result["category"] == "technical"
        assert result["priority"] == "high"

    def test_error_keyword_in_description(self):
        result = self._classify("Problem", "I keep getting an error when logging in.")
        assert result["category"] == "technical"
        assert result["priority"] == "high"

    def test_feature_request(self):
        result = self._classify("Suggest dark mode", "I would love a dark feature in the app.")
        assert result["category"] == "feature_request"
        assert result["priority"] == "medium"

    def test_general_fallback(self):
        result = self._classify("Hello", "Just wanted to say thanks!")
        assert result["category"] == "general"
        assert result["priority"] == "low"

    def test_returns_valid_json(self):
        from app.tools import classify_ticket
        raw = classify_ticket.invoke({"title": "test", "description": "test"})
        parsed = json.loads(raw)
        assert "category" in parsed
        assert "priority" in parsed


class TestGetCustomerInfo:
    """Tests for the get_customer_info tool (mock CRM)."""

    def _get_info(self, email: str) -> dict:
        from app.tools import get_customer_info
        result = get_customer_info.invoke({"email": email})
        return json.loads(result)

    def test_returns_customer_dict(self):
        info = self._get_info("alice@example.com")
        assert "name" in info
        assert "email" in info
        assert "plan" in info
        assert "tickets" in info

    def test_email_preserved(self):
        info = self._get_info("alice@example.com")
        assert info["email"] == "alice@example.com"

    def test_email_stripped_of_whitespace(self):
        info = self._get_info("  bob@example.com  ")
        assert info["email"] == "bob@example.com"

    def test_tickets_is_list(self):
        info = self._get_info("user@test.com")
        assert isinstance(info["tickets"], list)


class TestUpdateTicket:
    """Tests for the update_ticket tool."""

    def _update(self, ticket_id: str, status: str, note: str) -> str:
        from app.tools import update_ticket
        return update_ticket.invoke({"ticket_id": ticket_id, "status": status, "note": note})

    def test_contains_ticket_id(self):
        result = self._update("T123", "resolved", "Issue fixed.")
        assert "T123" in result

    def test_contains_status(self):
        result = self._update("T456", "in_progress", "Working on it.")
        assert "in_progress" in result

    def test_contains_note(self):
        result = self._update("T789", "closed", "Customer confirmed fix.")
        assert "Customer confirmed fix." in result

    def test_returns_string(self):
        result = self._update("T001", "open", "New ticket.")
        assert isinstance(result, str)


class TestDraftEmail:
    """Tests for the draft_email tool."""

    def _draft(self, recipient: str, context: str, tone: str) -> str:
        from app.tools import draft_email
        return draft_email.invoke({"recipient": recipient, "context": context, "tone": tone})

    def test_contains_recipient(self):
        result = self._draft("John", "Your refund has been processed.", "formal")
        assert "John" in result

    def test_contains_context(self):
        result = self._draft("Alice", "We received your complaint.", "empathetic")
        assert "We received your complaint." in result

    def test_contains_tone(self):
        result = self._draft("Bob", "Here is your update.", "friendly")
        assert "friendly" in result

    def test_contains_sign_off(self):
        result = self._draft("Carol", "Thank you for contacting us.", "formal")
        assert "Support Team" in result

    def test_returns_string(self):
        result = self._draft("Dave", "Test context.", "formal")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class TestMemory:
    """Tests for the SQLite memory module (get_facts / save_fact)."""

    @pytest.fixture(autouse=True)
    def use_temp_db(self, monkeypatch, tmp_path):
        """Redirect memory DB to a fresh temp file for each test."""
        db_file = str(tmp_path / "test_memory.db")
        monkeypatch.setenv("MEMORY_DB_PATH", db_file)
        # Re-import so the module picks up the new env var
        import importlib
        import app.memory as mem_module
        importlib.reload(mem_module)
        mem_module.init_db()
        self.mem = mem_module

    def test_get_facts_empty_for_new_user(self):
        facts = self.mem.get_facts("newuser@example.com")
        assert facts == []

    def test_save_and_retrieve_single_fact(self):
        self.mem.save_fact("user@example.com", "Prefers email communication.")
        facts = self.mem.get_facts("user@example.com")
        assert "Prefers email communication." in facts

    def test_save_multiple_facts(self):
        self.mem.save_fact("user@example.com", "On premium plan.")
        self.mem.save_fact("user@example.com", "Located in India.")
        facts = self.mem.get_facts("user@example.com")
        assert len(facts) == 2
        assert "On premium plan." in facts
        assert "Located in India." in facts

    def test_facts_are_per_user(self):
        self.mem.save_fact("alice@example.com", "Alice's fact.")
        self.mem.save_fact("bob@example.com", "Bob's fact.")
        assert self.mem.get_facts("alice@example.com") == ["Alice's fact."]
        assert self.mem.get_facts("bob@example.com") == ["Bob's fact."]

    def test_facts_accumulate_across_calls(self):
        for i in range(5):
            self.mem.save_fact("user@example.com", f"Fact {i}")
        facts = self.mem.get_facts("user@example.com")
        assert len(facts) == 5
