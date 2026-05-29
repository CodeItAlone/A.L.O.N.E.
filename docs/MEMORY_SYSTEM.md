# Semantic Memory System

A.L.O.N.E. maintains structured long-term semantic recollections and personal preferences across boot sessions using a local persistent vector database.

---

## 🏗️ Memory Architecture

The database is built on **ChromaDB** and uses **SentenceTransformers** to compute text vector embeddings completely offline.

```
[ User Prompt / Interaction ]
              │
              ├──> [ SentenceTransformer (all-MiniLM-L6-v2) ] ──> [ 384-Dim Float Vector ]
              │                                                             │
              ▼                                                             ▼
[ Context Prompt Injection ] <── [ Top-K Semantic Query ] <─── [ ChromaDB Persistent Client ]
```

---

## 🧩 Key Technologies

### 1. ChromaDB Vector DB
*   Operates as a persistent serverless embedded database stored on local disk.
*   Path: `~/.alone/memory/`

### 2. SentenceTransformers
*   Uses the **`all-MiniLM-L6-v2`** model.
*   **Size**: ~80 MB.
*   **Vector Dimensionality**: 384 dimensions.
*   **Performance**: Selected for its exceptionally small memory footprint, fast CPU/GPU inference, and high semantic matching accuracy.

---

## 💾 Core Memory Structures (Collections)

A.L.O.N.E. separates stored data into two distinct collections inside the vector database:

1.  **`alone_memory`**: Stores user inputs, assistant replies, and intermediate system tool execution results. Each item is tagged with metadata (timestamp, date, execution role).
2.  **`alone_preferences`**: Key-value metadata storage. Used to remember explicit facts (e.g. user name, favorite apps, main project directories).

---

## 🔄 Memory Processes

### 1. The Storage Process
Every conversation exchange and tool result is committed to memory using the `add_memory` function:

*   **Id Generation**: A unique identifier is generated using `uuid.uuid4()` (e.g. `mem_xxxx-xxxx-xxxx`).
*   **Vectorization**: The text content is converted into a 384-dimensional vector array.
*   **Commit**: Stored with metadata (timestamp, date-string, actor role) inside the ChromaDB collection:
    ```python
    meta = {
        "role": role,
        "timestamp": time.time(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ```

### 2. The Semantic Retrieval Process
Before executing any LLM agent logic, A.L.O.N.E. queries past memories to fetch historical context:

*   **Query Vectorization**: The incoming user prompt is encoded into a 384-dim vector.
*   **Similarity Match**: ChromaDB performs a cosine-similarity distance search against all stored records in `alone_memory`.
*   **Dynamic Prompt Injection**: The top-3 matches are retrieved, formatted chronologically, and injected directly into the LLM system prompt as context:
    ```plaintext
    Relevant context from past sessions:
    [2026-05-28 14:10:05] User: My primary project path is C:\Users\Shan\Desktop\Project
    [2026-05-28 14:10:32] Assistant: Understood, Sir. I will remember that path.
    ```

---

## 📈 Advantages and Limitations

### Advantages:
*   **Absolute Privacy**: Vector storage and text similarity calculations are performed 100% offline. No data is sent to external clouds.
*   **Cross-Session Persistence**: A.L.O.N.E. does not suffer from "amnesia" on reboot. It retains your preferences, directory structures, and names permanently.
*   **Low Footprint**: ChromaDB and `all-MiniLM-L6-v2` load in less than 2 seconds and occupy minimal RAM (~120MB total).

### Limitations:
*   **Context Window Bloat**: Injecting highly detailed past context consumes LLM context tokens.
*   **No Multi-User Separation**: Currently runs on a single user profile based on the OS home directory (`~`).
