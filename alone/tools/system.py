import subprocess
import os
import platform
import pyautogui
from langchain.tools import tool

from .browser import sanitize_tool_input

@tool
def open_app(app_name: str) -> str:
    """Opens a local application or popular website securely, handling shortcuts and duplicate prevention."""
    system = platform.system()
    try:
        app_name = sanitize_tool_input(app_name)
        
        # Web Aliases Dictionary for Popular Websites to prevent duplicate opens
        web_aliases = {
            "github": "https://github.com",
            "google": "https://google.com",
            "youtube": "https://youtube.com",
            "gmail": "https://gmail.com",
            "wikipedia": "https://wikipedia.org",
            "stackoverflow": "https://stackoverflow.com",
            "stack overflow": "https://stackoverflow.com",
            "jio hotstar": "https://www.hotstar.com",
            "hotstar": "https://www.hotstar.com",
            "jiohotstar": "https://www.hotstar.com",
            "linkedin": "https://www.linkedin.com",
            "facebook": "https://www.facebook.com",
            "twitter": "https://twitter.com",
            "instagram": "https://www.instagram.com"
        }
        
        name_lower = app_name.lower().strip()
        if name_lower in web_aliases:
            from .browser import open_url
            return open_url.run(web_aliases[name_lower])
            
        if app_name.startswith("http") or any(ext in name_lower for ext in [".com", ".org", ".net", ".io", ".html"]):
            from .browser import open_url
            return open_url.run(app_name)
            
        # Desktop Shortcut Scanning on Windows for custom installed apps
        if system == "Windows":
            shortcut_path = None
            try:
                app_name_clean = name_lower.replace(" ", "").replace("_", "")
                search_dirs = []
                if "USERPROFILE" in os.environ:
                    search_dirs.append(os.path.join(os.environ["USERPROFILE"], "Desktop"))
                    search_dirs.append(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"))
                if os.path.exists("C:\\Users\\Public\\Desktop"):
                    search_dirs.append("C:\\Users\\Public\\Desktop")
                if os.path.exists("C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"):
                    search_dirs.append("C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs")
                    
                for directory in search_dirs:
                    if not os.path.exists(directory):
                        continue
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            if file.lower().endswith(".lnk"):
                                name_without_ext = os.path.splitext(file)[0].lower().replace(" ", "").replace("_", "")
                                if app_name_clean in name_without_ext or name_without_ext in app_name_clean:
                                    shortcut_path = os.path.join(root, file)
                                    break
                        if shortcut_path:
                            break
                    if shortcut_path:
                        break
            except Exception:
                pass
                
            if shortcut_path:
                os.startfile(shortcut_path)
                return f"Successfully opened local app shortcut: {os.path.basename(shortcut_path)}."
                
            # Default Windows App fallback
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
    """Runs a shell command and returns output (stdout + stderr). Requires explicit user execution intent."""
    try:
        command = command.strip("'\"")
        
        # Security Intent Verification
        from tools import get_latest_query
        query = get_latest_query().lower()
        
        # Explicit keywords indicating direct shell command intent
        safety_keywords = [
            "run", "exec", "cmd", "shell", "terminal", "command", "install", 
            "git", "pip", "python", "npm", "node", "list files", "delete", "remove", 
            "make", "mkdir", "create dir", "dir", "ls", "untracked", "status"
        ]
        
        has_intent = any(k in query for k in safety_keywords)
        
        if not has_intent:
            return (
                "Safety Refusal: Running shell commands is blocked because there was no explicit "
                "user intent detected in your query. If you want me to run this, please explicitly ask me "
                "to 'run' or 'execute' the command."
            )
            
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
