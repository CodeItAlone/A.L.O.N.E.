import threading
import ollama
import yaml
import os
import sys

_ready = threading.Event()
_whisper_model = None

# Ensure project root is in path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(base_dir, "config.yaml")
sys.path.append(base_dir)

with open(config_path, "r") as f:
    config = yaml.safe_load(f)

def prewarm():
    global _whisper_model
    print("[ALONE] Pre-warming all systems...")

    # Start Memory Web Server
    try:
        from core.memory_server import start_server
        start_server()
    except Exception as e:
        print(f"[ALONE] Failed to start Memory Server: {e}")

    # Step 1: Wake up Ollama — loads model into VRAM
    try:
        ollama.chat(
            model=config["model"],
            messages=[{"role": "user", "content": "ok"}],
            keep_alive="60m"
        )
        print("[ALONE] LLM ready ✅")
    except Exception as e:
        print(f"[ALONE] LLM warmup failed: {e}")

    # Step 2: Pre-load Speech-to-Text Provider into RAM
    try:
        from core.stt_provider import get_stt_provider as init_provider
        import time
        
        provider_type = config.get("stt_provider", "whisper")
        start_time = time.time()
        
        print(f"[STT] Audio Received (Pre-warm initialization)")
        _stt_provider = init_provider(provider_type, config)
        
        latency = time.time() - start_time
        print(f"[STT] Provider Loaded: {type(_stt_provider).__name__}")
        print(f"[STT] Latency: {latency:.4f}s")
        print("[ALONE] Speech-to-Text ready ✅")
    except Exception as e:
        print(f"[ALONE] Speech-to-Text warmup failed: {e}")

    # Step 3: Pre-load OWW wake word model
    try:
        from core.listener import load_wakeword_model
        load_wakeword_model()
        print("[ALONE] Wake word model ready ✅")
    except Exception as e:
        print(f"[ALONE] OWW warmup failed: {e}")

    _ready.set()
    print("[ALONE] All systems pre-warmed ✅")

def wait_until_ready(timeout=120):
    _ready.wait(timeout=timeout)
    return _ready.is_set()

def get_stt_provider():
    return _stt_provider

def get_whisper_model():
    return _stt_provider
