from .system import open_app, open_file, run_shell, type_text, take_screenshot
from .browser import open_url
from .coder import write_code, run_code
from .files import read_file, write_file, list_files, delete_file
from .search import search_web
from .human_memory import search_human_memory, manage_goals, manage_projects, manage_contacts

# State to track the latest user query for security boundary validation
_latest_query = ""

def set_latest_query(query: str):
    global _latest_query
    _latest_query = query

def get_latest_query() -> str:
    return _latest_query

# Group tools for easy access
ALL_TOOLS = [
    open_app, open_file, run_shell, type_text, take_screenshot,
    open_url,
    write_code, run_code,
    read_file, write_file, list_files, delete_file,
    search_web,
    search_human_memory, manage_goals, manage_projects, manage_contacts
]
