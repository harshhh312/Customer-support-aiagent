import json
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock CRM
# ---------------------------------------------------------------------------
class CRM:
    @staticmethod
    def get_customer(email: str) -> dict:
        return {"name": email.split('@')[0], "email": email, "plan": "premium", "tickets": ["T123", "T456"]}

    @staticmethod
    def update_ticket(ticket_id: str, status: str, note: str) -> str:
        return f"Ticket {ticket_id} updated to {status} with note: {note}"


# ---------------------------------------------------------------------------
# Email sending (real SMTP)
# ---------------------------------------------------------------------------

def send_email(to_address: str, subject: str, body: str) -> dict:
    """
    Send an email via SMTP using credentials from environment variables.

    Required .env variables:
        SMTP_HOST     - e.g. smtp.gmail.com
        SMTP_PORT     - e.g. 587  (TLS) or 465 (SSL)
        SMTP_USER     - sender email address
        SMTP_PASSWORD - sender password / app password
        SMTP_FROM     - display name + address, e.g. "Support <support@example.com>"

    Returns a dict with keys: success (bool), message (str).
    """
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user)

    if not all([host, user, password]):
        missing = [k for k, v in {"SMTP_HOST": host, "SMTP_USER": user, "SMTP_PASSWORD": password}.items() if not v]
        return {
            "success": False,
            "message": f"Email not sent — missing environment variables: {', '.join(missing)}. "
                       "Add SMTP_HOST, SMTP_USER, and SMTP_PASSWORD to your .env file.",
        }

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))

    try:
        if port == 465:
            # SSL connection
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(user, password)
                server.sendmail(user, to_address, msg.as_string())
        else:
            # STARTTLS connection (port 587 default)
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls()
                server.login(user, password)
                server.sendmail(user, to_address, msg.as_string())

        logger.info("Email sent to %s via %s:%s", to_address, host, port)
        return {"success": True, "message": f"Email successfully sent to {to_address}."}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD."}
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
        return {"success": False, "message": f"Failed to send email: {exc}"}
    except OSError as exc:
        return {"success": False, "message": f"Could not connect to SMTP server {host}:{port} — {exc}"}


# ---------------------------------------------------------------------------
# LangChain tools
# ---------------------------------------------------------------------------

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