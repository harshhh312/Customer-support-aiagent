import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/chroma_db")

embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def load_and_index_knowledge_base():
    loader = DirectoryLoader("./data/knowledge_base", glob="**/*.txt", loader_cls=TextLoader)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    # persist_directory handles persistence automatically — no need to call .persist()
    vectorstore = Chroma.from_documents(chunks, embedding, persist_directory=VECTOR_DB_PATH)
    return vectorstore

def get_retriever():
    if not os.path.exists(VECTOR_DB_PATH):
        load_and_index_knowledge_base()
    vectorstore = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding)
    return vectorstore.as_retriever(search_kwargs={"k": 4})