import webbrowser
from langchain.tools import tool

@tool
def open_url(url: str) -> str:
    """Opens a URL in the default web browser."""
    try:
        url = url.strip("'\"")
        # Basic validation
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened URL: {url}"
    except Exception as e:
        return f"Failed to open URL {url}: {e}"
