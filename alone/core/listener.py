import os
import time
import wave
import tempfile
import threading
import numpy as np
import sounddevice as sd
import yaml
import re
from openwakeword.model import Model

# Active listening globals
_last_interaction_time = 0.0
_active_window_duration = 15.0  # 15 seconds active listening window

def update_last_interaction_time():
    global _last_interaction_time
    _last_interaction_time = time.time()
    print(f"[DEBUG LOGGING] Active listening window updated. Expiry in {_active_window_duration} seconds.")

def get_last_interaction_time():
    return _last_interaction_time

def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Normalize whitespaces
    return " ".join(text.split())

def match_wake_word_fuzzy(normalized_text, threshold=0.75):
    """
    Checks if normalized_text starts with or contains a fuzzy match of target phrases.
    Targets: "hey alone", "ok alone".
    Do NOT trigger on standalone "alone".
    Returns (detected, matched_phrase, confidence, clean_command).
    """
    words = normalized_text.split()
    if not words:
        return False, "", 0.0, normalized_text
        
    best_sim = 0.0
    best_match_phrase = ""
    best_match_len = 0
    
    # Check "hey alone" and "ok alone" targets (2 words)
    targets = ["hey alone", "ok alone"]
    if len(words) >= 2:
        for i in range(len(words) - 1):
            phrase = words[i] + " " + words[i+1]
            for target in targets:
                dist = levenshtein_distance(phrase, target)
                sim = 1.0 - (dist / max(len(phrase), len(target)))
                if sim > best_sim:
                    best_sim = sim
                    best_match_phrase = phrase
                    best_match_len = 2
                    
    # Also support other manual phonetic triggers for high confidence (always 2 words)
    two_word_phonetic_triggers = [
        "hey aloon", "hey alon", "hey allon", "hey alloon", "hey allone", "hey loone", 
        "hay alone", "hay alon", "hay alloon", "hey salon", "hey along", "hey low", 
        "he alone", "he alon", "ok aloon", "ok alon", "ok allon", "ok alloon", 
        "ok allone", "ok loone", "okay alone", "okay alon", "okay alloon", "okay aloon"
    ]
    if len(words) >= 2:
        for i in range(len(words) - 1):
            phrase = words[i] + " " + words[i+1]
            if phrase in two_word_phonetic_triggers:
                sim = 0.98
                if sim > best_sim:
                    best_sim = sim
                    best_match_phrase = phrase
                    best_match_len = 2

    if best_sim >= threshold:
        clean_command = normalized_text
        if normalized_text.startswith(best_match_phrase):
            clean_command = normalized_text[len(best_match_phrase):].strip()
        else:
            idx = normalized_text.find(best_match_phrase)
            if idx != -1:
                clean_command = (normalized_text[:idx] + " " + normalized_text[idx + len(best_match_phrase):]).strip()
        return True, best_match_phrase, best_sim, clean_command
        
    return False, "", 0.0, normalized_text


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
        cfg = _load_config()
        wake_word = cfg.get("voice", {}).get("wake_word", "hey_alone")
        if wake_word == "hey_alone":
            print("[ALONE] Custom wake word 'hey_alone' requested but tflite model is missing. Falling back to VAD Speech-to-Text engine.")
            oww_model = None
        else:
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
        time.sleep(0.25)  # Warm-up delay to allow audio output to clear before starting input stream
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
                    if total_frames > 8:  # Ignore first 8 frames (240ms) to avoid stream init pops/clicks
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
                        is_within_active_window = (time.time() - _last_interaction_time <= _active_window_duration)
                        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                        
                        prediction = oww_model.predict(audio_data)
                        prob = max(prediction.values()) if prediction and prediction.values() else 0.0
                        
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
                                callback(audio_path, wake_word_detected=True)
                                
                            oww_model.reset()
                            print(f"[*] ALONE: Awaiting wake word...")
                        elif is_within_active_window and rms >= energy_threshold:
                            print(f"\n[Active Window] Speech detected (RMS: {rms:.1f}). Capturing direct command...")
                            _stream.stop()
                            _stream.close()
                            _stream = None
                            
                            audio_path = record_until_silence()
                            if audio_path:
                                from core.transcriber import transcribe
                                print("[Active Window] Transcribing captured slice...")
                                text = transcribe(audio_path)
                                normalized_text = normalize_text(text)
                                if normalized_text.strip() != "":
                                    _play_beep()
                                    try:
                                        from ui.window import signals
                                        signals.status_changed.emit("LISTENING")
                                    except Exception:
                                        pass
                                    callback(audio_path, active_window_bypass=True)
                                else:
                                    print("[Active Window] Empty speech detected.")
                                    if os.path.exists(audio_path):
                                        try:
                                            os.remove(audio_path)
                                        except Exception:
                                            pass
                            oww_model.reset()
                    else:
                        # VAD Speech-To-Text fallback for custom wake word "hey alone"
                        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                        if rms >= energy_threshold:
                            is_within_active_window = (time.time() - _last_interaction_time <= _active_window_duration)
                            
                            if is_within_active_window:
                                print(f"\n[VAD Fallback] Speech detected (RMS: {rms:.1f}) within ACTIVE WINDOW ({time.time() - _last_interaction_time:.1f}s elapsed).")
                            else:
                                print(f"\n[VAD Fallback] Speech detected (RMS: {rms:.1f}). Capturing potential command...")
                            
                            # Temporarily close stream for recording
                            _stream.stop()
                            _stream.close()
                            _stream = None
                            
                            audio_path = record_until_silence()
                            if audio_path:
                                from core.transcriber import transcribe
                                print("[VAD Fallback] Transcribing captured slice...")
                                text = transcribe(audio_path)
                                print(f"[DEBUG LOGGING] Raw Whisper transcription: '{text}'")
                                
                                normalized_text = normalize_text(text)
                                print(f"[DEBUG LOGGING] Normalized transcription: '{normalized_text}'")
                                
                                # Systematically check if the user spoke the wake word
                                detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalized_text)
                                print(f"[DEBUG LOGGING] Wake-word matching result: {'SUCCESS' if detected else 'FAILED'} (Matched Phrase: '{matched_phrase}', Confidence: {confidence:.2f})")
                                
                                if detected:
                                    # User spoke the wake word (either alone or as a one-shot command)
                                    _play_beep()
                                    try:
                                        from ui.window import signals
                                        signals.status_changed.emit("LISTENING")
                                    except Exception:
                                        pass
                                        
                                    is_only_wake_word = (clean_command == "")
                                    print(f"[DEBUG LOGGING] Command extraction result: '{clean_command}' (Is Only Wake Word: {is_only_wake_word})")
                                    
                                    if is_only_wake_word:
                                        print("[VAD Fallback] Wake word only. Recording actual command...")
                                        # Delete the wake-word audio file to save disk space
                                        if os.path.exists(audio_path):
                                            try:
                                                os.remove(audio_path)
                                            except Exception:
                                                pass
                                                
                                        cmd_audio_path = record_until_silence()
                                        if cmd_audio_path:
                                            callback(cmd_audio_path, wake_word_detected=True)
                                        else:
                                            print("[VAD Fallback] No command detected.")
                                            try:
                                                from ui.window import signals
                                                signals.status_changed.emit("IDLE")
                                            except Exception:
                                                pass
                                    else:
                                        print("[VAD Fallback] One-shot command detected.")
                                        callback(audio_path)
                                else:
                                    # Wake word was NOT detected in the transcription
                                    if is_within_active_window:
                                        # Accept direct command within the active window only if transcription has content
                                        if normalized_text.strip() != "":
                                            print("[VAD Fallback] Active window bypass active. SUCCESS: Direct command accepted!")
                                            _play_beep()
                                            try:
                                                from ui.window import signals
                                                signals.status_changed.emit("LISTENING")
                                            except Exception:
                                                pass
                                            callback(audio_path, active_window_bypass=True)
                                        else:
                                            print("[VAD Fallback] Empty speech detected in active window.")
                                            try:
                                                from ui.window import signals
                                                signals.status_changed.emit("IDLE")
                                            except Exception:
                                                pass
                                            if os.path.exists(audio_path):
                                                try:
                                                    os.remove(audio_path)
                                                except Exception:
                                                    pass
                                    else:
                                        # Outside active window and no wake word -> ignore
                                        print("[VAD Fallback] No wake word detected in speech.")
                                        try:
                                            from ui.window import signals
                                            signals.status_changed.emit("IDLE")
                                        except Exception:
                                            pass
                                        if os.path.exists(audio_path):
                                            try:
                                                os.remove(audio_path)
                                            except Exception:
                                                pass
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
