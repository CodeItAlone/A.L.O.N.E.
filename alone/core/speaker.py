import pyttsx3
import queue
import sys
import gc

_speech_queue = queue.Queue()

def speak(text):
    """Only call from MAIN thread"""
    from core.listener import pause_listening, resume_listening
    if sys.platform == "win32":
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
    try:
        pause_listening()        # stop mic FIRST
        print(f"ALONE: {text}")
        
        # Initialize locally for this speech
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)
        voices = engine.getProperty('voices')
        for voice in voices:
            if "david" in voice.name.lower() or \
               "zira" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
                
        engine.say(text)
        engine.runAndWait()
        
        # Force cleanup to release audio device locks
        del engine
        gc.collect()
    except Exception as e:
        print(f"[ALONE TTS ERROR] {e}")
    finally:
        resume_listening()       # always restart mic

def speak_async(text):
    """Safe to call from ANY thread — puts in queue"""
    if text:
        print(f"[DEBUG SPEAKER] Enqueuing: '{text[:40]}...'")
        _speech_queue.put(text)

def process_speech_queue():
    """
    MUST be called repeatedly from MAIN thread loop.
    Drains the queue and speaks each item.
    """
    from core.listener import pause_listening, resume_listening
    if sys.platform == "win32":
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
    try:
        while not _speech_queue.empty():
            text = _speech_queue.get_nowait()
            print(f"[DEBUG SPEAKER] Dequeuing: '{text[:40]}...'")
            pause_listening()    # stop mic FIRST
            print(f"ALONE: {text}")
            
            # Initialize locally for this speech
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.setProperty('volume', 1.0)
            voices = engine.getProperty('voices')
            for voice in voices:
                if "david" in voice.name.lower() or \
                   "zira" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
                    
            engine.say(text)
            engine.runAndWait()
            
            # Force cleanup to release audio device locks
            del engine
            gc.collect()
            
            resume_listening()   # restart mic after
    except queue.Empty:
        pass
    except Exception as e:
        print(f"[ALONE TTS QUEUE ERROR] {e}")
        resume_listening()       # safety net

def get_queue():
    return _speech_queue
