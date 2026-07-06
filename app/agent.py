import os
import json
import re
from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from langchain_community.llms import Ollama  # <-- ✅ NEW
from langchain_core.messages import SystemMessage, HumanMessage
from .tools import classify_ticket, get_customer_info, send_email
from .rag import get_retriever
from .memory import get_facts

# --- Main LLM (for generation) ---
llm = ChatOllama(
    model=os.getenv("LLM_MODEL", "llama3"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)

# --- Judge LLM (strict JSON mode) ---
judge_llm = Ollama(
    model=os.getenv("JUDGE_MODEL", os.getenv("LLM_MODEL", "llama3")),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    format='json',  # <-- ✅ Works here!
)

# --- RAG retriever ---
retriever = get_retriever()

SYSTEM_PROMPT = """\
You are a helpful customer support AI agent.

Use the structured context provided below to answer the customer's question accurately and concisely.
Be empathetic, professional, and direct.

Guidelines:
- Extract the customer's first name from their email address and use it in the greeting (e.g., if the email is 'aids.16.harshchaudhari@gmail.com', the name is 'Harsh').
- For policy or product questions, refer to the Knowledge Base Articles section.
- For account-related questions, refer to the Customer Profile section.
- For billing issues, acknowledge urgency and provide clear next steps.
- For technical issues, provide step-by-step troubleshooting.
- Keep your response focused and relevant to the customer's question.
- Do not make up information that is not in the provided context.
- Write your response as a complete email reply (include a greeting and sign-off).
- Your name is 'Enzo Auditore' your employee id is '2022A7PS0293G' and your company name is 'Abstergo Industries'
- Address your name and employee id at the end of the email
"""


# ================================
# 🧑‍⚖️ LLM-as-Judge Functions
# ================================

def judge_reply(question: str, context: str, draft: str) -> dict:
    """
    Acts as a judge to evaluate the draft reply.
    Forces JSON output via the Ollama `format='json'` parameter.
    """
    judge_prompt = f"""
You are a strict evaluation AI. Your job is to grade a draft reply.

### Context (Ground Truth)
{context}

### User Question
{question}

### Draft Reply
{draft}

Evaluate the draft strictly on:
1. **Faithfulness (0-10)**: Does the draft strictly stick to the context? If it introduces facts not in the context, score low.
2. **Completeness (0-10)**: Does it directly answer the user's question?

Return ONLY a valid JSON object. Do not include any other text, explanations, or markdown.

Valid format:
{{"faithfulness_score": 8, "completeness_score": 9, "pass": true, "feedback": "The draft is accurate."}}
"""
    try:
        response = judge_llm.invoke(judge_prompt)  # <-- Now just the prompt string
        content = response.strip()

        # --- REGEX FALLBACK: Extract the first valid JSON object ---
        json_match = re.search(r'\{[^{}]*"(faithfulness_score|pass)"[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        else:
            fallback_match = re.search(r'\{.*\}', content, re.DOTALL)
            if fallback_match:
                content = fallback_match.group(0)

        result = json.loads(content)
        
        # Ensure required keys exist
        result.setdefault("faithfulness_score", 5)
        result.setdefault("completeness_score", 5)
        result.setdefault("pass", (result.get("faithfulness_score", 0) >= 7 and result.get("completeness_score", 0) >= 7))
        result.setdefault("feedback", "No feedback provided.")

        return result

    except Exception as e:
        print(f"⚠️ Judge failed: {e}. Raw response: {response if 'response' in locals() else 'None'}")
        return {"pass": True, "feedback": "Judge error, assuming OK."}


def revise_reply(question: str, context: str, draft: str, feedback: str) -> str:
    """
    If the judge fails the draft, ask the LLM to rewrite it based on feedback.
    """
    revision_prompt = f"""
You are a customer support agent. Your previous draft was rejected by our quality checker.

### Context (Ground Truth)
{context}

### User Question
{question}

### Your Previous Draft
{draft}

### Quality Checker Feedback
{feedback}

Please rewrite the draft strictly adhering to the context, addressing the feedback, and directly answering the user's question.
Write it as a complete email reply (greeting, body, sign-off).
"""
    response = llm.invoke([HumanMessage(content=revision_prompt)])
    return response.content


# ================================
# Main processing function
# ================================

def process_query(user_email: str, user_input: str, send_email_flag: bool = True) -> str:
    """
    Process a customer query using a RAG-augmented LLM pipeline, then
    send the generated reply as an email to the customer.

    Steps:
    1. Retrieve customer facts from memory (SQLite).
    2. Fetch customer profile from the CRM.
    3. Keyword-classify the ticket for context.
    4. Retrieve relevant knowledge base articles via vector search.
    5. Assemble all context and call the LLM once.
    6. Run LLM-as-Judge self-correction (if enabled).
    7. Send the generated reply as an email to the customer's address (optional).
    """

    # 1. Long-term customer facts
    facts = get_facts(user_email, user_input, k=3)
    facts_str = "\n".join(f"  - {f}" for f in facts) if facts else "  None recorded."

    # 2. CRM customer profile
    customer_info = json.loads(get_customer_info.invoke({"email": user_email}))
    customer_name = customer_info.get("name", "Customer")

    # 3. Ticket classification
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

    # Initial draft
    reply = llm.invoke(messages).content

    # ========================================
    # 🧑‍⚖️ LLM-as-Judge Self-Correction Loop
    # ========================================
    USE_JUDGE = os.getenv("USE_LLM_JUDGE", "True").lower() == "true"

    if USE_JUDGE and kb_context != "No relevant articles found.":
        print("🧑‍⚖️ Running LLM Judge on draft...")
        judgment = judge_reply(user_input, kb_context, reply)

        if not judgment.get("pass", True):
            print(f"❌ Draft failed. Feedback: {judgment.get('feedback')}")
            print("🔄 Regenerating draft with feedback...")
            reply = revise_reply(user_input, kb_context, reply, judgment.get("feedback", "Be more accurate."))
            print("✅ Revised draft generated.")
        else:
            print("✅ Draft passed quality check.")

    # Optional: Name fallback – ensures the greeting always contains the customer's name
    if customer_name and customer_name.lower() not in reply[:200].lower():
        lines = reply.split("\n")
        # Remove any existing generic greeting
        while lines and (lines[0].strip().lower().startswith("dear") or 
                         lines[0].strip().lower().startswith("hi") or 
                         lines[0].strip().lower().startswith("hello")):
            lines.pop(0)
        reply = f"Dear {customer_name},\n\n" + "\n".join(lines)

    # 6. Send the reply as an email (if enabled)
    if send_email_flag:
        subject = f"Your Support Request [{classification.get('category', 'general').title()}]"
        email_result = send_email(
            to_address=user_email,
            subject=subject,
            body=reply,
        )
        if email_result["success"]:
            reply += f"\n\n---\n📧 {email_result['message']}"
        else:
            reply += f"\n\n---\n⚠️ Email could not be sent: {email_result['message']}"

    return reply