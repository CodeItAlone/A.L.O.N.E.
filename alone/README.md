# A.L.O.N.E. 🤖
### *An Autonomous, Local-First AI Voice Assistant with Computer Control*

A.L.O.N.E. is a local AI personal assistant built to operate completely offline on your local machine. By combining LangChain-based ReAct agent reasoning with an optimized real-time voice pipeline and computer automation tools, A.L.O.N.E. functions as a fully capable, hands-free companion.

---

## 🏛️ System Architecture

A.L.O.N.E.'s architecture is divided into three key systems:

```
                  ┌──────────────────────────────┐
                  │          THE VOICE           │
                  │ (openWakeWord, Whisper, SAPI)│
                  └──────────────┬───────────────┘
                                 │ Audio Capture
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

1. **The Voice (Audio Pipeline)**: Handles continuous wake-word standby, dynamic ambient room noise calibration, local Whisper speech-to-text transcription, and a thread-safe SAPI5 speech synthesis queue.
2. **The Brain (Cognitive Layer)**: A LangChain-driven local agent using Ollama (`llama3.1:8b`) to interpret user queries, manage conversational memory, and autonomously plan tool executions.
3. **The Hands (Automation Layer)**: A set of system-level integration tools enabling the assistant to open applications, run shell commands, browse the web, write code, and control standard desktop tools.

---

## 🛠️ Key Technical Implementations & Workarounds

To guarantee highly stable, real-time operations on Windows, the system incorporates three specialized architectural breakthroughs:

### 1. Non-Blocking Async Speech Queue
To prevent the main execution thread from freezing during audio playback, the system uses a queue-based text-to-speech design. String responses are enqueued non-blockingly via `speak_async()`, while the main loop regularly polls and drains the queue via `process_speech_queue()` in a fluid, non-blocking tick loop.

### 2. Thread-Safe SAPI5 COM Isolation
Windows SAPI (`pyttsx3`) relies on the COM Single-Threaded Apartment (STA) model, raising errors if invoked from audio processing background threads. SAPI initialization and execution are fully isolated and run **exclusively** on the dedicated Main Thread during queue drainage.

### 3. Dynamic Sounddevice Stream Recreation (Bypassing MME Error 33)
The Windows MME audio driver locks sound devices exclusively during SAPI playback, blocking `sounddevice` from resuming the microphone capture stream. A.L.O.N.E. resolves this by:
* Instantiating SAPI locally inside each speech block and explicitly garbage collecting the COM resources immediately afterward.
* Toggling simple state flags on pause/resume, letting the background audio thread completely **close** the active microphone `InputStream` on pause, and negotiate a **completely fresh** stream binding on resume.

---

## 📁 Repository Structure

```text
alone/
├── artifacts/             # Engineering reports and documentation
├── core/
│   ├── agent.py           # LangChain ReAct agent brain & memory
│   ├── brain.py           # Ollama client connection
│   ├── listener.py        # openWakeWord mic loop & calibration
│   ├── speaker.py         # Thread-safe speech queue & local SAPI5
│   └── transcriber.py     # Faster-Whisper audio transcription
├── tools/
│   ├── browser.py         # OS browser integration
│   ├── search.py          # Search web automation
│   ├── system.py          # OS utility commands (e.g. run_shell)
│   └── writer.py          # File writing tools
├── config.yaml            # Model urls, voice parameters, & audio settings
├── main.py                # Main application loop and thread coordinator
├── requirements.txt       # Python dependencies
└── venv/                  # Local python virtual environment
```

---

## 🚀 Getting Started

### 📋 Prerequisites
* **Python**: Python 3.10 or 3.11 recommended.
* **Ollama**: Installed and running locally.
* **FFmpeg**: Required on your system path for Faster-Whisper transcriptions.

### ⚙️ Setup and Installation

1. **Activate Local Virtual Environment**:
   ```powershell
   .\venv\Scripts\activate
   ```

2. **Pull the Configured LLM**:
   Verify that your Ollama server is running, and pull your configured model (as specified in `config.yaml`):
   ```powershell
   ollama pull llama3.1:8b
   ```

3. **Verify Dependencies**:
   Ensure all local dependencies are fully installed inside the active virtual environment:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Launch the Assistant**:
   ```powershell
   python main.py
   ```

---

## 🎙️ Operating A.L.O.N.E.

* **Mic Calibration**: At startup, remain quiet for 1.5 seconds so the system can measure ambient room noise. The dynamic threshold is safely capped at `800.0` to prevent noise spikes from desensitizing wake-word detection.
* **Wake Word Trigger**: Say **`hey_jarvis`** clearly. A soft chime will sound, indicating that the assistant is actively recording your query.
* **Fallback Keyboard Entry**: You can type queries directly into the terminal prompt whenever the continuous listener is awaiting the wake word.
