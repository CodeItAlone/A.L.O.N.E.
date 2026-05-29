# Project Roadmap

Development timeline and feature roadmap for the A.L.O.N.E. local personal AI assistant.

---

## 🎯 Current Status
With the successful implementation of the system warming threads, zero-latency quick command bypasses, and openwakeword/VAD custom listener, the assistant has achieved **high daily operational stability** as an offline desktop butler.

---

## 🗺️ Development Phasing

```
[ Phase 1: Stability & Low-Latency ] ──> [ Phase 2: Deep System Memory ] ──> [ Phase 3: Autonomous Desktop Agent ]
        (COMPLETED / CURRENT)                   (MID-TERM GOALS)                     (LONG-TERM VISION)
```

---

## 🚀 Future Roadmap

### ⏱️ Short-Term Goals (Stability & Tuning)

*   [ ] **Microphone Hot-Plugging Support**: Implement automatic sound device recovery in `core.listener` if the USB headset or mic is unplugged and re-plugged at runtime.
*   [ ] **Quick Command Expansion**: Expand the hardcoded bypass dict to cover custom shell-script pipelines, system volume control, and screen brightness adjustments.
*   [ ] **GUI Voice Waveform Visualizer**: Integrate live audio amplitude mapping (`signals.amplitude_received`) to draw a smooth, dynamic voice waveform inside the PyQt5HUD circle, providing visual feedback of speech capture.

### 🧠 Mid-Term Goals (Deep Context & Integration)

*   [ ] **Hybrid Semantic Memory**: Integrate Recency-Weighted Vector Search in `core.memory` to prioritize highly fresh memories alongside semantic similarity.
*   [ ] **Multi-Model VAD Routing**: Train local lightweight models (e.g. Silero VAD) to run on CPU alongside WebRTC VAD to handle exceptionally loud background noise environments (e.g., cafes, office chatter).
*   [ ] **Whisper Transcription Streaming**: Upgrade from chunk-based wav transcription to real-time word-by-word streaming transcription for live typing visualization.
*   [ ] **Context Summarization**: Automatically compress older session logs into concise bullet points inside ChromaDB when history exceeds the context token limit.

### 👁️ Long-Term Vision (Autonomous Multi-Modal Butler)

*   [ ] **Desktop UI Automation**: Upgrade `tools/system.py` from simple launcher and typing scripts to advanced computer control agents using mouse coordinate maps.
*   [ ] **Multi-Modal Vision Capabilities**: Integrate local lightweight vision models (e.g. LLaVA, Qwen-VL) to allow the assistant to analyze screenshots and visual documents on command (e.g. *"Explain what is on my screen right now"*).
*   [ ] **Air-Gapped LAN Hub**: Allow A.L.O.N.E. to act as a secure offline voice assistant hub for other smart home devices over a secure local area network (LAN).
*   [ ] **Custom Local Text-To-Speech**: Replace the standard Windows system pyttsx3 synthesizer with ultra-realistic, low-latency offline neural voice models (e.g. ChatTTS or Kokoro-82M).
