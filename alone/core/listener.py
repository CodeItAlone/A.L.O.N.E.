import os
import time
import wave
import threading
import collections
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
import tempfile

class Listener:
    def __init__(self, sample_rate=16000, chunk_size=1280):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        # Simple energy-based VAD instead of webrtcvad (for better compatibility)
        self.vad_threshold = 300  # Adjust based on background noise
        
        # Initialize wake word model
        # Note: on first run, this will download the model (~5MB)
        self.oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        
        self.is_listening = False
        self.is_recording = False
        self._stop_event = threading.Event()
        
    def _play_beep(self):
        """Plays a soft beep sound using numpy/sounddevice"""
        duration = 0.1  # seconds
        frequency = 1000  # Hz
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        beep = np.sin(frequency * t * 2 * np.pi)
        # Ensure it's in int16 for sounddevice if that's what we are using
        beep = (beep * 32767).astype(np.int16)
        sd.play(beep, self.sample_rate)
        sd.wait()

    def start_listening(self, callback):
        """Runs the listener loop in a background thread"""
        self._stop_event.clear()
        thread = threading.Thread(target=self._listen_loop, args=(callback,))
        thread.daemon = True
        thread.start()
        return thread

    def stop(self):
        self._stop_event.set()

    def _is_speech(self, audio_data):
        """Simple energy-based VAD"""
        return np.abs(audio_data).mean() > self.vad_threshold

    def _listen_loop(self, callback):
        print("\n[*] ALONE: Listening for wake word ('Hey Jarvis' proxy)...")
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
                while not self._stop_event.is_set():
                    audio_chunk, overflow = stream.read(self.chunk_size)
                    audio_data = audio_chunk.flatten()
                    
                    # Get wake word prediction
                    prediction = self.oww_model.predict(audio_data)
                    
                    # If "hey_jarvis" detected (threshold > 0.5)
                    if prediction.get("hey_jarvis", 0) > 0.5:
                        print("\n[!] Wake word detected!")
                        self._play_beep()
                        print("ALONE: [Listening...]")
                        
                        audio_path = self._record_command(stream)
                        if audio_path:
                            callback(audio_path)
                        
                        print("[*] ALONE: Awaiting wake word...")
        except Exception as e:
            print(f"[!] Listener Stream Error: {e}")

    def _record_command(self, stream, max_duration=8, silence_timeout=1.5):
        """Records audio until silence is detected or max_duration reached"""
        start_time = time.time()
        frames = []
        silent_chunks = 0
        max_silent_chunks = int(silence_timeout * (self.sample_rate / self.chunk_size))
        
        # Record until silence or timeout
        while time.time() - start_time < max_duration:
            audio_chunk, overflow = stream.read(self.chunk_size)
            audio_data = audio_chunk.flatten()
            frames.append(audio_data.copy())
            
            if not self._is_speech(audio_data):
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            if silent_chunks > max_silent_chunks:
                break
        
        if not frames:
            return None
            
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"alone_command_{int(time.time())}.wav")
        
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(np.concatenate(frames).tobytes())
            
        return file_path
