import os
import sys
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
import yaml

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def _load_config(path="config.yaml"):
    if not os.path.exists(path):
        if os.path.exists("../config.yaml"):
            path = "../config.yaml"
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    config = _load_config()
    sample_rate = 16000
    chunk_len = 1280
    keyword = config.get('voice', {}).get('wake_word', "hey_alone")
    
    print(f"[*] Configured Wake Word: '{keyword}'")
    
    builtin_models = ["alexa", "hey_jarvis", "hey_mycroft", "hey_rhasspy", "timer", "weather"]
    norm_keyword = keyword.lower().replace("_", " ")
    is_builtin = any(b in norm_keyword for b in builtin_models)
    
    if is_builtin:
        print("[*] Initializing openWakeWord...")
        try:
            oww_model = Model(
                wakeword_models=[keyword],
                inference_framework="onnx"
            )
            print("[+] openWakeWord initialized successfully.")
        except Exception as e:
            print(f"[!] Init failed: {e}")
            return
    else:
        print("[*] Custom wake word detected. Initializing VAD Speech-To-Text wake word engine...")
        try:
            from core.transcriber import transcribe
            print("[+] VAD Speech-To-Text engine initialized successfully.")
        except Exception as e:
            print(f"[!] Init failed: {e}")
            return

    print("\n[*] Listing audio devices:")
    print(sd.query_devices())
    
    print(f"\n[*] Starting microphone stream for 15 seconds. Say '{keyword.replace('_', ' ')}' to test!")
    
    try:
        raw_stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_len)
        raw_stream.start()
        
        start_time = time.time()
        
        if is_builtin:
            while time.time() - start_time < 15:
                audio_chunk, overflow = raw_stream.read(chunk_len)
                audio_data = audio_chunk.flatten()
                
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                prediction = oww_model.predict(audio_data)
                prob = prediction.get(keyword, 0.0)
                
                if prob > 0.01 or rms > 10:
                    print(f"RMS: {rms:6.1f} | Wake Word Probability: {prob:.4f}")
                
                time.sleep(0.01)
        else:
            # Custom VAD continuous listening loop for testing
            energy_threshold = 200.0
            print("[*] Listening for speech spikes...")
            
            while time.time() - start_time < 15:
                audio_chunk, overflow = raw_stream.read(chunk_len)
                audio_data = audio_chunk.flatten()
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                
                if rms >= energy_threshold:
                    print(f"\n[VAD] Speech onset detected (RMS: {rms:.1f}). Recording 2.5 seconds...")
                    frames = [audio_data.copy()]
                    
                    # Record for 2.5 seconds to capture the wake word
                    rec_start = time.time()
                    while time.time() - rec_start < 2.5:
                        audio_chunk, overflow = raw_stream.read(chunk_len)
                        frames.append(audio_chunk.flatten().copy())
                    
                    import tempfile
                    import wave
                    temp_path = os.path.join(tempfile.gettempdir(), f"test_wakeword_{int(time.time())}.wav")
                    with wave.open(temp_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(sample_rate)
                        wf.writeframes(np.concatenate(frames).tobytes())
                        
                    print("[VAD] Transcribing recorded slice...")
                    text = transcribe(temp_path)
                    print(f"[VAD] Transcribed: '{text}'")
                    
                    # Clean up file
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                    
                    cleaned_text = text.lower().strip(".,?! ")
                    wake_word_variants = ["hey alone", "hey_alone", "alone", "hay alone", "hey salon", "hey along", "hey high line", "hello alone", "hey a long", "hey low"]
                    
                    detected = False
                    for variant in wake_word_variants:
                        if cleaned_text.startswith(variant) or f" {variant}" in cleaned_text:
                            detected = True
                            print(f"[!] SUCCESS: Wake word '{variant}' detected!")
                            break
                    if not detected:
                        print("[*] No wake word detected in this speech slice.")
                        
                time.sleep(0.01)
            
        raw_stream.stop()
        raw_stream.close()
        print("[*] Test complete.")
    except Exception as e:
        print(f"[!] Stream error: {e}")

if __name__ == "__main__":
    main()
