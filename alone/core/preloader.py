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

    # Step 2: Pre-load Whisper into RAM
    try:
        # Dynamically register CUDA paths to environment for faster_whisper if on cuda
        whisper_cfg = config.get("whisper", {})
        device = whisper_cfg.get("device", "cpu")
        compute_type = whisper_cfg.get("compute_type", "int8")
        
        if device == "cuda":
            cuda_paths = [
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3\bin",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2\bin",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0\bin",
                r"C:\Program Files\NVIDIA\CUDNN\v9.0\bin",
                r"C:\Program Files\NVIDIA\CUDNN\v8.9\bin"
            ]
            for path in cuda_paths:
                if os.path.exists(path) and path not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + path
                    print(f"[*] Dynamically registered CUDA path: {path}")

        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(
            whisper_cfg.get("model_size", "base.en"),
            device=device,
            compute_type=compute_type
        )
        print("[ALONE] Whisper ready ✅")
    except Exception as e:
        print(f"[ALONE] Whisper warmup failed: {e}")

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

def get_whisper_model():
    return _whisper_model
