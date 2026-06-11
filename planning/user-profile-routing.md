# User Profile Memory Storage Routing Plan

This document outlines the root cause analysis, architecture findings, proposed modifications, and verification plan for fixing the user profile persistence and routing in A.L.O.N.E.

---

## 🔍 Discovery Findings

### 1. Existing Storage Layer (SQLite + ChromaDB)

A.L.O.N.E. operates a hybrid persistent memory store:
- **SQLite (`~/.alone/human_memory.db`)**: Used for structured facts.
  - `user_profile` table:
    ```sql
    CREATE TABLE user_profile (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```
  - `preferences` table: Structured preference settings.
  - `projects`, `goals`, `relationships` tables: Structured database records.
- **ChromaDB (`~/.alone/memory/`)**: Stores semantic vector embeddings.
  - Collection `alone_profile_vector`: Syncs keys and values from the `user_profile` table for semantic query capabilities.

### 2. Existing Profile Save/Retrieve Methods

In [alone/core/human_memory/database.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/human_memory/database.py):
- `get_profile()`: Queries and returns all rows from the `user_profile` table as a dictionary. Logs each field using `[MEMORY RETRIEVE]`.
- `set_profile_field(key, value)`: Inserts or updates the field, logging `[MEMORY SAVE]` (for new fields) or `[MEMORY UPDATE]` (for existing ones), and verifies persistence.
- `delete_profile_field(key)`: Deletes the given field.

In [alone/core/human_memory/service.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/human_memory/service.py):
- `sync_profile_to_vector()`: Synchronizes SQLite profile keys/values into the `alone_profile_vector` collection.
- `get_active_context_summary()`: Compiles a context summary block of profile, active projects, goals, and relationships.

### 3. Existing Intent Routing Flow

In [alone/core/agent.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/agent.py):
- Spoken/written inputs run through `determine_intent(user_input)`.
- **Heuristics Classifier (`heuristics_classify`)**: Checks for simple pattern prefixes to classify as `SYSTEM_COMMAND`, `MEMORY_STORE`, `MEMORY_RETRIEVE`, `TOOL_EXECUTION`, or `GENERAL_CHAT`.
- **LLM Classifier (`llm_classify`)**: If heuristics return `None`, queries the LLM with a classification prompt.
- **Direct Router in `run`**:
  - `MEMORY_RETRIEVE`: Direct route to `retrieve_memory_and_respond()` or preference/project query handlers.
  - `GENERAL_CHAT`: CASUAL conversation handling (using ChatOllama).
  - `MEMORY_STORE`: Routes to `handle_preference_update` or `handle_project_intents`.
  - Fallback: ReAct agent execution with system tools via `AgentExecutor`.

---

## 🛑 Root Cause Analysis

1. **Missing Intent Classification**: Profile update statements like `"My name is Subrato..."` are not matched by any heuristic in `heuristics_classify` and are classified as `GENERAL_CHAT` (or occasionally `MEMORY_STORE` without match handlers).
2. **Missing Routing Branch**: There is no direct route for `USER_PROFILE_UPDATE`. The input is treated as `GENERAL_CHAT`.
3. **Conversational Hallucination**: The LLM responds politely ("I've updated your profile...") because its system prompt instructs it to be helpful, but no Python function call actually saves the extracted attributes to SQLite.
4. **Lack of Extraction Service**: There is no dedicated service to extract arbitrary attributes (e.g. name, role, education) from natural language inputs and pass them to the persistence layer.

---

## 🛠️ Proposed Modifications

### 1. Add `UserProfileService`
Create/declare `UserProfileService` in [alone/core/human_memory/service.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/human_memory/service.py) (or as a separate importable service).
- **`UserProfileService.extract(text: str) -> dict`**: Prompt the LLM to extract key-value pairs (e.g. name, education, role) as structured JSON from natural language statements.
- **`UserProfileService.save(extracted: dict)`**:
  - Save each key-value pair to SQLite using `database.set_profile_field(key, value)`.
  - Synchronize to the vector store (`service.sync_profile_to_vector()`).
  - Print structured logs (`[PROFILE DETECTED]`, `[PROFILE SAVE]`, `[PROFILE UPDATE]`).
  - Read back stored fields to verify write correctness (`[PROFILE VERIFY]`).

### 2. Introduce `USER_PROFILE_UPDATE` Intent
- Add regex heuristic checks in `heuristics_classify` matching starting patterns (`my name is`, `i am a`, etc.).
- Update `llm_classify` prompt to include the new `USER_PROFILE_UPDATE` category.

### 3. Route `USER_PROFILE_UPDATE` Direct Flow
In `AloneAgent.run()`:
```
USER_PROFILE_UPDATE 
→ UserProfileService.extract()
→ UserProfileService.save() 
→ UserProfileService.retrieve() (for prompt confirmation context)
→ natural confirmation response generated from retrieved database profile
```

---

## 📂 Files to Change

1. **[alone/core/agent.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/agent.py)**:
   - Add regex heuristic checks and update intent classifiers to return `USER_PROFILE_UPDATE`.
   - Add routing logic in `AloneAgent.run()` to invoke `UserProfileService`.
   - Add structured `[PROFILE RETRIEVE]` logging in `retrieve_memory_and_respond()`.
2. **[alone/core/human_memory/service.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/human_memory/service.py)**:
   - Add the `UserProfileService` class.

---

## ⚠️ Risks & Mitigation

- **Heuristic False Positives**: Overly broad `i am` matches could intercept tool requests.
  - *Mitigation*: Ensure profile heuristics require personal identifiers or run after command-specific check heuristics.
- **JSON Parsing Failures**: Ollama/LLM output might have extra text during JSON extraction.
  - *Mitigation*: Implement standard fallback parsing regex to pull JSON objects from LLM response text blocks.

---

## 🧪 Verification Plan

A new test suite **[alone/tests/test_user_profile_routing.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/tests/test_user_profile_routing.py)** will be written matching the system's testing conventions.

- **Test 1: Profile Save**: Inputs `"My name is Subrato."` saves to SQLite DB.
- **Test 2: Profile Update**: Inputs `"I am a second year engineering student."` updates profile keys.
- **Test 3: Profile Retrieve**: Inputs `"Who am I?"` outputs formatted name/education.
- **Test 4: Restart Persistence**: Instantiate new `AloneAgent` after save and confirm retrieved data still exists.
- **Test 5: Duplicate Prevention**: Inputs `"My name is Subrato Kundu."` updates the single key `name` rather than creating a duplicate.
