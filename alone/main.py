import sys
from core.brain import Brain

def main():
    try:
        # Initialize the Brain
        brain = Brain()
        
        print("\nA.L.O.N.E. online. Good day, Sir.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit"]:
                    print("\nALONE: Awaiting your return, Sir. Goodbye.")
                    break
                
                response = brain.chat(user_input)
                print(f"\nALONE: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nALONE: Abrupt departure, Sir? Very well. Goodbye.")
                break
            except Exception as e:
                print(f"\nALONE: I seem to have encountered a slight complication: {e}\n")

    except Exception as e:
        print(f"Failed to initialize ALONE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
