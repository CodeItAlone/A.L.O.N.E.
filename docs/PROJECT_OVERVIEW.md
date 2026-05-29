# A.L.O.N.E. — Project Overview

> **A.L.O.N.E.** (Just A Rather Very Intelligent System — *A Local Offline Networked Entity*) is a fully local, privacy-respecting, voice-controlled personal AI assistant modeled after sci-fi digital butlers.

---

## 🌟 The Vision

In an era dominated by cloud-based AI systems that monetize user data, require costly recurring subscription fees, and fail when internet connections drop, **A.L.O.N.E.** provides a secure, fully local alternative.

Designed to operate entirely on a user's laptop or workstation, A.L.O.N.E. combines voice activity detection, offline speech-to-text, a local ReAct agent model, semantic vector database storage, and zero-latency system automation to act as your local hardware-linked digital partner.

---

## 🛠️ Problems A.L.O.N.E. Solves

| Problem in Cloud AI | A.L.O.N.E. Solution |
| :--- | :--- |
| **Privacy Vulnerability** | All raw voice recordings, transcripts, and session memories are stored in an offline database on local storage. No data ever leaves your computer. |
| **Subscription & API Costs** | Completely free to operate. Runs on open-weights models and local inference engines (Ollama, Whisper). |
| **Internet Dependency** | Fully operational offline. Ideal for traveling, field operations, and secure air-gapped workstations. |
| **Sluggish System Integration** | Integrates directly with Windows API/processes, enabling rapid application launching, keystroke typing, and system automation. |

---

## 👥 Target Audience

*   **Developers & Power Users**: Enthusiasts who want a customizable terminal-and-voice butler capable of opening apps, executing scripts, and writing code locally.
*   **Privacy Advocates**: Users who require absolute confidentiality for their documents, conversations, and personal schedules.
*   **Offline Professionals**: Field engineers, developers, and writers working in low-connectivity environments.

---

## 🚀 Key Features

### 🎙️ 1. Continuous Voice Pipeline
*   **Always-On Wake Word**: Active wake-word listening with negligible CPU footprint via `openwakeword` using pre-trained and custom `.tflite` models.
*   **Voice Activity Detection (VAD)**: Dynamic sound capturing powered by WebRTC VAD and energy calibration. Cuts off instantly (600ms) on silence and limits recording to a hard 9-second window.

### 🧠 2. CUDA-Accelerated Local Transcription
*   Uses `faster-whisper` on GPU (float16 CUDA) or CPU (int8) to perform fast, highly accurate local speech-to-text transcription.

### 🧩 3. Local LLM ReAct Agent
*   Driven by **ChatOllama** utilizing a custom optimized model (`alone-model` derived from `llama3.2:3b`).
*   Leverages a **ReAct** (Reasoning and Acting) execution pattern to select, validate, and execute local operating system tools safely.

### 💾 4. Long-Term Semantic Memory
*   Maintains structured long-term semantic recollections across sessions using an offline **ChromaDB** vector database.
*   Converts transcripts and interactions into high-quality vector embeddings locally via `SentenceTransformers` (`all-MiniLM-L6-v2`), dynamically injecting historical context back into the agent's prompts.

### 🖥️ 5. Zero-Latency Quick Commands
*   An integrated hardcoded system-instruction parser bypasses LLM inference completely for frequent commands (opening YouTube/GitHub/VS Code, dates, times, screenshots). Delivers zero-latency execution in under 1 second.

---

## 📊 Development Stage

A.L.O.N.E. has advanced beyond a Minimum Viable Product (MVP) into a **stable, low-latency release stage**. 

Recent updates have successfully resolved historical bottlenecks like boot cold-starts, virtual environment duplicate bloats, wake word misdetections, and lagging speech-end cutoff thresholds. The project is highly optimized for daily desktop use on Windows environments.
