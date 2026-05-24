import os
import sys
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

def main():
    sample_rate = 16000
    chunk_len = 1280
    keyword = "hey_jarvis"
    
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

    print("\n[*] Listing audio devices:")
    print(sd.query_devices())
    
    print("\n[*] Starting microphone stream for 10 seconds. Say 'hey jarvis' to test!")
    
    try:
        raw_stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=chunk_len)
        raw_stream.start()
        
        start_time = time.time()
        while time.time() - start_time < 10:
            audio_chunk, overflow = raw_stream.read(chunk_len)
            audio_data = audio_chunk.flatten()
            
            # Print average energy (RMS)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # Predict
            prediction = oww_model.predict(audio_data)
            prob = prediction.get(keyword, 0.0)
            
            if prob > 0.01 or rms > 10:
                print(f"RMS: {rms:6.1f} | Wake Word Probability: {prob:.4f}")
            
            time.sleep(0.01)
            
        raw_stream.stop()
        raw_stream.close()
        print("[*] Test complete.")
    except Exception as e:
        print(f"[!] Stream error: {e}")

if __name__ == "__main__":
    main()
