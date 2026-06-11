import sys
import os
import threading
import time
import signal
import yaml
import random
from datetime import datetime

# Automatic redirection for headless running
if sys.executable.lower().endswith("pythonw.exe") or sys.stdout is None:
    try:
        _log_dir = os.path.expanduser("~/.alone")
        os.makedirs(_log_dir, exist_ok=True)
        _log_file = open(os.path.join(_log_dir, "alone.log"), "a", encoding="utf-8", buffering=1)
        sys.stdout = _log_file
        sys.stderr = _log_file
        print(f"\n--- ALONE Headless Log Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    except Exception:
        pass


# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.speaker import speak, speak_async, process_speech_queue, get_queue
from core.listener import start_listening
from core.transcriber import transcribe
from core.agent import run_agent

_shutdown_flag = threading.Event()
_speech_queue = get_queue()
_shutting_down = False
_agent_active = threading.Event()
_last_command = ""
_last_response = ""

def handle_audio(audio_path, wake_word_detected=False, active_window_bypass=False):
    """
    Called by listener — runs in background thread.
    Updates GUI thread-safely via custom signals.
    """
    try:
        print(f"[PIPELINE DIAGNOSTIC] Raw audio file received: {audio_path}")
        try:
            from ui.window import signals
            signals.status_changed.emit("THINKING")
        except Exception:
            pass

        text = transcribe(audio_path)
        print(f"[PIPELINE DIAGNOSTIC] Whisper transcription: \"{text}\"")
        if not text or text.strip() == "":
            speak_async("I didn't catch that, Sir.")
            try:
                from ui.window import signals
                signals.status_changed.emit("IDLE")
            except Exception:
                pass
            return
        
        # ----------------------------------------------------
        # NEW ROBUST NORMALIZATION & FUZZY MATCHING STRIPPING
        # ----------------------------------------------------
        from core.listener import normalize_text, match_wake_word_fuzzy, update_last_interaction_time, get_last_interaction_time, _active_window_duration
        
        print(f"[DEBUG LOGGING] Raw Whisper transcription: '{text}'")
        normalized_text = normalize_text(text)
        print(f"[DEBUG LOGGING] Normalized transcription: '{normalized_text}'")
        
        # Check active window bypass
        import time
        is_active_window = active_window_bypass or (time.time() - get_last_interaction_time() <= _active_window_duration)
        print(f"[PIPELINE DIAGNOSTIC] Listening window check: is_active_window={is_active_window}")
        
        if wake_word_detected:
            detected = True
            matched_phrase = "PRE-DETECTED"
            confidence = 1.0
            clean_command = normalized_text
            print("[DEBUG LOGGING] Wake-word pre-detected by listener. Bypassing wake-word extraction.")
        else:
            detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalized_text)
            print(f"[DEBUG LOGGING] Wake-word matching result: {'SUCCESS' if detected else 'FAILED'} (Matched Phrase: '{matched_phrase}', Confidence: {confidence:.2f})")
        
        print(f"[PIPELINE DIAGNOSTIC] Fuzzy wake-word check: detected={detected}, matched={matched_phrase}, sim={confidence:.2f}")
        
        global _last_command, _last_response
        if is_active_window:
            print(f"[DEBUG LOGGING] Active listening window active ({time.time() - get_last_interaction_time():.1f}s elapsed). Bypassing wake-word check.")
            # If wake word was spoken, clean it; otherwise use full normalized text as command
            if detected:
                clean_text = clean_command
            else:
                clean_text = normalized_text
                
            # Perform follow-up safety checks
            if not detected:
                from core.safety import FollowUpValidationService
                is_valid, score = FollowUpValidationService.validate_follow_up(
                    clean_text, _last_command, _last_response, is_active_window=True
                )
                if not is_valid:
                    speak_async("I may have heard background speech. Please repeat the command.")
                    try:
                        from ui.window import signals
                        signals.status_changed.emit("IDLE")
                    except Exception:
                        pass
                    return
        else:
            if detected:
                clean_text = clean_command
            else:
                print("[DEBUG LOGGING] Outside active window and no wake word detected. Discarding.")
                clean_text = ""
                
        print(f"[DEBUG LOGGING] Command extraction result: '{clean_text}'")
        print(f"[PIPELINE DIAGNOSTIC] Command extraction result: \"{clean_text}\"")
        # ----------------------------------------------------
                
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
        
        _agent_active.set()
        try:
            print(f"[DEBUG LOGGING] Intent routing starting for command: '{clean_text}'")
            result = run_agent(clean_text)
            
            # Always speak the result
            if isinstance(result, dict):
                output = result.get("output", result.get("response", str(result)))
            else:
                output = str(result)
                
            print(f"[DEBUG LOGGING] Intent routing & Action execution result: '{output}'")
            
            # Update history for safety context relevance
            _last_command = clean_text
            _last_response = output
            
            # Update active window timer on successful command execution
            update_last_interaction_time()
            
            if output:
                try:
                    from ui.window import signals
                    signals.response_received.emit(output)
                except Exception:
                    pass
                speak_async(output)
        finally:
            _agent_active.clear()
    except Exception as e:
        import traceback
        print(f"[ALONE AUDIO CALLBACK ERROR] {e}")
        traceback.print_exc()
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
    if sys.stdin is None or not sys.stdin.isatty():
        print("[ALONE] sys.stdin is not a TTY or is None. TextInput background thread disabled.")
        return
        
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
                
            _agent_active.set()
            try:
                result = run_agent(user_input)
                response_text = ""
                if isinstance(result, dict):
                    response_text = result.get("output", result.get("response", str(result)))
                elif isinstance(result, str):
                    response_text = result
                    
                # Update active window timer on successful command execution
                from core.listener import update_last_interaction_time
                update_last_interaction_time()
                
                if response_text:
                    try:
                        from ui.window import signals
                        signals.response_received.emit(response_text)
                    except Exception:
                        pass
                    speak_async(response_text)
            finally:
                _agent_active.clear()
        except (EOFError, OSError):
            break
        except Exception as e:
            print(f"[ALONE TEXT INPUT ERROR] {e}")
            break

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
