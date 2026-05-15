# PLAN: Phase 2 — The Hands (Computer Control)

## Overview
This phase upgrades A.L.O.N.E. from a basic chatbot to a functional AI Assistant using LangChain's Tool-calling and Agent capabilities. We are giving the "Brain" (Phase 1) "The Hands" (System, File, Browser, and Coder tools).

## Project Type
**BACKEND / SYSTEM AUTOMATION (Python)**

## Success Criteria
- [x] Plan Created
- [ ] All 5 tool modules implemented in `alone/tools/`
- [ ] LangChain `ReAct` Agent implemented in `alone/core/agent.py`
- [ ] `main.py` successfully routes requests to the Agent
- [ ] Passing the "10 Command Challenge" without crashes

## Tech Stack
- **Orchestration**: LangChain (AgentExecutor)
- **LLM**: ChatOllama (llama3.1)
- **Automation**: PyAutoGUI, Subprocess
- **Browser**: Selenium, Webbrowser
- **Search**: DuckDuckGo-Search

## File Structure
```plaintext
alone/
├── data/
│   ├── screenshots/       # Screenshot storage
│   └── generated_code/    # Generated scripts
├── tools/
│   ├── __init__.py        # Tool exporter
│   ├── system.py          # App/Shell control
│   ├── browser.py         # Web navigation
│   ├── coder.py           # Code generation/exec
│   ├── files.py           # File system ops
│   └── search.py          # Web search/summarization
└── core/
    ├── brain.py           # (Existing) LLM logic
    └── agent.py           # (New) Agent & Tool registration
```

## Task Breakdown

### P0: Foundation & Environment
- [ ] **Task 1**: Create `alone/data/` subfolders.
- [ ] **Task 2**: Install dependencies (`langchain`, `pyautogui`, etc.).

### P1: Tool Implementation
- [ ] **Task 3**: Implement `tools/system.py` (subprocess/pyautogui logic).
- [ ] **Task 4**: Implement `tools/files.py` (Safe file operations).
- [ ] **Task 5**: Implement `tools/browser.py` & `tools/search.py`.
- [ ] **Task 6**: Implement `tools/coder.py` (Ollama integration for code gen).

### P2: Agent Orchestration
- [ ] **Task 7**: Create `core/agent.py` and register all tools.
- [ ] **Task 8**: Define the Agent prompt and ReAct logic.

### P3: Integration & Testing
- [ ] **Task 9**: Update `main.py` to use the Agent layer.
- [ ] **Task 10**: Execute the "10 Command Challenge" and verify.

## Phase X: Final Verification
- [ ] Live execution of all 10 commands.
- [ ] Error handling check (invalid file paths, disconnected Ollama).
- [ ] Persona consistency during tool use.
