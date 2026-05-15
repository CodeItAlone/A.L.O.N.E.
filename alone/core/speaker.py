import pyttsx3
import threading
import random
import time

class Speaker:
    def __init__(self, rate=175, volume=1.0, voice_index=0):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)
        
        # Get available voices
        voices = self.engine.getProperty('voices')
        if voices:
            # Try to find a male voice or stick to index
            self.engine.setProperty('voice', voices[voice_index].id)
            
        self.confirmation_phrases = [
            "Certainly, Sir.", 
            "On it, Sir.", 
            "Right away, Sir.", 
            "Of course, Sir.", 
            "As you wish, Sir."
        ]
        
        self._is_speaking = False

    def speak(self, text, use_confirmation=False):
        """Synchronous speech"""
        if not text:
            return
            
        if use_confirmation:
            phrase = random.choice(self.confirmation_phrases)
            self._say(phrase)
            
        self._say(text)

    def _say(self, text):
        self._is_speaking = True
        self.engine.say(text)
        self.engine.runAndWait()
        self._is_speaking = False

    def speak_async(self, text, use_confirmation=False):
        """Asynchronous speech in a separate thread"""
        thread = threading.Thread(target=self.speak, args=(text, use_confirmation))
        thread.daemon = True
        thread.start()
        return thread

    def stop(self):
        """Attempts to stop the current speech"""
        try:
            self.engine.stop()
        except:
            pass

# Singleton instance
_speaker_instance = None

def get_speaker(config=None):
    global _speaker_instance
    if _speaker_instance is None:
        rate = config.get('voice', {}).get('rate', 175) if config else 175
        volume = config.get('voice', {}).get('volume', 1.0) if config else 1.0
        voice_index = config.get('voice', {}).get('voice_index', 0) if config else 0
        _speaker_instance = Speaker(rate, volume, voice_index)
    return _speaker_instance
