from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
import ollama
import os
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Global state
ensemble_retriever = None
qdrant_client = QdrantClient(url="http://localhost:6333",api_key=os.getenv("QDRANT_API_KEY"))
embedder = OllamaEmbeddings(model="nomic-embed-text", base_url="http://localhost:11434")
COLLECTION_NAME = "visionvault_parent_child_v1"

def build_ensemble_retriever():
    global ensemble_retriever
    
    # 1. Setup Qdrant Retriever
    vector_store = QdrantVectorStore(
        client=qdrant_client, 
        collection_name=COLLECTION_NAME, 
        embedding=embedder
    )
    qdrant_retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    # 2. Scroll through Qdrant to get all payloads for BM25
    documents = []
    offset = None
    while True:
        records, offset = qdrant_client.scroll(
            collection_name=COLLECTION_NAME, 
            offset=offset,
            limit=100, 
            with_payload=True,
            with_vectors=False
        )
        
        for record in records:
            payload = record.payload or {}
            metadata = dict(payload.get("metadata") or {})

            # Support LangChain's usual payload key and existing "text" payloads.
            child_text = payload.get("page_content") or payload.get("text")

            if child_text:
                documents.append(
                    Document(
                        page_content=child_text,
                        metadata=metadata
                    )
                )
                
        if offset is None:
            break
            
    # 3. Setup BM25 Retriever from memory
    if documents:
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = 3
        
        # 4. Bind together
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, qdrant_retriever],
            weights=[0.5, 0.5]
        )
        print(f"[+] Ensemble Retriever initialized with {len(documents)} chunks.")
    else:
        print("[-] No documents found in Qdrant. Falling back to strict Vector Search.")
        ensemble_retriever = qdrant_retriever

# 5. Lifespan event to trigger build on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Starting API and building BM25 index...")
    build_ensemble_retriever()
    yield
    print("[*] Shutting down...")

app = FastAPI(lifespan=lifespan)

class QueryRequest(BaseModel):
    query: str

@app.post("/api/chat")
async def chat_endpoint(req: QueryRequest):
    if not ensemble_retriever:
        return {"error": "Retriever not initialized"}
        
    docs = ensemble_retriever.invoke(req.query)
        # Use each matching child's parent text once as the model context.
    parent_contexts = {}

    for doc in docs:
        metadata = doc.metadata or {}
        parent_text = metadata.get("parent_text") or doc.page_content
        parent_id = metadata.get("parent_id") or parent_text
        parent_contexts.setdefault(parent_id, parent_text)

    context_text = "\n\n".join(parent_contexts.values())
    system_prompt = f"""
    You are a helpful AI assistant. Answer the user's query using ONLY the information provided in the context below. 

    first analyse that the user is asking a ques or he just want a normal communication, then give answers accordingly 

    If the answer is not contained in the context, simply say "I cannot find the answer in the provided document." Do not copy and paste the context directly; instead, summarize the relevant points to answer the question.

    Context: 
    {context_text}
    """    
    response = ollama.chat(
        model="llama3.2:3b",
        keep_alive=-1,
        stream=False,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.query}
        ]
    )
    
    return {"response": response['message']['content'], "context": context_text}

# 6. Webhook to refresh the index manually
@app.post("/api/refresh-index") 
async def refresh_index():
    build_ensemble_retriever()
    return {"message": "BM25 Index rebuilt successfully"}
