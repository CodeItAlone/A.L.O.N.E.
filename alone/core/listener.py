import os
import time
import wave
import tempfile
import threading
import numpy as np
import sounddevice as sd
import yaml
from openwakeword.model import Model

_stream = None
_paused = False
_listening = True

# Load config
def _load_config(path="config.yaml"):
    if not os.path.exists(path):
        if os.path.exists("../config.yaml"):
            path = "../config.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

config = _load_config()
sample_rate = 16000
keyword = config.get('voice', {}).get('wake_word', "hey_jarvis")
threshold = config.get('voice', {}).get('openwakeword_threshold', 0.5)
ptt_mode = config.get('voice', {}).get('ptt_mode', False)
energy_threshold = 200.0
oww_model = None

# Wrapper to support PyAudio API style calling
class SounddeviceStreamWrapper:
    def __init__(self, stream):
        self._stream = stream
    
    def is_active(self):
        return self._stream.active
        
    def stop_stream(self):
        self._stream.stop()
        
    def start_stream(self):
        self._stream.start()
        
    def close(self):
        self._stream.close()
        
    def read(self, frames):
        return self._stream.read(frames)

def check_enter_pressed():
    """Non-blocking check to see if ENTER was pressed in the console."""
    try:
        import msvcrt
        if msvcrt.kbhit():
            is_enter = False
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'\r', b'\n'):
                    is_enter = True
            return is_enter
    except ImportError:
        import sys
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0.0)
        if r:
            sys.stdin.readline() # Consume the entered text
            return True
    return False

def calibrate_threshold(duration=1.5):
    """Automatically calibrates energy threshold based on ambient room noise."""
    global energy_threshold
    print("[*] Calibrating microphone for ambient room noise... Please remain silent.")
    samples_to_record = int(sample_rate * duration)
    try:
        recording = sd.rec(samples_to_record, samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        
        chunks = [recording[i:i+1280] for i in range(0, len(recording), 1280) if len(recording[i:i+1280]) == 1280]
        rms_values = [np.sqrt(np.mean(c.astype(np.float32) ** 2)) for c in chunks]
        
        if rms_values:
            mean_rms = np.mean(rms_values)
            max_rms = np.max(rms_values)
            # Cap the threshold to a maximum of 800.0 to prevent noise spikes from blocking speech recognition
            energy_threshold = min(max(mean_rms * 1.5, max_rms * 1.2, 100.0), 800.0)
            print(f"[+] Calibration complete. Set Energy Threshold: {energy_threshold:.2f}")
        else:
            energy_threshold = 200.0
            print(f"[!] Calibration completed with no chunks. Using default energy threshold: {energy_threshold}")
    except Exception as e:
        energy_threshold = 200.0
        print(f"[!] Dynamic calibration failed ({e}). Using default energy threshold: {energy_threshold}")

def init_oww():
    """Initializes openWakeWord engine."""
    global oww_model, ptt_mode
    if not ptt_mode:
        print(f"[*] Initializing openWakeWord engine for model: '{keyword}'...")
        try:
            oww_model = Model(
                wakeword_models=[keyword],
                inference_framework="onnx"
            )
            print("[+] openWakeWord engine initialized successfully.")
        except Exception as e:
            print(f"[!] Failed to initialize openWakeWord: {e}")
            print("[!] Switching default listening state to Push-To-Talk Fallback Mode.")
            ptt_mode = True

def _play_beep():
    """Plays a soft beep sound"""
    duration = 0.1
    frequency = 1000
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    beep = np.sin(frequency * t * 2 * np.pi)
    beep = (beep * 32767).astype(np.int16)
    try:
        sd.play(beep, sample_rate)
        sd.wait()
    except Exception as e:
        print(f"[!] Failed to play beep: {e}")

def pause_listening():
    global _paused
    _paused = True

def resume_listening():
    global _paused
    _paused = False

def stop_listening():
    global _listening, _stream
    _listening = False
    try:
        if _stream:
            _stream.close()
            _stream = None
        print("[ALONE] Listener stopped")
    except Exception as e:
        print(f"[ALONE] Exception in stop_listening: {e}")

def start_listening(callback):
    """Starts/runs the background listening process"""
    global _listening
    _listening = True
    
    init_oww()
    calibrate_threshold()
    
    _listen_loop(callback)

def _listen_loop(callback):
    global _stream, _listening, _paused
    
    if ptt_mode or not oww_model:
        print("[*] Transitioning to Push-To-Talk Fallback Mode...")
        _ptt_loop(callback)
        return

    print(f"\n[*] ALONE: Continuous Listening active. Say '{keyword}' to activate.")
    chunk_len = 1280  # openWakeWord expects 1280 samples chunk at 16kHz
    
    try:
        while _listening:
            if not _paused:
                if _stream is None:
                    try:
                        # Let Windows release audio device from any previous playback first
                        time.sleep(0.4)
                        raw_stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_len)
                        _stream = SounddeviceStreamWrapper(raw_stream)
                        raw_stream.start()
                        print("[ALONE] Mic stream started successfully")
                    except Exception as e:
                        print(f"[ALONE] Failed to start mic stream (waiting for device release...): {e}")
                        time.sleep(0.5)
                        continue
                
                try:
                    audio_chunk, overflow = _stream._stream.read(chunk_len)
                    audio_data = audio_chunk.flatten()
                    
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                    
                    if rms < energy_threshold:
                        prob = 0.0
                    else:
                        prediction = oww_model.predict(audio_data)
                        prob = prediction.get(keyword, 0.0)
                    
                    if prob >= threshold:
                        print(f"\n[!] Wake word detected! Confidence: {prob:.2f}")
                        _play_beep()
                        print("ALONE: [Listening...]")
                        
                        audio_path = _record_command(_stream._stream)
                        if audio_path:
                            callback(audio_path)
                        
                        oww_model.reset()
                        print(f"[*] ALONE: Awaiting '{keyword}'...")
                except Exception as ex:
                    print(f"[!] InputStream read error (closing stream): {ex}")
                    try:
                        if _stream:
                            _stream.close()
                    except Exception:
                        pass
                    _stream = None
                    time.sleep(0.1)
            else:
                if _stream:
                    try:
                        _stream.close()
                    except Exception:
                        pass
                    _stream = None
                    print("[ALONE] Mic stream closed")
                time.sleep(0.05)
    except Exception as e:
        print(f"[!] Microphone/Stream error: {e}")
        print("[*] Falling back to Push-To-Talk Mode due to stream failure...")
        _ptt_loop(callback)


def _ptt_loop(callback):
    """PTT loop does not continuously stream mic to save CPU. It waits for CLI triggers."""
    global _listening
    print("[*] PTT Fallback mode active. Press ENTER on empty line in console to speak.")
    while _listening:
        time.sleep(0.5)

def _record_command(stream, max_duration=8, silence_timeout=1.5):
    """Records from the active stream until silence or max duration"""
    global _paused, _listening
    start_time = time.time()
    frames = []
    silent_chunks = 0
    chunk_len = 1280
    max_silent_chunks = int(silence_timeout * (sample_rate / chunk_len))
    
    try:
        while time.time() - start_time < max_duration and _listening:
            if _paused:
                time.sleep(0.05)
                continue
                
            audio_chunk, overflow = stream.read(chunk_len)
            audio_data = audio_chunk.flatten()
            frames.append(audio_data.copy())
            
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            if rms < energy_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            if silent_chunks > max_silent_chunks:
                print("[*] Silence detected in command.")
                break
    except Exception as e:
        print(f"[!] Recording error: {e}")
        
    if not frames:
        return None
        
    temp_path = os.path.join(tempfile.gettempdir(), f"alone_cmd_{int(time.time())}.wav")
    try:
        with wave.open(temp_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(np.concatenate(frames).tobytes())
        return temp_path
    except Exception as e:
        print(f"[!] Failed to save audio file: {e}")
        return None

def record_ptt_command(max_duration=10, silence_timeout=1.8):
    """Records from the microphone until the user presses ENTER or silence is detected."""
    global _stream
    frames = []
    chunk_len = 1024
    start_time = time.time()
    silent_chunks = 0
    max_silent_chunks = int(silence_timeout * (sample_rate / chunk_len))
    
    check_enter_pressed()
    
    try:
        raw_stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_len)
        _stream = SounddeviceStreamWrapper(raw_stream)
        raw_stream.start()
        
        print("[*] Speak now...")
        while time.time() - start_time < max_duration:
            audio_chunk, overflow = raw_stream.read(chunk_len)
            audio_data = audio_chunk.flatten()
            frames.append(audio_data.copy())
            
            if check_enter_pressed():
                print("[*] ENTER pressed. Stopping recording...")
                break
                
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            if rms < energy_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            if silent_chunks > max_silent_chunks:
                print("[*] Silence detected. Stopping recording...")
                break
    except Exception as e:
        print(f"[!] PTT recording stream error: {e}")
        return None
    finally:
        if _stream:
            _stream.close()
            _stream = None
        
    if not frames:
        return None
        
    temp_path = os.path.join(tempfile.gettempdir(), f"alone_ptt_{int(time.time())}.wav")
    try:
        with wave.open(temp_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(np.concatenate(frames).tobytes())
        print("[*] Recording stopped. Transcribing...")
        return temp_path
    except Exception as e:
        print(f"[!] Failed to save audio file: {e}")
        return None
