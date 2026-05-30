import os
import sys
# Add current dir to path
sys.path.append(os.getcwd())

from core.agent import run_agent

def run_test_command(command):
    print(f"\n[Testing Command]: {command}")
    try:
        response = run_agent(command)
        print(f"[ALONE]: {response}")
        return True
    except Exception as e:
        print(f"[Error]: {e}")
        return False

commands = [
    "Open Notepad",
    "Type Hello World",
    "Open Google Chrome",
    "Go to github.com",
    "List files in the current directory",
    "Write a Python hello world script named 'hello.py' and save it",
    "Run the script 'hello.py' you just wrote",
    "Take a screenshot named 'test_screenshot.png'",
    "Search the web for 'Python tutorials' and summarize",
    "Read the file 'config.yaml'"
]

if __name__ == "__main__":
    print("Starting 10 Command Challenge...")
    for cmd in commands:
        run_test_command(cmd)
    print("\nChallenge Complete.")
