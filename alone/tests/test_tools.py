import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.system import open_app, open_file, run_shell, type_text, take_screenshot
from tools.browser import open_url
from tools.coder import write_code, run_code
from tools.files import read_file, write_file, list_files, delete_file
from tools.search import search_web

# MOCK open_app tool
@patch("platform.system", return_value="Windows")
@patch("os.path.exists", return_value=True)
@patch("os.startfile")
@patch("subprocess.Popen")
def test_open_app_win(mock_popen, mock_startfile, mock_exists, mock_system):
    # Test popular web aliases path
    res = open_app.run("github")
    assert "github" in res.lower() or "opened" in res.lower()
    
    # Test local executable startfile path
    res = open_app.run("notepad")
    assert "success" in res.lower() or "attempted" in res.lower()

# MOCK open_file tool
@patch("platform.system", return_value="Windows")
@patch("os.startfile")
def test_open_file(mock_startfile, mock_system):
    res = open_file.run("dummy_file.txt")
    assert "dummy_file.txt" in res
    mock_startfile.assert_called_once_with("dummy_file.txt")

# MOCK run_shell tool with security intent verification
@patch("tools.get_latest_query", return_value="run git status please")
@patch("subprocess.run")
def test_run_shell_with_intent(mock_run, mock_query):
    mock_result = MagicMock()
    mock_result.stdout = "Everything clean"
    mock_result.stderr = ""
    mock_run.return_value = mock_result
    
    res = run_shell.run("git status")
    assert "Everything clean" in res
    mock_run.assert_called_once()

@patch("tools.get_latest_query", return_value="what is the weather today?")
def test_run_shell_without_intent(mock_query):
    res = run_shell.run("rm -rf /")
    assert "Safety Refusal" in res

# MOCK type_text tool
@patch("pyautogui.write")
def test_type_text(mock_write):
    res = type_text.run("hello jarvis")
    assert "hello jarvis" in res
    mock_write.assert_called_once_with("hello jarvis", interval=0.1)

# MOCK take_screenshot tool
@patch("os.makedirs")
@patch("pyautogui.screenshot")
def test_take_screenshot(mock_screenshot, mock_makedirs):
    res = take_screenshot.run("test.png")
    assert "test.png" in res
    mock_screenshot.assert_called_once()

# MOCK open_url tool
@patch("webbrowser.open")
def test_open_url(mock_open):
    res = open_url.run("google.com")
    assert "google.com" in res
    mock_open.assert_called_once()

# MOCK coder tools
@patch("tools.coder._get_llm")
@patch("os.makedirs")
@patch("builtins.open", new_callable=MagicMock)
def test_write_code(mock_open, mock_makedirs, mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="print('hello')")
    mock_get_llm.return_value = mock_llm
    
    res = write_code.run("hello.py, print('hello')")
    assert "saved" in res.lower()

@patch("subprocess.run")
@patch("os.path.exists", return_value=True)
def test_run_code(mock_exists, mock_run):
    mock_res = MagicMock()
    mock_res.stdout = "hello execution"
    mock_res.stderr = ""
    mock_run.return_value = mock_res
    
    res = run_code.run("hello.py")
    assert "hello execution" in res

# MOCK file operations
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
def test_read_file(mock_open, mock_exists):
    mock_open.return_value.__enter__.return_value.read.return_value = "file content"
    res = read_file.run("dummy.txt")
    assert "file content" in res

@patch("builtins.open", new_callable=MagicMock)
def test_write_file(mock_open):
    res = write_file.run("dummy.txt, hello content")
    assert "successfully wrote" in res.lower()

@patch("os.path.exists", return_value=True)
@patch("os.listdir", return_value=["file1.txt", "file2.py"])
def test_list_files(mock_listdir, mock_exists):
    res = list_files.run("dummy_dir")
    assert "file1.txt" in res
    assert "file2.py" in res

@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_delete_file(mock_remove, mock_exists):
    res = delete_file.run("dummy.txt")
    assert "deleted" in res.lower()
    mock_remove.assert_called_once_with("dummy.txt")
