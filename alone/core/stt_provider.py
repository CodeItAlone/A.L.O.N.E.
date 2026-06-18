import os
import sys
import time

class SpeechToTextProvider:
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError

    def transcribe_stream(self, audio_chunk) -> str:
        return ""

    def get_confidence(self) -> float:
        return 1.0

    def get_language(self) -> str:
        return "en"

class WhisperProvider(SpeechToTextProvider):
    def __init__(self, model_size="base.en", device="cpu", compute_type="int8"):
        from faster_whisper import WhisperModel
        
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

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        self.language = "en"

    def transcribe(self, audio_path: str) -> str:
        if not os.path.exists(audio_path):
            return ""
        segments, _ = self.model.transcribe(
            audio_path,
            language=self.language,
            vad_filter=True,
            initial_prompt="Hey Alone, ok alone."
        )
        return " ".join([s.text for s in segments]).strip()

    def get_language(self) -> str:
        return self.language


class ParakeetProvider(SpeechToTextProvider):
    def __init__(self, model_name="nvidia/parakeet-tdt-0.6b-v3", device="cpu"):
        import torch
        import nemo.collections.asr as nemo_asr
        
        self.device = device
        # Load the pretrained NVIDIA Parakeet TDT model
        self.model = nemo_asr.models.ASRModel.from_pretrained(model_name=model_name)
        
        if device == "cuda" and torch.cuda.is_available():
            self.model = self.model.cuda()
        else:
            self.model = self.model.cpu()
            
        self.model.eval()

    def transcribe(self, audio_path: str) -> str:
        if not os.path.exists(audio_path):
            return ""
        # NeMo transcribe expects a list of file paths and handles batching
        results = self.model.transcribe([audio_path])
        if results and len(results) > 0:
            # Return transcription text. In NeMo, transcribe returns a list of strings
            return str(results[0]).strip()
        return ""


def get_stt_provider(provider_type: str, config: dict) -> SpeechToTextProvider:
    whisper_cfg = config.get("whisper", {})
    parakeet_cfg = config.get("parakeet", {})

    if provider_type == "parakeet":
        try:
            print("[STT] Loading ParakeetProvider...")
            model_name = parakeet_cfg.get("model_name", "nvidia/parakeet-tdt-0.6b-v3")
            device = parakeet_cfg.get("device", "cpu")
            return ParakeetProvider(model_name=model_name, device=device)
        except Exception as e:
            print(f"[STT] Failed to initialize ParakeetProvider: {e}")
            if parakeet_cfg.get("fallback_to_whisper", True):
                print("[STT] Falling back to WhisperProvider...")
            else:
                raise e

    # Default to Whisper
    print("[STT] Loading WhisperProvider...")
    return WhisperProvider(
        model_size=whisper_cfg.get("model_size", "base.en"),
        device=whisper_cfg.get("device", "cpu"),
        compute_type=whisper_cfg.get("compute_type", "int8")
    )
