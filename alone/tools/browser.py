import webbrowser
import time
from langchain.tools import tool

# Track recently opened URLs to prevent duplicate opens from LLM loops (10-second window)
_opened_urls = {}

def sanitize_tool_input(input_str: str) -> str:
    # Strip basic characters
    s = input_str.strip("'\"\t\n ")
    
    # Check for common LLM hallucinated transitions and truncate
    for keyword in ["Opened", "Observation:", "Thought:", "Final Answer:", "Sir,", "Since you've"]:
        idx = s.lower().find(keyword.lower())
        if idx != -1:
            s = s[:idx].strip()
            
    # Handle newlines - tool inputs are single-line
    if "\n" in s:
        s = s.split("\n")[0].strip()
        
    return s

@tool
def open_url(url: str) -> str:
    """Opens a URL in the default web browser."""
    global _opened_urls
    try:
        url = sanitize_tool_input(url)
        
        # Basic validation
        if not url.startswith("http"):
            url = "https://" + url
            
        current_time = time.time()
        # Check if already opened within the last 10 seconds to prevent duplicates
        if url in _opened_urls and (current_time - _opened_urls[url] < 10):
            return f"Opened URL: {url} (already opened in this loop)"
            
        # Update timestamp
        _opened_urls[url] = current_time
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Failed to open URL {url}: {e}"

