import sys
import os
import threading
import time
import yaml
from core.brain import Brain
from core.agent import run_agent
from core.listener import Listener
from core.transcriber import Transcriber
from core.speaker import get_speaker

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

class AloneApp:
    def __init__(self):
        self.config = load_config()
        self.brain = Brain()
        self.speaker = get_speaker(self.config)
        self.transcriber = Transcriber(
            model_size=self.config['whisper']['model_size'],
            device=self.config['whisper']['device']
        )
        self.listener = Listener()
        
        self.current_agent_thread = None
        self.interrupt_event = threading.Event()

    def start(self):
        print("\n" + "="*50)
        print("   A.L.O.N.E. PHASE 3: THE VOICE ONLINE")
        print("="*50 + "\n")
        
        self.speaker.speak("A.L.O.N.E. online. All systems operational. Good day, Sir.")
        
        # Start Voice Listener in background
        self.listener.start_listening(self.voice_callback)
        
        # Text Input Fallback Loop
        self.text_input_loop()

    def voice_callback(self, audio_path):
        """Called when audio is captured by the listener"""
        try:
            # 1. Transcribe
            print("[*] Transcribing...")
            text = self.transcriber.transcribe(audio_path)
            
            if not text:
                # Potentially silent or low confidence
                return

            print(f"Captured: '{text}'")
            
            # 2. Check for interrupts
            if any(word in text.lower() for word in ["stop", "cancel", "shut up", "enough"]):
                self.handle_interrupt()
                return

            # 3. Process Command
            self.process_command(text)
            
        except Exception as e:
            print(f"[!] Voice Pipeline Error: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def process_command(self, text):
        """Routes the command to the agent"""
        self.interrupt_event.clear()
        
        # Random confirmation
        self.speaker.speak("", use_confirmation=True)
        
        # Run agent in a separate thread to keep listener active
        def run():
            print(f"[*] Processing: {text}")
            response = run_agent(text, stop_event=self.interrupt_event)
            
            # Fallback to Brain if agent fails
            if not response or "I apologize, Sir, but my mechanical hands failed" in response:
                print("[*] Agent failed. Falling back to Brain...")
                response = self.brain.chat(text)
            
            if not self.interrupt_event.is_set():
                print(f"\nALONE: {response}\n")
                self.speaker.speak_async(response)
            else:
                print("[*] Agent response suppressed due to interrupt.")

        self.current_agent_thread = threading.Thread(target=run)
        self.current_agent_thread.daemon = True
        self.current_agent_thread.start()

    def handle_interrupt(self):
        """Stops current TTS and suppresses agent output"""
        print("\n[!] ALONE: Interrupt detected. Stopping task, Sir.")
        self.interrupt_event.set()
        self.speaker.stop()
        # Note: Truly killing a running tool process requires more complex 
        # process management, but this stops the interaction.
        self.speaker.speak("As you wish, Sir. Task cancelled.")

    def text_input_loop(self):
        """Fallback text input loop"""
        while True:
            try:
                user_input = input("You (Text): ").strip()
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit"]:
                    print("\nALONE: Awaiting your return, Sir. Goodbye.")
                    self.speaker.speak("Goodbye, Sir.")
                    self.listener.stop()
                    break
                
                if any(word in user_input.lower() for word in ["stop", "cancel"]):
                    self.handle_interrupt()
                    continue

                self.process_command(user_input)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nALONE: Complication encountered: {e}\n")

if __name__ == "__main__":
    app = AloneApp()
    app.start()
