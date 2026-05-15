import os
from langchain.tools import tool

@tool
def read_file(filepath: str) -> str:
    """Reads and returns file content."""
    try:
        filepath = filepath.strip("'\"")
        if not os.path.exists(filepath):
            return f"Error: File not found at {filepath}"
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(input_str: str) -> str:
    """Writes content to a file. Input should be 'filepath, content'."""
    try:
        if "," not in input_str:
            return "Error: Input must be in 'filepath, content' format."
        
        filepath, content = input_str.split(",", 1)
        filepath = filepath.strip().strip("'\"")
        
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def list_files(directory: str = ".") -> str:
    """Lists files in a directory."""
    try:
        directory = directory.strip("'\"")
        if not os.path.exists(directory):
            return f"Error: Directory not found: {directory}"
        files = os.listdir(directory)
        return f"Files in {directory}:\n" + "\n".join(files)
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def delete_file(filepath: str) -> str:
    """Deletes a file. Safety: This tool should be used with caution."""
    try:
        filepath = filepath.strip("'\"")
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"
        # For now, we perform the deletion. LangChain agents can be instructed to ask first.
        os.remove(filepath)
        return f"Successfully deleted {filepath}"
    except Exception as e:
        return f"Error deleting file: {e}"
