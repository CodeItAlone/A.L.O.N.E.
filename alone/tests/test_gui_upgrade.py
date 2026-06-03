import os
import sys
import json
import time
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer

# Initialize QApplication singleton if it doesn't exist
app = QApplication.instance()
if not app:
    app = QApplication([])

from ui.window import HUDConfirmDialog, LiveLogPanel, HistoryPanel, AloneHUDWindow, signals

def test_hud_confirm_dialog():
    dialog = HUDConfirmDialog(title="TEST TITLE", message="Test Message, Sir?")
    assert dialog.title_label.text() == "TEST TITLE"
    assert dialog.msg_label.text() == "Test Message, Sir?"
    assert dialog.windowFlags() & Qt.FramelessWindowHint

def test_live_log_panel():
    panel = LiveLogPanel()
    assert panel.title_label.text() == "LIVE LOG"
    assert panel.list_widget.count() == 0
    
    # Enqueue message
    panel.enqueue_log("Testing live log entry", "info")
    assert len(panel.log_queue) == 1
    
    # Force batch processing
    panel.process_log_queue()
    assert len(panel.log_queue) == 0
    assert panel.list_widget.count() == 1
    assert "Testing live log entry" in panel.list_widget.item(0).text()

def test_live_log_fifo_eviction():
    panel = LiveLogPanel()
    # Add 210 logs
    for i in range(210):
        panel.enqueue_log(f"Log {i}")
    panel.process_log_queue()
    
    # Verify count is capped at 200
    assert panel.list_widget.count() == 200
    # First item should be Log 10 (since Log 0-9 got evicted)
    assert "Log 10" in panel.list_widget.item(0).text()

def test_history_panel_command_completed():
    panel = HistoryPanel()
    # Clear current history in memory
    panel.history_data.clear()
    panel.list_widget.clear()
    
    # Simulate a command completed signal
    signals.command_completed.emit("12:00:00", "Play music", "Spotify opened")
    
    # Yield control to allow Qt events to process
    QApplication.processEvents()
    
    assert len(panel.history_data) == 1
    assert panel.history_data[0]["command"] == "Play music"
    assert panel.history_data[0]["outcome"] == "Spotify opened"
    assert panel.list_widget.count() == 1
    assert "Play music" in panel.list_widget.item(0).text()

def test_history_retention_and_persistence():
    panel = HistoryPanel()
    panel.history_data.clear()
    
    # Add dummy entries
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    old_date = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
    
    panel.history_data.append({"timestamp": "10:00:00", "command": "cmd1", "outcome": "ok", "date": today})
    panel.history_data.append({"timestamp": "09:00:00", "command": "cmd2", "outcome": "ok", "date": old_date})
    
    # Trigger save and then load
    panel.save_history_async()
    time.sleep(0.2) # Allow thread to complete write
    
    loaded = panel.load_history()
    
    # cmd2 should be filtered out (older than 7 days)
    assert len(loaded) == 1
    assert loaded[0]["command"] == "cmd1"

def test_alone_hud_window_integration():
    hud = AloneHUDWindow()
    assert hud.log_panel is not None
    assert hud.history_panel is not None
    
    # Ensure log panel is not minimized initially so toggling will reduce height
    if hud.log_panel.is_minimized:
        hud.log_panel.toggle_minimized()
        
    # Verify resize adjust height matches bounds
    h_initial = hud.minimumHeight()
    
    # Toggle minimize log panel and adjust
    hud.log_panel.toggle_minimized()
    h_min = hud.minimumHeight()
    assert h_min < h_initial

def test_stop_button_integration():
    from PyQt5.QtWidgets import QDialog
    hud = AloneHUDWindow()
    # Verify stop button is instantiated
    assert hud.stop_btn is not None
    assert hud.stop_btn.text() == "STOP AGENT"
    assert hud.stop_btn.height() == 35
    
    # Mock confirm dialog and quit_app
    with patch('ui.window.HUDConfirmDialog') as mock_dialog_cls, \
         patch.object(hud, 'quit_app') as mock_quit_app, \
         patch.object(hud, 'hide') as mock_hide, \
         patch.object(hud.tray_icon, 'hide') as mock_tray_hide, \
         patch('PyQt5.QtWidgets.QApplication.processEvents') as mock_process_events:
         
        # Simulate cancellation
        mock_dialog_inst = MagicMock()
        mock_dialog_inst.exec_.return_value = QDialog.Rejected
        mock_dialog_cls.return_value = mock_dialog_inst
        
        hud.stop_btn.click()
        
        mock_hide.assert_not_called()
        mock_quit_app.assert_not_called()
        
        # Simulate confirmation
        mock_dialog_inst.exec_.return_value = QDialog.Accepted
        hud.stop_btn.click()
        
        mock_hide.assert_called_once()
        mock_tray_hide.assert_called_once()
        mock_process_events.assert_called_once()
        mock_quit_app.assert_called_once()

