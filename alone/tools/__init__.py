from .system import open_app, open_file, run_shell, type_text, take_screenshot
from .browser import open_url
from .coder import write_code, run_code
from .files import read_file, write_file, list_files, delete_file
from .search import search_web

# Group tools for easy access
ALL_TOOLS = [
    open_app, open_file, run_shell, type_text, take_screenshot,
    open_url,
    write_code, run_code,
    read_file, write_file, list_files, delete_file,
    search_web
]
