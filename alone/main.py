import threading
import time
import signal
import sys
import os
from core.speaker import speak, speak_async, process_speech_queue, get_queue
from core.listener import start_listening
from core.transcriber import transcribe
from core.agent import run_agent

_shutdown_flag = threading.Event()
_speech_queue = get_queue()
_shutting_down = False

def handle_audio(audio_path):
    """
    Called by listener — runs in background thread.
    NEVER calls speak() directly — uses speak_async().
    """
    try:
        text = transcribe(audio_path)
        if not text or text.strip() == "":
            speak_async("I didn't catch that, Sir.")
            return
        
        # Clean wake word prefix if present (e.g. for VAD one-shot)
        clean_text = text.strip()
        wake_word_variants = ["hey alone", "hey_alone", "alone", "hay alone", "hey salon", "hey along", "hey high line", "hello alone", "hey a long", "hey low"]
        for prefix in wake_word_variants:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):].strip(", ")
                break
                
        if not clean_text:
            return
            
        print(f"You (voice): {clean_text}")
        
        # Check for cancel/stop keywords
        if clean_text.strip().lower() in ["stop", "cancel"]:
            speak_async("Understood, Sir. Cancelling.")
            return
        
        # Check for shutdown keywords
        if clean_text.strip().lower() in ["alone shutdown", 
                                           "alone exit",
                                           "goodbye alone"]:
            speak_async("Goodbye, Sir.")
            _shutdown_flag.set()
            return
        
        result = run_agent(clean_text)
        speak_async(result)   # ✅ safe — background thread
    except Exception as e:
        print(f"[ALONE AUDIO CALLBACK ERROR] {e}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def text_input_loop():
    """
    Runs in background thread.
    Handles keyboard fallback input.
    Never blocks main thread.
    """
    while not _shutdown_flag.is_set():
        try:
            user_input = input("You (text): ")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit"]:
                _shutdown_flag.set()
                break
            result = run_agent(user_input)
            speak_async(result)  # ✅ safe — background
        except EOFError:
            break
        except Exception as e:
            print(f"[ALONE TEXT INPUT ERROR] {e}")

def shutdown(signum=None, frame=None):
    """
    Handles: Ctrl+C, SIGTERM, 'exit' command, 
    voice shutdown command, window close (Phase 5)
    """
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True
    
    print("\n[ALONE] Shutdown requested. "
          "Finishing up, Sir...")
    
    # Step 1: Stop accepting new commands
    _shutdown_flag.set()
    
    # Step 2: Queue the goodbye message
    speak_async("Shutting down all systems. "
                "Goodbye, Sir.")
    
    # Step 3: Drain the speech queue fully
    # Max 10 seconds — then force exit
    drain_start = time.time()
    drain_timeout = 10
    
    print("[ALONE] Draining speech queue...")
    while not _speech_queue.empty():
        process_speech_queue()
        elapsed = time.time() - drain_start
        if elapsed > drain_timeout:
            print("[ALONE] Drain timeout. "
                  "Forcing exit.")
            break
        time.sleep(0.1)
    
    # Step 4: Clean up audio resources
    try:
        from core.listener import stop_listening
        stop_listening()
    except Exception as e:
        print(f"[ALONE] Listener cleanup error: {e}")
    


    
    print("[ALONE] Shutdown complete. "
          "All systems offline.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

def main():
    # ✅ Main thread — speak() is safe here
    speak("A.L.O.N.E. online. All systems operational. Good day, Sir.")
    
    # Start background threads
    threading.Thread(
        target=start_listening,
        args=(handle_audio,),
        daemon=True,
        name="VoiceListener"
    ).start()
    
    threading.Thread(
        target=text_input_loop,
        daemon=True,
        name="TextInput"
    ).start()
    
    print("\n[ALONE] Listening. Say wake word or type.\n")
    
    # ✅ MAIN THREAD LOOP — only job is TTS queue
    ticks = 0
    while not _shutdown_flag.is_set():
        ticks += 1
        if ticks % 50 == 0:
            print(f"[DEBUG MAIN LOOP] Tick {ticks} - Queue size: {get_queue().qsize()}")
        process_speech_queue()
        time.sleep(0.1)
    
    # Shutdown sequence starts here
    shutdown()

if __name__ == "__main__":
    main()
