import os
import uuid
from datetime import datetime
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Path for the vector memory store
MEMORY_VECTOR_PATH = os.getenv("MEMORY_VECTOR_PATH", "./data/memory_chroma")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Init embedding and vector store (collection = "user_memories")
embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

memory_store = Chroma(
    persist_directory=MEMORY_VECTOR_PATH,
    embedding_function=embedding,
    collection_name="user_memories"
)

def init_db():
    """
    No longer needed, but we keep the function name for compatibility.
    The vector store is automatically created on first use.
    """
    pass

def save_fact(email: str, fact: str):
    """
    Save a fact as a vector, attached to the user's email.
    """
    doc_id = f"{email}_{uuid.uuid4().hex[:8]}"
    metadata = {
        "email": email,
        "timestamp": datetime.now().isoformat()
    }
    memory_store.add_texts(
        texts=[fact],
        metadatas=[metadata],
        ids=[doc_id]
    )
    memory_store.persist()

def get_facts(email: str, query: str = "", k: int = 3) -> list:
    """
    Retrieve the most semantically relevant facts for this user.
    If query is empty, fallback to a generic search.
    """
    if not query:
        query = "general"   # fallback – will still return some facts for this email

    # Use metadata filter to only get facts from this user
    results = memory_store.similarity_search(
        query,
        k=k,
        filter={"email": email}
    )
    return [doc.page_content for doc in results]