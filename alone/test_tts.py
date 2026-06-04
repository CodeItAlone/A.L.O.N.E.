import pyttsx3

print("[*] Initializing pyttsx3 engine...")
try:
    engine = pyttsx3.init()
    print("[+] Engine initialized successfully.")
    
    print("[*] Queuing speech: 'Testing voice output'...")
    engine.say("Testing voice output")
    
    print("[*] Calling runAndWait()...")
    engine.runAndWait()
    print("[+] runAndWait() finished successfully!")
except Exception as e:
    print(f"[!] Error occurred: {e}")
