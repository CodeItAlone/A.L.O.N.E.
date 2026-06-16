# Developer & Contributor Guide

Welcome to the **A.L.O.N.E.** Developer Guide. This document provides codebase walkthroughs, repository directory mapping, manual setup procedures, and a comprehensive code quality audit.

---

## 📁 Repository Directory Structure

```plaintext
C:\Users\SHAN KUMAR\Desktop\ALONE
├── .agent/                    # AI specialist rules, skills, and checklists
├── docs/                      # Architectural and voice pipeline documentation
│   ├── ARCHITECTURE.md
│   ├── DEVELOPER_GUIDE.md     # This file
│   ├── MEMORY_SYSTEM.md
│   ├── PROJECT_OVERVIEW.md
│   ├── ROADMAP.md
│   └── VOICE_PIPELINE.md
└── alone/                     # Main assistant codebase root
    ├── Modelfile              # Ollama model definition file
    ├── config.yaml            # Port, model, audio, and VAD parameters
    ├── launch_alone.bat       # Direct background runtime launcher
    ├── main.py                # Main entry point and GUI event loop
    ├── setup.bat              # One-time virtual environment builder
    ├── requirements.txt       # Core dependencies file
    ├── core/                  # Core modules
    │   ├── __init__.py
    │   ├── agent.py           # LangChain ReAct agent & QUICK_COMMANDS
    │   ├── brain.py           # ChatOllama prompt context generator
    │   ├── listener.py        # openwakeword stream & WebRTC/energy VAD
    │   ├── memory.py          # ChromaDB semantic client
    │   ├── preloader.py       # Asynchronous prewarming thread
    │   ├── speaker.py         # Thread-safe speech queue & TTS
    │   └── transcriber.py     # Whisper transcription wrapper
    ├── tools/                 # LangChain automation tools
    │   ├── __init__.py
    │   ├── browser.py         # Selenium web tools
    │   ├── files.py           # File CRUD tools
    │   ├── search.py          # DuckDuckGo search tools
    │   └── system.py          # App launching, typing, screenshots, shell commands
    ├── ui/                    # PyQt5 Graphic files
    │   ├── settings.py        # Settings layout and sliders window
    │   └── window.py          # HUD circular GUI and bubble chimes
    └── tests/                 # Unit and integration test suites
```

---

## 🛠️ Developer Setup & Setup Procedures

### System Requirements
*   **OS**: Windows 10/11 (with system-native `pyttsx3` voice engines SAPI5).
*   **Python**: Python 3.10 to Python 3.14.
*   **Inference Hardware**: Nvidia GPU with CUDA Toolkits is highly recommended for Whisper GPU transcription, though CPU fallback (int8) is supported.

### Manual Installation
1.  Clone the repository.
2.  Navigate to the code directory and run the setup script:
    ```cmd
    cd alone
    setup.bat
    ```
    This script automatically creates a `.venv` virtual environment and installs all requirements from `requirements.txt`.
3.  Ensure **Ollama** is installed and running on your system.
4.  Run the system launcher to boot up the HUD in background pre-warming mode:
    ```cmd
    launch_alone.bat
    ```

---

## 🔬 Comprehensive Code Quality Review

As part of maintaining high-standard engineering, here is a detailed audit of A.L.O.N.E.'s codebase:

### 🌟 Architectural Strengths
1.  **Thread Safety & Responsive TTS**: By offloading heavy audio recording, ONNX inference, and console scanning to background threads, and executing text-to-speech in a dedicated background `TTSWorker` thread (running an isolated Python subprocess for SAPI5 SAPI COM calls on Windows), the GUI remains responsive and avoids both Windows COM threading apartment violations and speech synthesis device locking.
2.  **Low-Latency Bypass**: The `QUICK_COMMANDS` static routing in `core/agent.py` completely side-steps the LLM, enabling zero-latency execution in under 1 second for standard queries.
3.  **Graceful Audio Fallback**: The voice listener features automatic hardware checks and falls back from standard WebRTC VAD C-bindings to high-precision energy-based RMS voice activity detection, ensuring the system runs smoothly across standard installations.

### ⚠️ Architectural Weaknesses & Refactoring Opportunities
1.  **Hardcoded Paths**: Startup `.vbs` shortcuts use absolute path configurations which must be manually edited.
    *   *Refactoring Opportunity*: Add automatic project directory resolution into `setup.bat` to write the `.vbs` launcher dynamically.
2.  **Monolithic Tool File**: `tools/system.py` contains multiple massive automation tools (app mapping, scanning, typing, screenshot capture).
    *   *Refactoring Opportunity*: Split `tools/system.py` into modular, focused files (e.g. `tools/system/screenshots.py`, `tools/system/typing.py`, `tools/system/registry.py`) to increase maintainability.

### ⏱️ Performance Bottlenecks & Scalability Concerns
1.  **Ollama cold-starts**: If the local LLM is unloaded, the first request faces a cold-start delay.
    *   *Mitigation*: Prewarmer resolves this on boot. Setting `keep_alive="60m"` in ChatOllama keeps it pinned in VRAM.
2.  **ChromaDB scaling**: Semantic search retrieves records by reading all indices recursively. This remains extremely fast for local desktop use (<10ms) but may scale linearly as hundreds of thousands of conversational exchanges are recorded.
    *   *Mitigation*: Periodically run index compressions or archive histories beyond a certain timestamp.

---

## 🧪 Testing Guidelines

A.L.O.N.E. uses `pytest` for unit and integration testing.

### Running the Test Suite
Activate your virtual environment and execute pytest from the repository root:
```bash
.\venv\Scripts\activate.bat
pytest
```
*Note: Ensure Ollama is running if running integrations test cases.*
