"""
Run this script ONCE manually to train your 
custom 'hey alone' wake word.
It will record 10 samples of your voice.
"""
import os

# Ensure the output directory exists
os.makedirs("data", exist_ok=True)

try:
    from openwakeword.train import train_model
except ImportError:
    print("[Error] openwakeword.train could not be imported. Please ensure openwakeword is fully installed.")
    exit(1)

print("[*] Starting custom wake word training for 'hey alone'...")
print("[*] Prepare to record 10 samples of your voice saying 'hey alone' when prompted.")

try:
    train_model(
        target_phrase="hey alone",
        output_path="data/hey_alone.tflite",
        num_samples=10
    )
    print("Wake word trained successfully!")
    print("File saved: data/hey_alone.tflite")
except Exception as e:
    print(f"[!] Custom training failed: {e}")
