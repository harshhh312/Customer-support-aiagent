"""
In‑memory conversation memory for multi‑turn chat.
Stores the last N exchanges per user.
"""

from collections import defaultdict, deque
from typing import List, Dict, Any

# Configuration
MAX_HISTORY_LENGTH = 6  # 3 exchanges (user + assistant = 1 exchange)

# In‑memory storage: email -> deque of messages
_conversations: Dict[str, deque] = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY_LENGTH)
)

def get_conversation(email: str) -> List[Dict[str, str]]:
    """
    Returns the conversation history for a given user.
    Each message is a dict: {"role": "user" or "assistant", "content": "..."}
    """
    return list(_conversations[email])

def add_to_conversation(email: str, user_msg: str, assistant_msg: str) -> None:
    """
    Adds a new exchange to the user's conversation history.
    """
    history = _conversations[email]
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": assistant_msg})

def clear_conversation(email: str) -> None:
    """
    Clears the entire conversation history for a user.
    """
    if email in _conversations:
        _conversations[email].clear()

def format_history_for_prompt(history: List[Dict[str, str]]) -> str:
    """
    Formats the conversation history into a string for the LLM prompt.
    """
    if not history:
        return "No previous conversation."
    
    lines = []
    for msg in history:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    
    return "\n".join(lines)