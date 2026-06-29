import json
from langchain.tools import tool

# Mock CRM
class CRM:
    @staticmethod
    def get_customer(email: str) -> dict:
        return {"name": "John Doe", "email": email, "plan": "premium", "tickets": ["T123", "T456"]}

    @staticmethod
    def update_ticket(ticket_id: str, status: str, note: str) -> str:
        return f"Ticket {ticket_id} updated to {status} with note: {note}"


@tool
def classify_ticket(title: str, description: str) -> str:
    """
    Classify a support ticket into one of: billing, technical, feature_request, general.
    Returns a JSON string with 'category' and 'priority'.
    """
    if "billing" in title.lower() or "invoice" in description.lower():
        cat, priority = "billing", "high"
    elif "bug" in title.lower() or "error" in description.lower():
        cat, priority = "technical", "high"
    elif "suggest" in title.lower() or "feature" in description.lower():
        cat, priority = "feature_request", "medium"
    else:
        cat, priority = "general", "low"
    return json.dumps({"category": cat, "priority": priority})


@tool
def get_customer_info(email: str) -> str:
    """Retrieve customer profile and recent tickets from CRM given an email address."""
    info = CRM.get_customer(email.strip())
    return json.dumps(info)


@tool
def update_ticket(ticket_id: str, status: str, note: str) -> str:
    """Update a ticket's status and add a note given ticket_id, status, and note."""
    return CRM.update_ticket(ticket_id, status, note)


@tool
def draft_email(recipient: str, context: str, tone: str) -> str:
    """
    Generate a draft email for a recipient given context and tone (formal/friendly/empathetic).
    """
    return (
        f"Draft for {recipient} (tone: {tone}):\n\n"
        f"Dear {recipient},\n\n{context}\n\nBest regards,\nSupport Team"
    )