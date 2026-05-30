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
2. **The Suit (PyQt5 HUD)**: A beautiful, frameless floating overlay sitting in the bottom-right of your screen. Features real-time audio waveform animations (scaling with mic input RMS levels), a pulsing circle during thinking loops, user/response text rows, and a system tray icon with a complete settings configuration panel.
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

## ⚙️ Robust Synchronization & VAD Fixes

To guarantee smooth hands-free desktop operations and prevent continuous loop locks, we implemented two key architectural refinements:

1. **Systematic Wake Word Verification in Active Listening**:
   Refined the continuous VAD Fallback listening engine inside `core/listener.py` to prioritize wake word matching even during the 15-second follow-up window. This ensures that saying "hey alone" to trigger a new command plays the chime immediately, resets the standby recording loop, and captures the fresh command cleanly without returning early to `IDLE` or causing Whisper to transcribe hallucinated static noise (like *"I'll see you"*).
2. **Global Platform Resolution**:
   Fixed settings GUI startup path shortcuts by resolving a local scope NameError in `alone/ui/settings.py` for `platform.system()`, migrating OS detection to a clean global import.

---

## ⚠️ Known Limitations

1. **Speech Queue apartment COM locks**: SAPI5 speech synthesis is restricted strictly to the Main Thread event loop (managed via QTimers) to prevent access violation crashes during thread crossovers.
2. **Device Stream Locks**: On Windows, default audio devices will lock exclusively during pyttsx3 speech operations, blocking simultaneous Whisper listener audio stream binding. A.L.O.N.E. bypasses this by closing and tearing down active `InputStream` bindings during pause/resume state cycles.
3. **Frameless Window Draggability**: HUD Window does not have standard OS frame handles. Double-click and drag the container frame directly to reposition it on screen.
