import pyttsx3
import queue
import sys
import gc
import threading
import time
import subprocess
from core.state import AssistantState, get_state, set_state

_speech_queue = queue.Queue()
_tts_thread = None
_tts_active = threading.Event()
_tts_process = None
_tts_process_lock = threading.Lock()

def speak(text):
    """Speak synchronously (blocks the caller until done)"""
    if not text:
        return
    speak_async(text)
    # Block caller until queue is empty and speech is finished
    while not _speech_queue.empty() or _tts_active.is_set():
        time.sleep(0.05)

def speak_async(text):
    """Safe to call from ANY thread — puts text into queue and ensures TTS thread is running"""
    if text:
        print(f"[DEBUG SPEAKER] Enqueuing: '{text[:40]}...'")
        _speech_queue.put(text)
        start_tts_thread()

def stop_tts():
    global _tts_process
    with _tts_process_lock:
        if _tts_process and _tts_process.poll() is None:
            print("[DEBUG SPEAKER] Terminating TTS process...")
            _tts_process.terminate()
            try:
                _tts_process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                _tts_process.kill()
            _tts_process = None

def clear_speech_queue():
    while not _speech_queue.empty():
        try:
            _speech_queue.get_nowait()
            _speech_queue.task_done()
        except queue.Empty:
            break

def start_tts_thread():
    global _tts_thread
    if _tts_thread is None or not _tts_thread.is_alive():
        _tts_thread = threading.Thread(target=_tts_worker, daemon=True, name="TTSWorker")
        _tts_active.clear()
        _tts_thread.start()

def _tts_worker():
    from ui.window import signals
    
    engine = None
    if sys.platform != "win32":
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.setProperty('volume', 1.0)
            voices = engine.getProperty('voices')
            for voice in voices:
                if "david" in voice.name.lower() or "zira" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
        except Exception as init_err:
            print(f"[TTSWorker] Failed to init pyttsx3 engine: {init_err}")
            
    print("[TTSWorker] Dedicated background TTS Thread started.")
    try:
        while True:
            try:
                # Retrieve next text from queue with a short timeout to check for shutdown
                text = _speech_queue.get(timeout=0.5)
            except queue.Empty:
                try:
                    import main
                    if main._shutdown_flag.is_set():
                        break
                except Exception:
                    pass
                continue
                
            _tts_active.set()
            print(f"[DEBUG SPEAKER] Dequeuing and speaking: '{text[:40]}...'")
            
            # Transition state to SPEAKING
            set_state(AssistantState.SPEAKING)
            print(f"ALONE: {text}")
            
            try:
                if sys.platform == "win32":
                    cmd = [
                        sys.executable,
                        "-c",
                        "import sys, pyttsx3\n"
                        "text = sys.argv[1]\n"
                        "engine = pyttsx3.init()\n"
                        "engine.setProperty('rate', 175)\n"
                        "voices = engine.getProperty('voices')\n"
                        "for voice in voices:\n"
                        "    if 'david' in voice.name.lower() or 'zira' in voice.name.lower():\n"
                        "        engine.setProperty('voice', voice.id)\n"
                        "        break\n"
                        "engine.say(text)\n"
                        "engine.runAndWait()\n",
                        text
                    ]
                    global _tts_process
                    with _tts_process_lock:
                        _tts_process = subprocess.Popen(cmd)
                    _tts_process.wait()
                    with _tts_process_lock:
                        _tts_process = None
                else:
                    if engine:
                        engine.say(text)
                        engine.runAndWait()
            except Exception as speak_err:
                print(f"[ALONE TTS WORKER ERROR] speak failed: {speak_err}")
                
            _tts_active.clear()
            
            # Transition state
            current_s = get_state()
            if current_s == AssistantState.SPEAKING:
                # Naturally finished speaking, transition to FOLLOW_UP
                set_state(AssistantState.FOLLOW_UP)
            
            # Log transition back depending on main agent active state if not follow up/listening
            current_s = get_state()
            if current_s not in (AssistantState.FOLLOW_UP, AssistantState.LISTENING, AssistantState.INTERRUPTED):
                try:
                    import main
                    if main._agent_active.is_set():
                        set_state(AssistantState.THINKING)
                    else:
                        set_state(AssistantState.IDLE)
                except Exception:
                    set_state(AssistantState.IDLE)
                    
        # Explicit cleanup on shutdown
        if engine:
            del engine
            gc.collect()
            
    except Exception as e:
        print(f"[TTSWorker CRITICAL ERROR] {e}")
    print("[TTSWorker] Dedicated background TTS Thread terminated.")

def process_speech_queue():
    """Legacy compatibility no-op method (handling transitioned to TTS background worker)"""
    pass

def get_queue():
    return _speech_queue
