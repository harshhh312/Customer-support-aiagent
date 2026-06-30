import os
import json
from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from .tools import classify_ticket, get_customer_info, send_email
from .rag import get_retriever
from .memory import get_facts

# --- LLM ---
llm = ChatOllama(
    model=os.getenv("LLM_MODEL", "llama3"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)

# --- RAG retriever ---
retriever = get_retriever()

SYSTEM_PROMPT = """\
You are a helpful customer support AI agent.

Use the structured context provided below to answer the customer's question accurately and concisely.
Be empathetic, professional, and direct.

Guidelines:
- For policy or product questions, refer to the Knowledge Base Articles section.
- For account-related questions, refer to the Customer Profile section.
- For billing issues, acknowledge urgency and provide clear next steps.
- For technical issues, provide step-by-step troubleshooting.
- Keep your response focused and relevant to the customer's question.
- Do not make up information that is not in the provided context.
- Write your response as a complete email reply (include a greeting and sign-off).
"""


def process_query(user_email: str, user_input: str) -> str:
    """
    Process a customer query using a RAG-augmented LLM pipeline, then
    send the generated reply as an email to the customer.

    Steps:
    1. Retrieve customer facts from memory (SQLite).
    2. Fetch customer profile from the CRM.
    3. Keyword-classify the ticket for context.
    4. Retrieve relevant knowledge base articles via vector search.
    5. Assemble all context and call the LLM once.
    6. Send the generated reply as an email to the customer's address.
    """

    # 1. Long-term customer facts
    facts = get_facts(user_email)
    facts_str = "\n".join(f"  - {f}" for f in facts) if facts else "  None recorded."

    # 2. CRM customer profile
    customer_info = json.loads(get_customer_info.invoke({"email": user_email}))
    customer_name = customer_info.get("name", "Customer")

    # 3. Ticket classification (keyword-based, no LLM call needed)
    classification = json.loads(classify_ticket.invoke({
        "title": user_input[:60],
        "description": user_input,
    }))

    # 4. RAG: retrieve the most relevant knowledge base chunks
    docs = retriever.invoke(user_input)
    kb_context = "\n\n".join(d.page_content for d in docs) if docs else "No relevant articles found."

    # 5. Assemble structured context for the LLM
    context = f"""\
=== Customer Profile ===
Name    : {customer_name}
Email   : {customer_info.get('email', user_email)}
Plan    : {customer_info.get('plan', 'Unknown')}
Tickets : {', '.join(customer_info.get('tickets', [])) or 'None'}

=== Ticket Classification ===
Category : {classification.get('category', 'general')}
Priority : {classification.get('priority', 'low')}

=== Long-term Customer Notes ===
{facts_str}

=== Relevant Knowledge Base Articles ===
{kb_context}
"""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT + "\n\n" + context),
        HumanMessage(content=user_input),
    ]

    reply = llm.invoke(messages).content

    # 6. Send the reply as an email to the customer
    subject = f"Re: Your Support Request [{classification.get('category', 'general').title()}]"
    email_result = send_email(
        to_address=user_email,
        subject=subject,
        body=reply,
    )

    # Append email send status to the reply so the caller can see it
    if email_result["success"]:
        reply += f"\n\n---\n📧 {email_result['message']}"
    else:
        reply += f"\n\n---\n⚠️ Email could not be sent: {email_result['message']}"

    return reply