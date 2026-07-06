import os
from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/chroma_db")
KNOWLEDGE_BASE_PATH = "./data/knowledge_base"

embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

@lru_cache(maxsize=1)
def get_document_chunks():
    if not os.path.exists(KNOWLEDGE_BASE_PATH):
        os.makedirs(KNOWLEDGE_BASE_PATH)
        return []
    loader = DirectoryLoader(KNOWLEDGE_BASE_PATH, glob="**/*.txt", loader_cls=TextLoader)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    return chunks

def load_and_index_knowledge_base():
    get_document_chunks.cache_clear()
    chunks = get_document_chunks()
    if not chunks:
        print("⚠️ No documents found to index.")
        return None
    vectorstore = Chroma.from_documents(chunks, embedding, persist_directory=VECTOR_DB_PATH)
    print(f"✅ Indexed {len(chunks)} chunks into Chroma DB.")
    return vectorstore

def reciprocal_rank_fusion(bm25_results, vector_results, k=60):
    """
    Combines two ranked lists using Reciprocal Rank Fusion (RRF).
    Returns a list of Document objects, not strings.
    """
    scores = {}
    doc_map = {}  # Store content -> Document object

    # Process BM25 results (already Document objects)
    for rank, doc in enumerate(bm25_results, start=1):
        content = doc.page_content
        doc_map[content] = doc  # Store the actual Document object
        scores[content] = scores.get(content, 0) + 1 / (k + rank)

    # Process Vector results (already Document objects)
    for rank, doc in enumerate(vector_results, start=1):
        content = doc.page_content
        doc_map[content] = doc  # Store the actual Document object
        scores[content] = scores.get(content, 0) + 1 / (k + rank)

    # Sort by score and return the actual Document objects
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_contents = [item[0] for item in sorted_items[:4]]  # Get top 4 content strings
    
    # Convert back to Document objects
    return [doc_map[content] for content in top_contents]

def get_hybrid_retriever():
    """
    Returns a custom hybrid retriever.
    """
    if not os.path.exists(VECTOR_DB_PATH):
        load_and_index_knowledge_base()
    
    vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding)
    chunks = get_document_chunks()
    
    if not chunks:
        return vectorstore.as_retriever(search_kwargs={"k": 4})
    
    bm25_retriever = BM25Retriever.from_documents(chunks)
    bm25_retriever.k = 8

    def hybrid_search(query: str):
        bm25_docs = bm25_retriever.invoke(query)
        vector_docs = vectorstore.similarity_search(query, k=8)
        merged_docs = reciprocal_rank_fusion(bm25_docs, vector_docs, k=60)
        return merged_docs  # Returns List[Document], not strings!

    return hybrid_search

def get_retriever():
    hybrid_fn = get_hybrid_retriever()
    
    class HybridRetrieverWrapper:
        def invoke(self, query):
            return hybrid_fn(query)  # Returns List[Document]
    
    return HybridRetrieverWrapper()