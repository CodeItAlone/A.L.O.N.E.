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

## 💾 Core Memory Structures (Hybrid System)

A.L.O.N.E. separates stored data into two distinct database layers:

1.  **`alone_memory` (ChromaDB Vector DB)**: Stores conversational logs, user inputs, and intermediate system tool executions. Used for similarity searches and dynamically injecting past context.
2.  **`preferences` (SQLite Database)**: Stores personal preference settings inside a local SQLite database (`~/.alone/human_memory.db`). Features structured category mappings (`development`, `communication`, `assistant`, `productivity`, `general`) to store verified preference facts.

---

## 🔄 Memory Processes

### 1. SQLite Preference Storage & Verification
Preferences are managed by `PreferenceService` ([core/preferences_service.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/preferences_service.py)):
*   **Write**: Values are written using SQL `INSERT INTO ... ON CONFLICT(key) DO UPDATE` to guarantee overwrite safety and prevent duplicate records.
*   **Validation Check**: The database is queried immediately post-save to verify that the value matches the request. Output is logged as `[Preference Validation Passed]` or `[Preference Validation Failed]`.
*   **Migration**: On startup, a background synchronization routine copies legacy ChromaDB preferences over to SQLite structured tables.

### 2. Conversational Storage & Retrieval
Every conversational turn is vectorized using SentenceTransformers and saved in the ChromaDB vector database. When a user sends a general query, ChromaDB performs a similarity search to inject historical context into the prompt:
```plaintext
=== USER PREFERENCES ===
[Development Preferences]:
  * editor: VS Code
  * programming_language: Python

[Communication Preferences]:
  * user_name: Shan
========================
```

---

## 📈 Advantages and Limitations

### Advantages:
*   **Absolute Privacy**: All database writes and queries are performed locally on-disk.
*   **Overwriting Overwrite Safety**: Categorized preferences are kept unique per-key using SQLite relational rules.
*   **Low footprint**: ChromaDB and SQLite operate in-memory/on-disk with less than 2 seconds initialization.

### Limitations:
*   **Context Window Bloat**: Injected past context consumes LLM tokens.
*   **Single User Profile**: System is limited to a single user profile mapped to the OS home directory (`~`).
