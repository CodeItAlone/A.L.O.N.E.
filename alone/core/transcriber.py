from faster_whisper import WhisperModel
import os

class Transcriber:
    def __init__(self, model_size="base.en", device="cpu", compute_type="int8"):
        self.vad_filter = True
        self.model = None
        
        if device == "cuda":
            print("[*] Checking CUDA availability and PATH configuration for Whisper...")
            try:
                # Add typical Windows CUDA toolkit and cuDNN paths dynamically to PATH env var
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
                
                # Attempt to initialize WhisperModel on GPU
                # Using float16 for CUDA standard speedup
                self.model = WhisperModel(model_size, device="cuda", compute_type="float16")
                print(f"[+] Whisper initialized successfully with GPU CUDA acceleration (float16). Model: '{model_size}'")
                return
            except Exception as e:
                print(f"[!] CUDA initialization failed: {e}")
                print("[!] This is usually due to missing Windows CUDA dlls (cublas64_12.dll or cudnn_ops_infer64_12.dll).")
                print("[!] Falling back gracefully to optimized CPU inference (int8)...")
        
        # CPU Fallback
        try:
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(f"[+] Whisper initialized successfully on CPU (int8). Model: '{model_size}'")
        except Exception as e:
            print(f"[!] Critical Error: Failed to initialize Whisper on CPU: {e}")
            self.model = None

    def transcribe(self, audio_path):
        """Transcribes audio file to text using faster-whisper"""
        if not os.path.exists(audio_path):
            return ""

        if not self.model:
            print("[!] Transcription failed: WhisperModel is not initialized.")
            return ""

        try:
            segments, info = self.model.transcribe(
                audio_path, 
                beam_size=5, 
                vad_filter=self.vad_filter,
                language="en"
            )
            
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text)
            
            full_text = " ".join(text_segments).strip()
            
            if not full_text:
                return ""
            
            return full_text
            
        except Exception as e:
            print(f"[!] Transcription error: {e}")
            return ""

def get_transcriber(config):
    whisper_cfg = config.get('whisper', {})
    return Transcriber(
        model_size=whisper_cfg.get('model_size', 'base.en'),
        device=whisper_cfg.get('device', 'cpu'),
        compute_type=whisper_cfg.get('compute_type', 'int8')
    )

_transcriber_instance = None

def transcribe(audio_path):
    from core.preloader import get_whisper_model
    model = get_whisper_model()
    if model is None:
        # Fallback: load fresh if prewarm failed
        from faster_whisper import WhisperModel
        import yaml
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        whisper_cfg = config.get("whisper", {})
        device = whisper_cfg.get("device", "cpu")
        compute_type = whisper_cfg.get("compute_type", "int8")
        
        # Dynamically register CUDA paths to environment for faster_whisper if on cuda
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

        model = WhisperModel(
            whisper_cfg.get("model_size", "base.en"),
            device=device,
            compute_type=compute_type
        )
    segments, _ = model.transcribe(
        audio_path,
        language="en",
        vad_filter=True
    )
    return " ".join([s.text for s in segments]).strip()

