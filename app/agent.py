import os
import json
import re
from dotenv import load_dotenv
load_dotenv()

from langchain_ollama import ChatOllama
from langchain_ollama import OllamaLLM
from langchain_core.messages import SystemMessage, HumanMessage
from .tools import classify_ticket, get_customer_info, send_email
from .rag import get_retriever
from .memory import get_facts
from .conversation_memory import get_conversation, format_history_for_prompt, add_to_conversation
from .pii_redaction import redact_pii, restore_pii


# ========================================
# 🤖 LLM CONFIGURATION
# ========================================

# --- Main LLM (for generation) ---
llm = ChatOllama(
    model=os.getenv("LLM_MODEL", "llama3"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)

# --- Judge LLM (strict JSON mode) ---
judge_llm = OllamaLLM(
    model=os.getenv("JUDGE_MODEL", os.getenv("LLM_MODEL", "llama3")),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    format='json',
)

# --- RAG retriever ---
retriever = get_retriever()


# ========================================
# 📝 SYSTEM PROMPT (Strict Rules)
# ========================================


SYSTEM_PROMPT = """\
You are a helpful customer support AI agent named Enzo Auditore (Employee ID: 2022A7PS0293G) from Abstergo Industries.

Use the structured context provided below to answer the customer's question accurately and concisely.
Be empathetic, professional, and direct.

CRITICAL RULES - FOLLOW THESE EXACTLY:
1. The customer's first name is provided in the Customer Profile section as "Name". If it says "Customer", extract it from their email (e.g., if email is harsh@gmail.com, use "Harsh").
2. ALWAYS start your email with: "Dear {first_name}," where {first_name} is the name from the Customer Profile.
3. NEVER include a subject line in the email body – the subject is set separately by the system.
4. NEVER use placeholders like {PII_1} – these are automatically restored by the system.
5. Your signature MUST be:
   Enzo Auditore
   Employee ID: 2022A7PS0293G
   Abstergo Industries

Guidelines:
- For policy or product questions, refer to the Knowledge Base Articles section.
- For account-related questions, refer to the Customer Profile section.
- For billing issues, acknowledge urgency and provide clear next steps.
- For technical issues, provide step-by-step troubleshooting.
- Keep your response focused and relevant to the customer's question.
- Do not make up information that is not in the provided context.
- Write your response as a complete email reply with a professional greeting, body, and sign-off.
"""



# ========================================
# 🧑‍⚖️ LLM-as-Judge Functions
# ========================================

def judge_reply(question: str, context: str, draft: str) -> dict:
    """
    Evaluates a draft reply for faithfulness and completeness.
    Returns a JSON object with scores and a pass/fail flag.
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
        response = judge_llm.invoke(judge_prompt)
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
    Rewrites a rejected draft based on the judge's feedback.
    """
    revision_prompt = f"""
You are a customer support agent named Enzo Auditore (Employee ID: 2022A7PS0293G) from Abstergo Industries.

Your previous draft was rejected by our quality checker for the following reason:
{feedback}

### Context (Ground Truth)
{context}

### User Question
{question}

### Your Previous Draft (REJECTED)
{draft}

CRITICAL RULES FOR THE REWRITE:
1. Use the customer's first name from the Customer Profile (NOT a placeholder like {{Customer}}).
2. DO NOT include a subject line in the email body.
3. Your signature MUST be: Enzo Auditore, Employee ID: 2022A7PS0293G, Abstergo Industries
4. Stick strictly to the context – do not add information not in the Knowledge Base Articles.
5. Directly answer the user's question.

Rewrite the draft following these rules strictly. Write it as a complete email reply with:
- A professional greeting using the customer's first name.
- A clear, well-structured body that answers the question.
- Your signature (Enzo Auditore, Employee ID: 2022A7PS0293G, Abstergo Industries).
"""
    response = llm.invoke([HumanMessage(content=revision_prompt)])
    return response.content


def clean_email_body(reply: str) -> str:
    """
    Cleans up the email body by removing subject lines and leftover placeholders.
    """
    lines = reply.split("\n")
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that start with "Subject:" (case-insensitive)
        if line.strip().lower().startswith("subject:"):
            continue
        cleaned_lines.append(line)
    
    # Remove any lingering {PII_X} placeholders (just in case)
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r'\{PII_\d+\}', '[REDACTED]', cleaned_text)
    
    return cleaned_text


# ========================================
# 🚀 Main Processing Function
# ========================================

def process_query(user_email: str, user_input: str, send_email_flag: bool = True) -> str:
    """
    Process a customer query using a RAG-augmented LLM pipeline.

    Steps:
    1. PII Redaction – Redact sensitive data before it reaches the LLM.
    2. Retrieve customer facts from memory (SQLite).
    3. Fetch customer profile from the CRM.
    4. Keyword-classify the ticket for context.
    5. Retrieve relevant knowledge base articles via vector search.
    6. Retrieve conversation history for multi-turn chat.
    7. Assemble all context and call the LLM once.
    8. Run LLM-as-Judge self-correction (if enabled).
    9. Restore PII in the final reply.
    10. Clean the email body (remove subject lines, leftover placeholders).
    11. Save the exchange to conversation memory.
    12. Send the generated reply as an email to the customer's address (optional).
    """

    # ========================================
    # 🛡️ PII REDACTION
    # ========================================
    redacted_input, pii_map = redact_pii(user_input)
    if pii_map:
        print(f"🔒 Redacted {len(pii_map)} PII items")
    clean_input = redacted_input

    # ========================================
    # 1. LONG-TERM CUSTOMER FACTS
    # ========================================
    facts = get_facts(user_email, clean_input, k=3)
    facts_str = "\n".join(f"  - {f}" for f in facts) if facts else "  None recorded."

    # ========================================
    # 2. CRM CUSTOMER PROFILE
    # ========================================
    customer_info = json.loads(get_customer_info.invoke({"email": user_email}))
    customer_name = customer_info.get("name", "Customer")

    # ========================================
    # 3. TICKET CLASSIFICATION
    # ========================================
    classification = json.loads(classify_ticket.invoke({
        "title": clean_input[:60],
        "description": clean_input,
    }))

    # ========================================
    # 4. RAG RETRIEVAL
    # ========================================
    docs = retriever.invoke(clean_input)
    kb_context = "\n\n".join(d.page_content for d in docs) if docs else "No relevant articles found."

    # ========================================
    # 5. CONVERSATION HISTORY
    # ========================================
    history = get_conversation(user_email)
    history_str = format_history_for_prompt(history)

    # ========================================
    # 6. ASSEMBLE CONTEXT
    # ========================================
    context = f"""\
=== Customer Profile ===
Name    : {customer_name}
Email   : {customer_info.get('email', user_email)}
Plan    : {customer_info.get('plan', 'Unknown')}
Tickets : {', '.join(customer_info.get('tickets', [])) or 'None'}

=== Ticket Classification ===
Category : {classification.get('category', 'general')}
Priority : {classification.get('priority', 'low')}
Sentiment: {classification.get('sentiment', 'neutral')}

=== Long-term Customer Notes ===
{facts_str}

=== Relevant Knowledge Base Articles ===
{kb_context}

=== Recent Conversation History ===
{history_str}
"""

    # ========================================
    # 7. LLM GENERATION
    # ========================================
    messages = [
        SystemMessage(content=SYSTEM_PROMPT + "\n\n" + context),
        HumanMessage(content=clean_input),
    ]
    reply = llm.invoke(messages).content

    # ========================================
    # 8. LLM-AS-JUDGE SELF-CORRECTION LOOP
    # ========================================
    USE_JUDGE = os.getenv("USE_LLM_JUDGE", "True").lower() == "true"

    if USE_JUDGE and kb_context != "No relevant articles found.":
        print("🧑‍⚖️ Running LLM Judge on draft...")
        judgment = judge_reply(clean_input, kb_context, reply)

        if not judgment.get("pass", True):
            print(f"❌ Draft failed. Feedback: {judgment.get('feedback')}")
            print("🔄 Regenerating draft with feedback...")
            reply = revise_reply(clean_input, kb_context, reply, judgment.get("feedback", "Be more accurate."))
            print("✅ Revised draft generated.")
        else:
            print("✅ Draft passed quality check.")

    # ========================================
    # 9. RESTORE PII
    # ========================================
    reply = restore_pii(reply, pii_map)

    # ========================================
    # 10. CLEAN EMAIL BODY
    # ========================================
    reply = clean_email_body(reply)

    # ========================================
    # 11. SAVE TO CONVERSATION MEMORY
    # ========================================
    add_to_conversation(user_email, user_input, reply)
    print(f"💾 Conversation saved for {user_email} ({len(get_conversation(user_email))} messages)")

    # ========================================
    # 🎯 NAME FALLBACK (if the LLM still fails to use the name)
    # ========================================
    if customer_name and customer_name.lower() not in reply[:200].lower():
        lines = reply.split("\n")
        # Remove any existing generic greeting
        while lines and (lines[0].strip().lower().startswith("dear") or 
                         lines[0].strip().lower().startswith("hi") or 
                         lines[0].strip().lower().startswith("hello")):
            lines.pop(0)
        reply = f"Dear {customer_name},\n\n" + "\n".join(lines)

    # ========================================
    # 12. SEND EMAIL (if enabled)
    # ========================================
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

    return {"reply": reply, "sentiment": classification.get("sentiment", "neutral")}