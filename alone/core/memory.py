import os
import uuid
import time
from datetime import datetime
import chromadb  # type: ignore
from chromadb import EmbeddingFunction, Documents, Embeddings  # type: ignore

# Persistent storage paths
db_path = os.path.expanduser("~/.alone/memory")
os.makedirs(db_path, exist_ok=True)

# Custom Local Embedding Function using sentence-transformers
class LocalEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # type: ignore
        # Disable tokenizers warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        print(f"[*] Loading local SentenceTransformer model '{model_name}' (approx. 80MB)...")
        self.model = SentenceTransformer(model_name)
        print("[+] Embedding model loaded successfully.")

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self.model.encode(input, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

# Initialize ChromaDB persistent client and collections
try:
    client = chromadb.PersistentClient(path=db_path)
    embedding_fn = LocalEmbeddingFunction()
    
    memory_col = client.get_or_create_collection(
        name="alone_memory", 
        embedding_function=embedding_fn
    )
    pref_col = client.get_or_create_collection(
        name="alone_preferences", 
        embedding_function=embedding_fn
    )
except Exception as e:
    print(f"[!] Critical Error initializing ChromaDB: {e}")
    # Bounded fallback to prevent system crash
    client = None
    memory_col = None
    pref_col = None

def add_memory(role: str, content: str, metadata: dict = None):
    """Stores text with timestamp + role as metadata in ChromaDB."""
    if memory_col is None or not content.strip():
        return
        
    if metadata is None:
        metadata = {}
        
    timestamp = time.time()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    doc_id = f"mem_{uuid.uuid4()}"
    
    meta = {
        "role": role,
        "timestamp": timestamp,
        "date": date_str,
        **metadata
    }
    
    try:
        memory_col.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id]
        )
    except Exception as e:
        print(f"[Memory Warning] Failed to add memory: {e}")

def retrieve_context(query: str, top_k: int = 3) -> str:
    """Returns top_k most semantically similar past memories as a formatted string."""
    if memory_col is None or not query.strip():
        return ""
        
    try:
        results = memory_col.query(
            query_texts=[query],
            n_results=top_k
        )
        
        if not results or not results["documents"] or not results["documents"][0]:
            return ""
            
        formatted_memories = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        
        for doc, meta in zip(documents, metadatas):
            role = meta.get("role", "user")
            date = meta.get("date", "Unknown Date")
            formatted_memories.append(f"[{date}] {role.capitalize()}: {doc}")
            
        return "\n".join(formatted_memories)
    except Exception as e:
        print(f"[Memory Warning] Context retrieval failed: {e}")
        return ""

def clear_last_memory() -> str:
    """Deletes the most recent entry from ChromaDB."""
    if memory_col is None:
        return "Memory system is offline, Sir."
        
    try:
        data = memory_col.get()
        if not data or not data["ids"]:
            return "No memories found to forget, Sir."
            
        metadatas = data["metadatas"]
        ids = data["ids"]
        
        # Sort memories in python by timestamp
        valid_entries = []
        for doc_id, meta in zip(ids, metadatas):
            if meta and "timestamp" in meta:
                valid_entries.append((doc_id, meta["timestamp"]))
                
        if not valid_entries:
            return "No recent memories with timestamps found, Sir."
            
        valid_entries.sort(key=lambda x: x[1], reverse=True)
        latest_id = valid_entries[0][0]
        
        memory_col.delete(ids=[latest_id])
        return "I have forgotten the last memory entry, Sir."
    except Exception as e:
        return f"I apologize, Sir, but I failed to forget the last memory: {e}"

def get_session_summary() -> str:
    """Returns all memories recorded today, sorted chronologically."""
    if memory_col is None:
        return "Memory system is offline, Sir."
        
    try:
        data = memory_col.get()
        if not data or not data["ids"]:
            return "No memories recorded today, Sir."
            
        today_prefix = datetime.now().strftime("%Y-%m-%d")
        entries = []
        
        documents = data["documents"]
        metadatas = data["metadatas"]
        
        for doc, meta in zip(documents, metadatas):
            if meta and "date" in meta and meta["date"].startswith(today_prefix):
                entries.append((doc, meta.get("role", "user"), meta.get("timestamp", 0)))
                
        if not entries:
            return "No memories recorded today, Sir."
            
        # Sort chronologically (oldest to newest)
        entries.sort(key=lambda x: x[2])
        
        formatted = []
        for doc, role, ts in entries:
            formatted.append(f"{role.capitalize()}: {doc}")
            
        return "\n".join(formatted)
    except Exception as e:
        return f"I apologize, Sir, but I failed to retrieve today's session summary: {e}"

def save_preference(key: str, value: str):
    """Saves a preference key-value pair in a separate ChromaDB collection."""
    if pref_col is None:
        return
        
    try:
        pref_id = f"pref_{key.lower().strip()}"
        
        existing = pref_col.get(ids=[pref_id])
        if existing and existing["ids"]:
            pref_col.update(
                ids=[pref_id],
                documents=[value],
                metadatas=[{"key": key}]
            )
        else:
            pref_col.add(
                ids=[pref_id],
                documents=[value],
                metadatas=[{"key": key}]
            )
    except Exception as e:
        print(f"[Memory Warning] Failed to save preference '{key}': {e}")

def get_preference(key: str) -> str:
    """Retrieves a preference by key from ChromaDB preference collection."""
    if pref_col is None:
        return None
        
    try:
        pref_id = f"pref_{key.lower().strip()}"
        existing = pref_col.get(ids=[pref_id])
        if existing and existing["documents"]:
            return existing["documents"][0]
        return None
    except Exception as e:
        print(f"[Memory Warning] Failed to retrieve preference '{key}': {e}")
        return None
