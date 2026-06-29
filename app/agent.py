import os
from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from .tools import classify_ticket, get_customer_info, update_ticket, draft_email
from .rag import get_retriever
from .memory import get_facts
from langchain.tools import tool

# --- LLM (must be a chat model for tool-calling) ---
llm = ChatOllama(
    model=os.getenv("LLM_MODEL", "llama3"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
)

# --- Build the RAG retriever and wrap as a @tool ---
retriever = get_retriever()

@tool
def search_knowledge_base(query: str) -> str:
    """Search the internal knowledge base for articles relevant to a customer query."""
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant articles found."
    return "\n\n".join([doc.page_content for doc in docs])

# All tools the agent can use
TOOLS = [
    classify_ticket,
    get_customer_info,
    update_ticket,
    draft_email,
    search_knowledge_base,
]

SYSTEM_PROMPT = """\
You are a helpful customer support AI agent. Use the available tools to assist customers.

When answering:
- Search the knowledge base first for policy or product questions.
- Use GetCustomerInfo when you need customer account details.
- Use ClassifyTicket to categorise a support request.
- Use UpdateTicket to change a ticket status or add a note.
- Use DraftEmail to compose email replies.

Always be concise, empathetic, and professional.
"""

def create_agent_with_user(email: str):
    """Create an agent executor for a specific user, injecting their long-term facts."""
    facts = get_facts(email)
    facts_str = "\n".join(facts) if facts else "No known facts about this customer."

    system = f"{SYSTEM_PROMPT}\n\nLong-term facts about this customer:\n{facts_str}"

    agent = create_agent(model=llm, tools=TOOLS, system_prompt=system)
    return agent

def process_query(user_email: str, user_input: str) -> str:
    """Run the agent for a given user email and input message."""
    agent = create_agent_with_user(user_email)
    # create_agent returns a CompiledStateGraph; invoke with messages list
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
    # The last message in the output is the assistant's reply
    messages = result.get("messages", [])
    if messages:
        last_msg = messages[-1]
        # Handle both dict and AIMessage object
        if hasattr(last_msg, "content"):
            return last_msg.content
        return last_msg.get("content", str(last_msg))
    return "I'm sorry, I couldn't generate a response."