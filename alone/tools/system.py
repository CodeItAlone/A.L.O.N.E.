import subprocess
import os
import platform
import pyautogui
from langchain.tools import tool

from .browser import sanitize_tool_input

@tool
def open_app(app_name: str) -> str:
    """Opens an application using subprocess. Handle system-specific commands."""
    system = platform.system()
    try:
        app_name = sanitize_tool_input(app_name)
        if system == "Windows":
            # Try to start the process. For common apps, just use start.
            subprocess.Popen(["start", "", app_name], shell=True)
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
        else:  # Linux
            subprocess.Popen([app_name])
        return f"Attempted to open {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"


@tool
def open_file(file_path: str) -> str:
    """Opens a file using the system's default application."""
    try:
        file_path = file_path.strip("'\"")
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
        return f"Opened file: {file_path}"
    except Exception as e:
        return f"Error opening file {file_path}: {e}"

@tool
def run_shell(command: str) -> str:
    """Runs a shell command and returns output (stdout + stderr)."""
    try:
        command = command.strip("'\"")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Failed to run command: {e}"

@tool
def type_text(text: str) -> str:
    """Types text using pyautogui."""
    try:
        text = text.strip("'\"")
        pyautogui.write(text, interval=0.1)
        return f"Typed text: {text}"
    except Exception as e:
        return f"Failed to type text: {e}"

@tool
def take_screenshot(filename: str = "screenshot.png") -> str:
    """Saves a screenshot to alone/data/screenshots/."""
    try:
        filename = filename.strip("'\"")
        save_path = os.path.join("data", "screenshots", filename)
        # Ensure we are relative to the project root 'alone'
        # But if main.py is in 'alone', then 'data/screenshots' is correct.
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        pyautogui.screenshot(save_path)
        return f"Screenshot saved to {save_path}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"
