import os
import sys
from faster_whisper import WhisperModel
import ctranslate2

def _add_cuda_to_path():
    """Finds and adds NVIDIA pip package library paths to the OS PATH (Windows fix)"""
    if sys.platform != "win32":
        return
        
    # Try to find nvidia package paths in site-packages
    import site
    package_dirs = site.getsitepackages()
    if hasattr(site, 'getusersitepackages'):
        package_dirs.append(site.getusersitepackages())
        
    # venv fallback
    package_dirs.append(os.path.join(sys.prefix, "Lib", "site-packages"))
        
    for base in package_dirs:
        nvidia_path = os.path.join(base, "nvidia")
        if os.path.exists(nvidia_path):
            # Check for cublas and cudnn bin folders
            for sub in ["cublas", "cudnn"]:
                bin_path = os.path.join(nvidia_path, sub, "bin")
                if os.path.exists(bin_path):
                    if bin_path not in os.environ["PATH"]:
                        os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]
                        print(f"[*] Added {sub} to PATH")

# Fix CUDA paths before initializing model
_add_cuda_to_path()

class Transcriber:
    def __init__(self, model_size="base.en", device="cpu", compute_type="int8"):
        """
        Initialize the Whisper model.
        device: "cuda" or "cpu"
        compute_type: "int8", "float16", etc.
        """
        # Auto-detect CUDA if device is not specified or if "cuda" is requested
        cuda_available = False
        try:
            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except:
            pass

        if device == "cuda" and not cuda_available:
            print("[!] CUDA requested but not available. Falling back to CPU.")
            device = "cpu"
            compute_type = "int8"
        elif device == "cuda":
            # For RTX 5050, float16 is usually faster than int8
            compute_type = "float16"
            
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.confidence_threshold = 0.6

    def transcribe(self, audio_path):
        """
        Transcribe audio file to text.
        Returns: text string
        """
        if not os.path.exists(audio_path):
            return ""

        segments, info = self.model.transcribe(audio_path, beam_size=5, vad_filter=True)
        
        full_text = []
        confidences = []
        
        for segment in segments:
            full_text.append(segment.text)
            # segment.avg_logprob is a log probability, we can convert to 0-1 range
            # but usually, we just take the text if it's not silence
            # segment.no_speech_prob is also useful
            confidences.append(1.0 - segment.no_speech_prob)

        if not full_text:
            return ""

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        if avg_confidence < self.confidence_threshold:
            return ""

        return " ".join(full_text).strip()

# Singleton instance
_transcriber_instance = None

def get_transcriber(config=None):
    global _transcriber_instance
    if _transcriber_instance is None:
        model_size = config.get('whisper', {}).get('model_size', 'base.en') if config else 'base.en'
        device = "cuda" # Defaulting to cuda as requested by user
        _transcriber_instance = Transcriber(model_size, device=device)
    return _transcriber_instance
