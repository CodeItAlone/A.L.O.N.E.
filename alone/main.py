import sys
import os
import threading
import time
import signal
import yaml
import random
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    Updates GUI thread-safely via custom signals.
    """
    try:
        try:
            from ui.window import signals
            signals.status_changed.emit("THINKING")
        except Exception:
            pass

        text = transcribe(audio_path)
        if not text or text.strip() == "":
            speak_async("I didn't catch that, Sir.")
            try:
                from ui.window import signals
                signals.status_changed.emit("IDLE")
            except Exception:
                pass
            return
        
        print(f"You: {text}")
        
        # Clean wake word prefix if present (e.g. for VAD one-shot)
        clean_text = text.strip()
        wake_word_variants = ["hey alone", "hey_alone", "alone", "hay alone", "hey salon", "hey along", "hey high line", "hello alone", "hey a long", "hey low", "hey_jarvis", "hey jarvis"]
        for prefix in wake_word_variants:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):].strip(", ")
                break
                
        if not clean_text:
            try:
                from ui.window import signals
                signals.status_changed.emit("IDLE")
            except Exception:
                pass
            return
        
        # Update user bubble in GUI
        try:
            from ui.window import signals
            signals.user_command_received.emit(clean_text)
        except Exception:
            pass
        
        # Check quick commands first
        from core.agent import QUICK_COMMANDS
        key = clean_text.lower().strip().rstrip("?.!")
        if key not in QUICK_COMMANDS:
            # Only say "on it" for complex commands
            speak_async("On it, Sir.")
        
        # Check for cancel/stop keywords
        if clean_text.strip().lower() in ["stop", "cancel"]:
            speak_async("Understood, Sir. Cancelling.")
            return
        
        # Check for shutdown keywords
        if clean_text.strip().lower() in ["alone shutdown", 
                                           "alone exit",
                                           "goodbye alone",
                                           "alone end session",
                                           "end session"]:
            from core import memory
            summary = memory.get_session_summary()
            speak_output = "Ending session, Sir. "
            if "No memories" not in summary:
                speak_output += "Here is a recap of today's session:\n" + summary
            else:
                speak_output += "Goodbye, Sir."
            speak_async(speak_output)
            _shutdown_flag.set()
            return
        
        result = run_agent(clean_text)
        
        # Always speak the result
        if isinstance(result, dict):
            output = result.get("output", result.get("response", str(result)))
        else:
            output = str(result)
            
        if output:
            speak_async(output)
    except Exception as e:
        print(f"[ALONE AUDIO CALLBACK ERROR] {e}")
        try:
            from ui.window import signals
            signals.status_changed.emit("IDLE")
        except Exception:
            pass
    finally:
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

def text_input_loop():
    """
    Runs in background thread.
    Handles keyboard fallback input.
    """
    while not _shutdown_flag.is_set():
        try:
            user_input = input("You (text): ")
            if not user_input.strip():
                continue
                
            # Signal user text entered and start thinking
            try:
                from ui.window import signals
                signals.user_command_received.emit(user_input)
                signals.status_changed.emit("THINKING")
            except Exception:
                pass
                
            if user_input.lower() in ["exit", "quit", "alone end session", "end session"]:
                from core import memory
                summary = memory.get_session_summary()
                speak_output = "Ending session, Sir. "
                if "No memories" not in summary:
                    speak_output += "Here is a recap of today's session:\n" + summary
                else:
                    speak_output += "Goodbye, Sir."
                speak_async(speak_output)
                _shutdown_flag.set()
                break
                
            result = run_agent(user_input)
            response_text = ""
            if isinstance(result, dict):
                response_text = result.get("output", result.get("response", str(result)))
            elif isinstance(result, str):
                response_text = result
                
            if response_text:
                speak_async(response_text)
        except EOFError:
            break
        except Exception as e:
            print(f"[ALONE TEXT INPUT ERROR] {e}")

def shutdown(signum=None, frame=None):
    """
    Clean shutdown procedure.
    """
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True
    
    print("\n[ALONE] Shutdown requested. Finishing up, Sir...")
    _shutdown_flag.set()
    
    speak_async("Shutting down all systems. Goodbye, Sir.")
    
    drain_start = time.time()
    drain_timeout = 8
    
    print("[ALONE] Draining speech queue...")
    while not _speech_queue.empty():
        process_speech_queue()
        elapsed = time.time() - drain_start
        if elapsed > drain_timeout:
            print("[ALONE] Drain timeout. Forcing exit.")
            break
        time.sleep(0.1)
    
    try:
        from core.listener import stop_listening
        stop_listening()
    except Exception as e:
        print(f"[ALONE] Listener cleanup error: {e}")
        
    try:
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
    except Exception:
        pass
        
    print("[ALONE] Shutdown complete. All systems offline.")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

def main():
    # 1. Initialize PyQt5 Application on the Main Thread
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer
    from ui.window import AloneHUDWindow, signals
    from ui.settings import AloneSettingsWindow
    from core.preloader import prewarm, wait_until_ready
    
    # Fire prewarm immediately
    threading.Thread(
        target=prewarm,
        daemon=True,
        name="Prewarmer"
    ).start()
    
    app = QApplication(sys.argv)
    
    # 2. Build UI windows
    hud = AloneHUDWindow()
    hud.show_hud()
    
    settings_win = AloneSettingsWindow(hud)
    signals.open_settings.connect(settings_win.show)
    
    # Speak while warming — user knows it is starting
    speak("A.L.O.N.E. initializing. One moment please, Sir.")
    
    # Wait max 2 minutes for all models to load
    if wait_until_ready(timeout=120):
        speak("All systems online. Good day, Sir.")
    else:
        speak("Partially initialized. Some systems may be slow, Sir.")
    
    # 4. Bind the speech queue drain process to a main thread QTimer (avoids COM errors)
    def speech_timer_tick():
        if not get_queue().empty():
            try:
                signals.status_changed.emit("SPEAKING")
            except Exception:
                pass
            process_speech_queue()
            try:
                signals.status_changed.emit("IDLE")
            except Exception:
                pass
                
    timer = QTimer()
    timer.timeout.connect(speech_timer_tick)
    timer.start(100) # Check every 100ms
    
    # 5. Start background threads
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
    
    print("\n[ALONE] Headless HUD Listening. Say wake word or type.\n")
    
    # Run the GUI event loop
    exit_code = app.exec_()
    shutdown()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
