import subprocess
import os
import platform
import shutil
import json
import pyautogui
from langchain.tools import tool

from .browser import sanitize_tool_input

CACHE_PATH = os.path.expanduser("~/.alone/app_cache.json")

# Hardcoded APP_MAP with placeholders for dynamically replaced username
APP_MAP = {
    "vscode": r"C:\Users\{user}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "spotify": r"C:\Users\{user}\AppData\Local\Microsoft\WindowsApps\Spotify.exe",
    "discord": r"C:\Users\{user}\AppData\Local\Discord\Update.exe",
    "notepad": r"C:\Windows\System32\notepad.exe"
}

def _scan_registry():
    apps = {}
    if platform.system() != "Windows":
        return apps
    try:
        import winreg
    except ImportError:
        return apps

    # 1. App Paths registry query (best for executable paths)
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
    ]
    for hkey, subkey in keys:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, name) as subkey_item:
                            try:
                                val, _ = winreg.QueryValueEx(subkey_item, "")
                                if val and os.path.exists(val):
                                    app_name = os.path.splitext(name)[0].lower()
                                    apps[app_name] = val
                            except OSError:
                                pass
                    except OSError:
                        pass
        except Exception:
            pass
            
    # 2. Uninstall registry query (great for finding install folders)
    paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    for hkey, subkey in paths:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, name) as subkey_item:
                            try:
                                disp, _ = winreg.QueryValueEx(subkey_item, "DisplayName")
                                loc, _ = winreg.QueryValueEx(subkey_item, "InstallLocation")
                                if loc and os.path.isdir(loc):
                                    # Shallow search for executables in install folder
                                    for file in os.listdir(loc):
                                        if file.lower().endswith(".exe") and "uninstall" not in file.lower():
                                            apps[disp.lower()] = os.path.join(loc, file)
                                            apps[os.path.splitext(file)[0].lower()] = os.path.join(loc, file)
                            except OSError:
                                pass
                    except OSError:
                        pass
        except Exception:
            pass
    return apps

def _scan_standard_dirs():
    apps = {}
    user = os.environ.get("USERNAME") or "User"
    dirs = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        rf"C:\Users\{user}\AppData\Local\Programs",
        rf"C:\Users\{user}\AppData\Local",
        rf"C:\Users\{user}\AppData\Roaming"
    ]
    
    # Fast shallow walk of these directories (depth 1 and 2 to be instant)
    for d in dirs:
        if not os.path.exists(d):
            continue
        try:
            for entry in os.scandir(d):
                try:
                    if entry.is_dir():
                        # Check contents of the subfolder (depth 1)
                        for sub_entry in os.scandir(entry.path):
                            if sub_entry.is_file() and sub_entry.name.lower().endswith(".exe"):
                                if "uninstall" not in sub_entry.name.lower():
                                    apps[os.path.splitext(sub_entry.name)[0].lower()] = sub_entry.path
                            elif sub_entry.is_dir():
                                # Depth 2 search
                                try:
                                    for sub_sub in os.scandir(sub_entry.path):
                                        if sub_sub.is_file() and sub_sub.name.lower().endswith(".exe"):
                                            if "uninstall" not in sub_sub.name.lower():
                                                apps[os.path.splitext(sub_sub.name)[0].lower()] = sub_sub.path
                                except OSError:
                                    pass
                    elif entry.is_file() and entry.name.lower().endswith(".exe"):
                        if "uninstall" not in entry.name.lower():
                            apps[os.path.splitext(entry.name)[0].lower()] = entry.path
                except OSError:
                    pass
        except Exception:
            pass
    return apps

def _scan_desktop_shortcuts():
    apps = {}
    shortcut_paths = []
    if "USERPROFILE" in os.environ:
        shortcut_paths.append(os.path.join(os.environ["USERPROFILE"], "Desktop"))
        shortcut_paths.append(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"))
    if os.path.exists("C:\\Users\\Public\\Desktop"):
        shortcut_paths.append("C:\\Users\\Public\\Desktop")
    if os.path.exists("C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"):
        shortcut_paths.append("C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs")
        
    for d in shortcut_paths:
        if not os.path.exists(d):
            continue
        try:
            for root, dirs, files in os.walk(d):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        name_without_ext = os.path.splitext(file)[0].lower().strip()
                        apps[name_without_ext] = os.path.join(root, file)
        except Exception:
            pass
    return apps

def build_app_map():
    """
    Scans standard directories + registry ONCE.
    Saves result to ~/.alone/app_cache.json.
    On future launches loads from cache instantly.
    """
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
            
    app_map = {}
    
    # 1. Start with hardcoded map values
    user = os.environ.get("USERNAME") or "User"
    for k, v in APP_MAP.items():
        resolved_path = v.replace("{user}", user)
        if os.path.exists(resolved_path):
            app_map[k] = resolved_path
            
    # 2. Add registry scanned apps
    app_map.update(_scan_registry())
    
    # 3. Add standard folders scanned apps
    app_map.update(_scan_standard_dirs())
    
    # 4. Add desktop and start menu shortcuts
    app_map.update(_scan_desktop_shortcuts())
    
    # Ensure folder exists
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w") as f:
            json.dump(app_map, f, indent=2)
    except Exception as e:
        print(f"[Warning] Failed to cache app map: {e}")
        
    return app_map

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
            
        # Desktop / App opening logic
        user = os.environ.get("USERNAME") or "User"
        
        # 1. Hardcoded APP_MAP
        resolved_app_map = {}
        for k, v in APP_MAP.items():
            resolved_app_map[k] = v.replace("{user}", user)
            
        # Try hardcoded app map first
        if name_lower in resolved_app_map:
            path = resolved_app_map[name_lower]
            if os.path.exists(path):
                if system == "Windows":
                    os.startfile(path)
                else:
                    subprocess.Popen([path])
                return f"Successfully opened {app_name} from primary mapping."
                
        # 2. Fallback to shutil.which()
        which_path = shutil.which(app_name)
        if which_path:
            if system == "Windows":
                os.startfile(which_path)
            else:
                subprocess.Popen([which_path])
            return f"Successfully opened {app_name} via system PATH."
            
        # 3. Fallback to common install paths search (scanned app map)
        if system == "Windows":
            scanned_apps = build_app_map()
            # Try to match app name in scanned list
            matched_path = None
            
            # Exact match
            if name_lower in scanned_apps:
                matched_path = scanned_apps[name_lower]
            else:
                # Fuzzy match / Substring match
                app_name_clean = name_lower.replace(" ", "").replace("_", "")
                for key, val in scanned_apps.items():
                    key_clean = key.replace(" ", "").replace("_", "")
                    if app_name_clean in key_clean or key_clean in app_name_clean:
                        matched_path = val
                        break
            
            if matched_path and os.path.exists(matched_path):
                os.startfile(matched_path)
                return f"Successfully opened {app_name} from scanned applications: {os.path.basename(matched_path)}."
                
        # 4. Final Fallback: subprocess start with shell=True
        if system == "Windows":
            subprocess.Popen(["start", "", app_name], shell=True)
            return f"Attempted final fallback shell start for {app_name}."
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
            return f"Attempted final fallback open for {app_name}."
        else:
            subprocess.Popen([app_name])
            return f"Attempted final fallback exec for {app_name}."
            
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
