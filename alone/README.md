# A.L.O.N.E. 🤖
### *An Autonomous, Local-First AI Voice Assistant with Computer Control & Floating HUD*

A.L.O.N.E. (Just A Rather Very Intelligent System) is an offline, privacy-first personal assistant running completely locally on your laptop. By combining a LangChain-based ReAct agent reasoning engine with an optimized voice pipeline and local automation tools, A.L.O.N.E. provides premium desktop operations completely hands-free.

---

## 🏛️ System Architecture

```
                  ┌──────────────────────────────┐
                  │          THE VOICE           │
                  │ (openWakeWord, Whisper, SAPI)│
                  └──────────────┬───────────────┘
                                 │ Mic RMS & Status Signals
                                 ▼
                  ┌──────────────────────────────┐
                  │          THE SUIT            │
                  │   (PyQt5 Frameless HUD UI)   │
                  └──────────────┬───────────────┘
                                 │ User Query
                                 ▼
                  ┌──────────────────────────────┐
                  │          THE BRAIN           │
                  │   (LangChain ReAct Agent)    │
                  └──────────────┬───────────────┘
                                 │ Tool Decision
                                 ▼
                  ┌──────────────────────────────┐
                  │          THE HANDS           │
                  │   (System/OS Automation)     │
                  └──────────────────────────────┘
```

1. **The Voice (Audio Pipeline)**: Manages continuous wake-word standby, dynamic ambient room noise calibration, local Whisper speech-to-text transcription, and a thread-safe SAPI5 speech synthesis queue.
2. **The Suit (PyQt5 HUD)**: A beautiful, frameless floating overlay sitting in the bottom-right of your screen. Features real-time audio waveform animations (scaling with mic input RMS levels), a pulsing circle during thinking loops, user/response text rows, a system tray icon with a complete settings configuration panel, and a red-themed "Stop Agent" button at the bottom for quick and clean termination directly from the GUI (with confirmation).
3. **The Brain (Cognitive Layer)**: A local ReAct agent using Ollama (`llama3.1:8b`) to interpret user inputs, manage conversational history, retrieve long-term context from ChromaDB, and schedule tool executions.
4. **The Hands (Automation Layer)**: System-level integration tools enabling the assistant to open apps, run shell commands with intent verification, browse the web, write/execute code, and manipulate files.

---

## 💻 Hardware & Software Requirements

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **OS** | Windows 10/11 (CUDA setup supported) | Windows 10/11 |
| **RAM** | 8 GB RAM (Ollama CPU standard) | 16 GB+ RAM (8B Model standard) |
| **CPU** | 4 Cores, 2.5 GHz | 8 Cores+ (Faster Whisper / LLM inference) |
| **GPU** | Optional (CPU standard works well) | NVIDIA GPU (4GB+ VRAM) for CUDA speedup |
| **Microphone**| Any built-in laptop mic | Dedicated USB microphone or headset |

---

## 🚀 Quick Install Guide (3 Steps)

Get A.L.O.N.E. online on your Windows machine in 3 simple steps:

### Step 1: Clone & Configure
Install Python 3.10 or 3.11 and ensure Ollama is installed and running:
```powershell
ollama pull llama3.1:8b
```

### Step 2: Run Installer
Open the repository folder, navigate to `install` and double-click `setup.bat`.
This will:
* Verify and configure local `~/.alone/` structures and memory folders.
* Install all required dependencies from `requirements.txt`.
* Generate a headless boot shortcut (`ALONE.lnk`) inside the Windows Startup folder.

### Step 3: Launch A.L.O.N.E.
Start the application from the root repository:
```powershell
python main.py
```
*At startup, remain quiet for 1.5 seconds so the microphone can calibrate to ambient room noise.*

---

## 🎙️ Personality & Custom Commands

A.L.O.N.E. possesses a dry, calm, and composed personality. It greets you dynamically based on the time of day ("Good morning", "Good afternoon", "Good evening") and responds with built-in witty Easter eggs for certain questions:
* *"Are you Skynet?"*
* *"Are you ChatGPT?"*
* *"Are you JARVIS?"*
* *"I love you"*

### System Interactions:
* **`alone help` or `what can you do?`**: Instantly prints all registered system automation tools.
* **`forget that`**: Deletes the most recent semantic transaction from ChromaDB memory.
* **`what do you remember?`**: Recalls a chronological summary of all memories recorded in today's session.

---

## 🛠️ How to Add a New Tool

All A.L.O.N.E. tools inherit from LangChain's `@tool` decorator. Add your new tool in 3 simple steps:

1. **Write Tool Definition**: Open [alone/tools/system.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/tools/system.py) and write your python function under the `@tool` decorator:
   ```python
   @tool
   def my_custom_tool(param: str) -> str:
       """Put a highly descriptive docstring here so the ReAct LLM knows when to call it."""
       try:
           # Tool implementation
           return f"Successfully executed with param: {param}"
       except Exception as e:
           return f"Failed: {e}"
   ```

2. **Register Tool**: Import and add your tool inside [alone/tools/__init__.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/tools/__init__.py):
   ```python
   from .system import my_custom_tool
   
   # Add it to the ALL_TOOLS array
   ALL_TOOLS = [
       ...
       my_custom_tool
   ]
   ```

3. **Reload A.L.O.N.E.**: Restart `main.py` and the assistant will automatically register and describe the tool to the LLM during runtime!

## ⚙️ Robust Synchronization & Safety Refinements

To guarantee smooth hands-free desktop operations and prevent background noise loop locks, we implemented three key architectural refinements:

1. **Active Window Safety Layer**:
   Created `FollowUpValidationService` ([core/safety.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/safety.py)) to score transcribed commands. Ambient audio phrases ("thanks for watching", "like and subscribe") are assigned a low confidence level and discarded, preventing random typing or unwanted automation.
2. **Dedicated Background TTS Worker**:
   Refactored the speech output engine in [core/speaker.py](file:///c:/Users/SHAN%20KUMAR/Desktop/ALONE/alone/core/speaker.py) to run on a dedicated background thread. Speech synthesis is handled completely asynchronously, avoiding blocking PyQt5 window visualizers and resolving previous thread-crossover COM crashes.
3. **SQLite Structured Preference Memory**:
   Introduced a local SQLite database for structured preferences inside `core/human_memory/` with validation logs (`[Preference Saved]`, `[Preference Validation Passed]`) and automatic migration of legacy preferences from ChromaDB.

---

## ⚠️ Limitations & Workarounds

1. **Active Listening Window Duration**:
   A.L.O.N.E. operates with a default active follow-up window (configurable, recommended at **5 seconds** for safety). Validation prevents background audio leakages during this active window.
2. **Device Stream Locks**:
   Windows audio devices lock during PyTTSx3 speaking. A.L.O.N.E. handles this by pausing microphone input stream binding during active speaking and resuming after speech completes.
3. **Frameless Window Draggability**:
   The floating HUD window does not have standard OS frame handles. Double-click and drag the container frame directly to reposition it on screen.
