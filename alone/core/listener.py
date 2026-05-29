import os
import time
import wave
import tempfile
import threading
import numpy as np
import sounddevice as sd
import yaml
from openwakeword.model import Model

# Try importing webrtcvad
try:
    import webrtcvad
    _has_webrtcvad = True
except ImportError:
    _has_webrtcvad = False

_stream = None
_paused = False
_listening = True

# Load config
def _load_config(path="config.yaml"):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_path):
        config_path = "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

config = _load_config()
sample_rate = 16000
energy_threshold = 200.0
oww_model = None

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
            energy_threshold = min(max(mean_rms * 1.5, max_rms * 1.2, 100.0), 800.0)
            print(f"[+] Calibration complete. Set Energy Threshold: {energy_threshold:.2f}")
        else:
            energy_threshold = 200.0
            print(f"[!] Calibration completed with no chunks. Using default energy threshold: {energy_threshold}")
    except Exception as e:
        energy_threshold = 200.0
        print(f"[!] Dynamic calibration failed ({e}). Using default energy threshold: {energy_threshold}")

def load_wakeword_model():
    """Initializes openWakeWord engine with custom or fallback model."""
    global oww_model
    if oww_model is not None:
        return oww_model
        
    cfg = _load_config()
    ww_cfg = cfg.get("wake_word", {})
    model_path = ww_cfg.get("model_path", "data/hey_alone.tflite")
    fallback_model = ww_cfg.get("fallback_model", "hey_jarvis")
    
    resolved_path = None
    paths_to_try = [
        model_path,
        os.path.join("alone", model_path) if not model_path.startswith("alone") else model_path,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), model_path),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "hey_alone.tflite")
    ]
    for p in paths_to_try:
        if p and os.path.exists(p):
            resolved_path = p
            break
            
    if resolved_path:
        print(f"[ALONE] Loading custom wake word model from: {resolved_path}")
        try:
            oww_model = Model(
                wakeword_models=[resolved_path],
                inference_framework="onnx"
            )
        except Exception as e:
            print(f"[ALONE] Failed to load custom model: {e}. Using fallback.")
            
    if oww_model is None:
        print(f"[ALONE] Loading fallback wake word model: {fallback_model}")
        try:
            oww_model = Model(
                wakeword_models=[fallback_model],
                inference_framework="onnx"
            )
        except Exception as e:
            print(f"[ALONE] Critical: Failed to load fallback model: {e}")
            
    return oww_model

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

def record_until_silence():
    """Records audio from microphone using dynamic VAD configurations."""
    global _listening, _paused
    
    cfg = _load_config()
    vad_cfg = cfg.get("vad", {})
    vad_mode = vad_cfg.get("mode", 2)
    max_silent_frames = vad_cfg.get("max_silent_frames", 20)
    max_total_frames = vad_cfg.get("max_total_frames", 300)
    
    vad = None
    if _has_webrtcvad:
        try:
            import webrtcvad
            vad = webrtcvad.Vad(vad_mode)
            print(f"[ALONE] webrtcvad initialized with mode {vad_mode}")
        except Exception as e:
            print(f"[ALONE] Failed to init webrtcvad: {e}. Falling back to energy VAD.")
            
    print("[ALONE] Listening for command...")
    
    frame_size = 480  # 30ms at 16kHz
    frames = []
    ring_buffer = [False] * 10
    speech_detected = False
    silent_frames = 0
    total_frames = 0
    
    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=frame_size) as stream:
            while total_frames < max_total_frames and _listening:
                if _paused:
                    time.sleep(0.01)
                    continue
                    
                audio_chunk, overflow = stream.read(frame_size)
                audio_data = audio_chunk.flatten()
                frames.append(audio_data.copy())
                total_frames += 1
                
                # Check speech flag
                is_speech = False
                if vad is not None:
                    try:
                        is_speech = vad.is_speech(audio_data.tobytes(), sample_rate)
                    except Exception:
                        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                        is_speech = rms >= energy_threshold
                else:
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                    is_speech = rms >= energy_threshold
                
                # Update ring buffer
                ring_buffer.pop(0)
                ring_buffer.append(is_speech)
                
                # Check for start
                if not speech_detected:
                    if sum(ring_buffer) >= 3:
                        speech_detected = True
                        print("[ALONE] Speech detected... 🎤")
                        try:
                            from ui.window import signals
                            signals.status_changed.emit("RECORDING")
                        except Exception:
                            pass
                else:
                    # Check for end
                    if not is_speech:
                        silent_frames += 1
                    else:
                        silent_frames = 0
                        
                    if silent_frames >= max_silent_frames:
                        print("[ALONE] Speech ended ✅")
                        break
                        
            if total_frames >= max_total_frames:
                print("[ALONE] Max time reached, processing...")
                
    except Exception as e:
        print(f"[ALONE] Error recording command: {e}")
        
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
        print(f"[ALONE] Failed to save command audio: {e}")
        return None

def start_listening(callback):
    """Starts/runs the background listening process."""
    global _listening
    _listening = True
    
    load_wakeword_model()
    calibrate_threshold()
    
    _listen_loop(callback)

def _listen_loop(callback):
    global _stream, _listening, _paused
    
    cfg = _load_config()
    ww_cfg = cfg.get("wake_word", {})
    threshold = ww_cfg.get("threshold", 0.5)
    chunk_len = ww_cfg.get("chunk_size", 1280)
    
    print("\n[*] ALONE: Continuous Listening active. Say wake word to activate.")
    
    try:
        while _listening:
            if not _paused:
                if _stream is None:
                    try:
                        time.sleep(0.4)
                        _stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_len)
                        _stream.start()
                        print("[ALONE] Mic stream started successfully")
                    except Exception as e:
                        print(f"[ALONE] Failed to start mic stream: {e}")
                        time.sleep(0.5)
                        continue
                
                try:
                    audio_chunk, overflow = _stream.read(chunk_len)
                    audio_data = audio_chunk.flatten()
                    
                    if oww_model:
                        prediction = oww_model.predict(audio_data)
                        if prediction:
                            prob = max(prediction.values()) if prediction.values() else 0.0
                            
                            # Print score if > 0.2
                            if prob > 0.2:
                                print(f"[ALONE] Wake word score: {prob:.4f}")
                                
                            if prob >= threshold:
                                print(f"\n[!] Wake word detected! Confidence: {prob:.2f}")
                                _play_beep()
                                
                                try:
                                    from ui.window import signals
                                    signals.status_changed.emit("LISTENING")
                                except Exception:
                                    pass
                                    
                                # Close the wake word input stream temporarily to allow command recording
                                _stream.stop()
                                _stream.close()
                                _stream = None
                                
                                audio_path = record_until_silence()
                                if audio_path:
                                    callback(audio_path)
                                    
                                oww_model.reset()
                                print(f"[*] ALONE: Awaiting wake word...")
                except Exception as ex:
                    print(f"[!] InputStream read error: {ex}")
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
