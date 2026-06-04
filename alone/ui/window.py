import sys
import os
import math
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint, QSettings
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QFont
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QHBoxLayout, QSystemTrayIcon, QMenu, QAction,
                             QPushButton, QScrollArea, QListWidget, QListWidgetItem,
                             QDialog)


class AloneSignals(QObject):
    # Thread-safe signals to communicate with the GUI
    status_changed = pyqtSignal(str)          # 'IDLE', 'LISTENING', 'THINKING', 'SPEAKING'
    amplitude_received = pyqtSignal(float)     # Mic RMS value for waveform animation
    user_command_received = pyqtSignal(str)   # Display user's command
    response_received = pyqtSignal(str)       # Display ALONE's response
    open_settings = pyqtSignal()              # Trigger settings window open
    
    # New thread-safe signals for live log and history
    log_message = pyqtSignal(str, str)        # log_text, category ('info', 'command', 'action', 'error', 'stall')
    command_completed = pyqtSignal(str, str, str) # timestamp, command, outcome

# Singleton instance for global signal access
signals = AloneSignals()

# Transparent runtime monkey-patching of the backend callbacks and agent pipelines
def setup_runtime_hooks():
    try:
        from core.agent import AloneCallbackHandler
        
        orig_on_tool_start = AloneCallbackHandler.on_tool_start
        orig_on_tool_end = AloneCallbackHandler.on_tool_end
        orig_on_tool_error = AloneCallbackHandler.on_tool_error
        
        def patched_on_tool_start(self, serialized: dict, input_str: str, **kwargs):
            try:
                tool_name = serialized.get("name", "unknown_tool")
                signals.log_message.emit(f"Action: Launching application \"{tool_name}\"" if tool_name == "open_app" else f"Action: Executing tool \"{tool_name}\"", "action")
            except Exception:
                pass
            try:
                return orig_on_tool_start(self, serialized, input_str, **kwargs)
            except Exception as e:
                raise e
                
        def patched_on_tool_end(self, output: str, *, run_id, parent_run_id=None, **kwargs):
            try:
                tool_name = kwargs.get("name", "unknown_tool")
                # Format a user-friendly log entry for tool execution
                clean_output = str(output).strip()
                if len(clean_output) > 80:
                    clean_output = clean_output[:77] + "..."
                signals.log_message.emit(f"Action outcome: '{tool_name}' finished -> {clean_output}", "action")
            except Exception:
                pass
            try:
                return orig_on_tool_end(self, output, run_id=run_id, parent_run_id=parent_run_id, **kwargs)
            except Exception as e:
                raise e
                
        def patched_on_tool_error(self, error: BaseException, **kwargs):
            try:
                tool_name = kwargs.get("name", "unknown_tool")
                signals.log_message.emit(f"Exception: Tool '{tool_name}' failed -> {str(error)}", "error")
            except Exception:
                pass
            try:
                return orig_on_tool_error(self, error, **kwargs)
            except Exception as e:
                raise e
                
        AloneCallbackHandler.on_tool_start = patched_on_tool_start
        AloneCallbackHandler.on_tool_end = patched_on_tool_end
        AloneCallbackHandler.on_tool_error = patched_on_tool_error
    except Exception as e:
        print(f"[ALONE GUI HOOKS] Failed to wrap AloneCallbackHandler: {e}")
        
    try:
        import core.agent
        orig_run_agent = core.agent.run_agent
        
        def patched_run_agent(user_input, stop_event=None):
            try:
                return orig_run_agent(user_input, stop_event)
            except Exception as e:
                try:
                    signals.log_message.emit(f"Agent Pipeline Failure: {str(e)}", "error")
                except Exception:
                    pass
                raise e
        core.agent.run_agent = patched_run_agent
    except Exception as e:
        print(f"[ALONE GUI HOOKS] Failed to wrap run_agent: {e}")
        
    try:
        import sys
        main_module = sys.modules.get('__main__')
        if main_module and hasattr(main_module, 'handle_audio'):
            orig_handle_audio = main_module.handle_audio
            def patched_handle_audio(audio_path):
                try:
                    orig_handle_audio(audio_path)
                except Exception as e:
                    try:
                        signals.log_message.emit(f"Audio pipeline failed: {str(e)}", "error")
                    except Exception:
                        pass
                    raise e
            main_module.handle_audio = patched_handle_audio
    except Exception as e:
        print(f"[ALONE GUI HOOKS] Failed to wrap handle_audio: {e}")

setup_runtime_hooks()


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars_count = 9
        self.amplitudes = [5.0] * self.bars_count
        self.target_amplitudes = [5.0] * self.bars_count
        self.phase = 0.0
        
        # Internal animation timer for smooth visualizer movements
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30) # ~33 FPS

    def set_amplitude(self, rms):
        # Scale and distribute the mic energy to the bars
        # Dynamic normalization to keep visualizer active but capped
        norm_rms = min(max(rms / 10.0, 2.0), 45.0)
        for i in range(self.bars_count):
            # Center bars react more than outer bars for standard visualizer look
            dist_factor = 1.0 - abs(i - (self.bars_count // 2)) / (self.bars_count / 1.5)
            self.target_amplitudes[i] = max(norm_rms * dist_factor, 4.0)

    def update_animation(self):
        self.phase += 0.15
        for i in range(self.bars_count):
            # Smoothly interpolate current amplitude to target
            self.amplitudes[i] += (self.target_amplitudes[i] - self.amplitudes[i]) * 0.25
            # Decay the target amplitude back to baseline if no new audio signal
            self.target_amplitudes[i] = max(self.target_amplitudes[i] * 0.9, 4.0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = 8
        spacing = 6
        total_width = (bar_width * self.bars_count) + (spacing * (self.bars_count - 1))
        start_x = (width - total_width) // 2
        
        for i in range(self.bars_count):
            x = start_x + i * (bar_width + spacing)
            # Add a subtle sine wave ripple for extra premium look
            ripple = math.sin(self.phase + i * 0.8) * 3.0
            bar_height = max(self.amplitudes[i] + ripple, 4.0)
            y = (height - bar_height) // 2
            
            # Electric blue color palette gradient
            color = QColor(0, 212, 255, 220)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, int(y), bar_width, int(bar_height), 4, 4)

class PulsingCircleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale = 1.0
        self.growing = True
        self.angle = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(16) # ~60 FPS for fluid motion

    def update_pulse(self):
        # Breathing / Pulsing rhythm logic
        self.angle += 0.05
        self.scale = 1.0 + math.sin(self.angle) * 0.18
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        base_radius = 22
        radius = int(base_radius * self.scale)
        
        # Translucent pulsing glow ring
        glow_color = QColor(0, 212, 255, 45)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(center_x, center_y), radius + 8, radius + 8)
        
        # Solid center core
        core_color = QColor(0, 212, 255, 230)
        core_color = QColor(0, 212, 255, 230)
        painter.setBrush(QBrush(core_color))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)


class HUDConfirmDialog(QDialog):
    def __init__(self, parent=None, title="CLEAR HISTORY", message="Are you sure, Sir?", red_theme=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(320, 160)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.frame = QWidget(self)
        border_color = "rgba(255, 68, 68, 150)" if red_theme else "rgba(0, 212, 255, 150)"
        self.frame.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(15, 15, 15, 245);
                border: 2px solid {border_color};
                border-radius: 0px;
            }}
        """)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        
        self.title_label = QLabel(title, self.frame)
        self.title_label.setFont(QFont("Outfit", 10, QFont.Bold))
        title_color = "#FF4444" if red_theme else "#00D4FF"
        self.title_label.setStyleSheet(f"color: {title_color}; border: none; background: transparent;")
        frame_layout.addWidget(self.title_label, alignment=Qt.AlignCenter)
        
        self.msg_label = QLabel(message, self.frame)
        self.msg_label.setFont(QFont("Inter", 9, QFont.Medium))
        self.msg_label.setStyleSheet("color: rgba(255, 255, 255, 220); border: none; background: transparent;")
        self.msg_label.setWordWrap(True)
        frame_layout.addWidget(self.msg_label, alignment=Qt.AlignCenter)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.no_btn = QPushButton("CANCEL", self.frame)
        self.no_btn.setFont(QFont("Outfit", 9, QFont.Bold))
        self.no_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 10);
                color: rgba(255, 255, 255, 200);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 0px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 25);
            }
        """)
        self.no_btn.clicked.connect(self.reject)
        
        self.yes_btn = QPushButton("CONFIRM", self.frame)
        self.yes_btn.setFont(QFont("Outfit", 9, QFont.Bold))
        if red_theme:
            self.yes_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 68, 68, 40);
                    color: #FF4444;
                    border: 1px solid #FF4444;
                    border-radius: 0px;
                    padding: 6px 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 68, 68, 80);
                }
            """)
        else:
            self.yes_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 212, 255, 40);
                    color: #00D4FF;
                    border: 1px solid #00D4FF;
                    border-radius: 0px;
                    padding: 6px 16px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 212, 255, 80);
                }
            """)
        self.yes_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.no_btn)
        btn_layout.addWidget(self.yes_btn)
        frame_layout.addLayout(btn_layout)
        
        layout.addWidget(self.frame)
        
        if parent:
            parent_geo = parent.geometry()
            self.move(parent_geo.center() - self.rect().center())


class LiveLogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent
        self.log_queue = []
        self.prev_state = "IDLE"
        self.current_state_item = None
        self.last_state_time = 0.0
        self.auto_scroll_paused = False
        
        # Load minimize setting
        self.settings = QSettings("ALONE", "HUD")
        self.is_minimized = self.settings.value("log_minimized", False, type=bool)
        
        self.init_ui()
        
        # Throttler QTimer (10 FPS limit to avoid CPU spikes)
        self.throttle_timer = QTimer(self)
        self.throttle_timer.timeout.connect(self.process_log_queue)
        self.throttle_timer.start(100) # 100ms = 10 FPS
        
        # Stall detection QTimer (1s resolution)
        self.stall_timer = QTimer(self)
        self.stall_timer.timeout.connect(self.check_state_stall)
        self.stall_timer.start(1000) # 1 second
        
        # Connect signals
        signals.log_message.connect(self.enqueue_log)
        signals.status_changed.connect(self.handle_state_change)
        signals.user_command_received.connect(self.handle_command)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 5)
        self.layout.setSpacing(0)
        
        # Monospaced Cyberpunk HUD Panel Frame
        self.frame = QWidget(self)
        self.frame.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 10, 10, 225);
                border: 2px solid rgba(0, 212, 255, 80);
                border-radius: 0px;
            }
        """)
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(10, 8, 10, 8)
        self.frame_layout.setSpacing(5)
        
        # Header Row
        header_layout = QHBoxLayout()
        self.title_label = QLabel("LIVE LOG", self.frame)
        self.title_label.setFont(QFont("Outfit", 9, QFont.Bold))
        self.title_label.setStyleSheet("color: rgba(255, 255, 255, 180); border: none; background: transparent;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Minimize / Maximize button
        self.toggle_btn = QPushButton("▲" if not self.is_minimized else "▼", self.frame)
        self.toggle_btn.setFixedSize(24, 20)
        self.toggle_btn.setFont(QFont("Consolas", 8, QFont.Bold))
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 10);
                color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 0px;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 212, 255, 40);
                color: #00D4FF;
                border: 1px solid #00D4FF;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_minimized)
        header_layout.addWidget(self.toggle_btn)
        
        self.frame_layout.addLayout(header_layout)
        
        # Content Container (List Widget)
        self.list_widget = QListWidget(self.frame)
        self.list_widget.setFont(QFont("Consolas", 8))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(5, 5, 5, 240);
                border: 1px solid rgba(0, 212, 255, 40);
                color: rgba(255, 255, 255, 200);
                border-radius: 0px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 2px 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 10);
            }
        """)
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.setMinimumHeight(120)
        self.list_widget.setMaximumHeight(120)
        self.frame_layout.addWidget(self.list_widget)
        
        # Connect vertical scroll bar to detect manual scrolling up
        self.list_widget.verticalScrollBar().valueChanged.connect(self.handle_scrollbar_value_changed)
        
        # Floating "Scroll to Bottom" Button
        self.scroll_btn = QPushButton("Scroll to bottom ↓", self.frame)
        self.scroll_btn.setFont(QFont("Outfit", 8, QFont.Bold))
        self.scroll_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 212, 255, 200);
                color: #050505;
                border: none;
                border-radius: 0px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #00D4FF;
            }
        """)
        self.scroll_btn.clicked.connect(self.scroll_to_bottom)
        self.scroll_btn.hide()
        
        self.frame_layout.addWidget(self.scroll_btn)
        
        self.layout.addWidget(self.frame)
        
        # Apply initial minimized state
        if self.is_minimized:
            self.list_widget.hide()
            self.scroll_btn.hide()
            self.setFixedHeight(35)
        else:
            self.list_widget.show()
            self.setFixedHeight(175)

    def enqueue_log(self, text, category="info"):
        self.log_queue.append((text, category))

    def process_log_queue(self):
        if not self.log_queue:
            return
            
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        while self.log_queue:
            text, category = self.log_queue.pop(0)
            
            # Format: [HH:MM:SS] message
            log_line = f"[{timestamp}] {text}"
            item = QListWidgetItem(log_line)
            
            # Category color coding
            if category == "error":
                item.setForeground(QColor("#FF4444")) # red text
            elif category == "command":
                item.setForeground(QColor("#00D4FF")) # cyan/blue text
            elif category == "action":
                item.setForeground(QColor(255, 255, 255, 220)) # neutral white
            elif category == "stall":
                item.setBackground(QColor(255, 200, 0, 45)) # yellow translucent
                item.setForeground(QColor(255, 215, 0)) # gold text
            else:
                item.setForeground(QColor(200, 200, 200)) # gray text
                
            self.list_widget.addItem(item)
            
            # FIFO Eviction - limit to 200 items in memory
            if self.list_widget.count() > 200:
                self.list_widget.takeItem(0)
                
        # Auto-scroll if not paused
        if not self.auto_scroll_paused and not self.is_minimized:
            self.list_widget.scrollToBottom()

    def handle_scrollbar_value_changed(self, value):
        vbar = self.list_widget.verticalScrollBar()
        if self.is_minimized:
            return
            
        # If the user has scrolled up, show the button and pause auto scroll
        if value < vbar.maximum() - 8:
            if not self.auto_scroll_paused:
                self.auto_scroll_paused = True
                self.scroll_btn.show()
        else:
            if self.auto_scroll_paused:
                self.auto_scroll_paused = False
                self.scroll_btn.hide()

    def scroll_to_bottom(self):
        self.list_widget.scrollToBottom()
        self.scroll_btn.hide()
        self.auto_scroll_paused = False

    def handle_state_change(self, state):
        state_upper = state.upper().strip()
        
        # Log transition
        if state_upper != self.prev_state:
            signals.log_message.emit(f"Transitioning: {self.prev_state} → {state_upper}", "info")
            
        self.prev_state = state_upper
        
        # Track current state item for stall detection
        import time
        self.last_state_time = time.time()
        
        if state_upper == "LISTENING":
            signals.log_message.emit("Listening for command...", "info")
        elif state_upper == "THINKING":
            signals.log_message.emit("Processing command...", "info")
            
        QTimer.singleShot(150, self.update_current_state_item)

    def update_current_state_item(self):
        if self.list_widget.count() > 0:
            self.current_state_item = self.list_widget.item(self.list_widget.count() - 1)

    def handle_command(self, cmd_text):
        signals.log_message.emit(f"Command received: \"{cmd_text}\"", "command")

    def check_state_stall(self):
        if self.current_state_item and not getattr(self.current_state_item, "is_stalled", False):
            import time
            elapsed = time.time() - self.last_state_time
            if elapsed > 10.0:
                self.current_state_item.is_stalled = True
                self.current_state_item.setBackground(QColor(255, 200, 0, 45))
                self.current_state_item.setForeground(QColor(255, 215, 0))
                signals.log_message.emit(f"Warning: Agent stalled in state '{self.prev_state}' for >10 seconds", "stall")

    def toggle_minimized(self):
        self.is_minimized = not self.is_minimized
        self.settings.setValue("log_minimized", self.is_minimized)
        
        if self.is_minimized:
            self.list_widget.hide()
            self.scroll_btn.hide()
            self.toggle_btn.setText("▼")
            self.setFixedHeight(35)
        else:
            self.list_widget.show()
            self.toggle_btn.setText("▲")
            self.setFixedHeight(175)
            self.scroll_to_bottom()
            
        if self.parent_win and hasattr(self.parent_win, "adjust_window_size"):
            self.parent_win.adjust_window_size()


class HistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_win = parent
        self.pending_command = None
        self.pending_timestamp = None
        
        # Load minimize setting
        self.settings = QSettings("ALONE", "HUD")
        self.is_minimized = self.settings.value("hist_minimized", False, type=bool)
        
        self.history_filepath = os.path.join(os.path.expanduser("~/.alone/gui"), "gui_history.json")
        self.history_data = self.load_history()
        
        self.init_ui()
        
        # Populate history GUI (newest on top)
        self.populate_history_gui()
        
        # Connect signals
        signals.user_command_received.connect(self.on_command_received)
        signals.response_received.connect(self.on_response_received)
        signals.command_completed.connect(self.on_command_completed)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 10)
        self.layout.setSpacing(0)
        
        # Monospaced Cyberpunk HUD Panel Frame
        self.frame = QWidget(self)
        self.frame.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 10, 10, 225);
                border: 2px solid rgba(0, 212, 255, 80);
                border-radius: 0px;
            }
        """)
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(10, 8, 10, 8)
        self.frame_layout.setSpacing(5)
        
        # Header Row
        header_layout = QHBoxLayout()
        self.title_label = QLabel("HISTORY", self.frame)
        self.title_label.setFont(QFont("Outfit", 9, QFont.Bold))
        self.title_label.setStyleSheet("color: rgba(255, 255, 255, 180); border: none; background: transparent;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Clear History Button
        self.clear_btn = QPushButton("CLEAR", self.frame)
        self.clear_btn.setFont(QFont("Outfit", 8, QFont.Bold))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 68, 68, 20);
                color: #FF4444;
                border: 1px solid rgba(255, 68, 68, 40);
                border-radius: 0px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 68, 68, 60);
                color: #FF2222;
                border: 1px solid #FF2222;
            }
        """)
        self.clear_btn.clicked.connect(self.confirm_clear_history)
        header_layout.addWidget(self.clear_btn)
        
        # Minimize / Maximize button
        self.toggle_btn = QPushButton("▲" if not self.is_minimized else "▼", self.frame)
        self.toggle_btn.setFixedSize(24, 20)
        self.toggle_btn.setFont(QFont("Consolas", 8, QFont.Bold))
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 10);
                color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 0px;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 212, 255, 40);
                color: #00D4FF;
                border: 1px solid #00D4FF;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_minimized)
        header_layout.addWidget(self.toggle_btn)
        
        self.frame_layout.addLayout(header_layout)
        
        # Content Container (List Widget)
        self.list_widget = QListWidget(self.frame)
        self.list_widget.setFont(QFont("Consolas", 8))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(5, 5, 5, 240);
                border: 1px solid rgba(0, 212, 255, 40);
                color: rgba(255, 255, 255, 200);
                border-radius: 0px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid rgba(255, 255, 255, 10);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 212, 255, 30);
                color: #00D4FF;
                border: 1px solid #00D4FF;
            }
        """)
        self.list_widget.setMinimumHeight(120)
        self.list_widget.setMaximumHeight(120)
        self.frame_layout.addWidget(self.list_widget)
        
        self.layout.addWidget(self.frame)
        
        # Apply initial minimized state
        if self.is_minimized:
            self.list_widget.hide()
            self.clear_btn.hide()
            self.setFixedHeight(35)
        else:
            self.list_widget.show()
            self.clear_btn.show()
            self.setFixedHeight(175)

    def load_history(self):
        import json
        if not os.path.exists(self.history_filepath):

            return []
            
        try:
            with open(self.history_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Perform strict 7-day retention filtering
                import datetime
                seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                filtered = []
                for entry in data:
                    try:
                        entry_date = datetime.datetime.strptime(entry.get("date", ""), "%Y-%m-%d")
                        if entry_date >= seven_days_ago:
                            filtered.append(entry)
                    except Exception:
                        filtered.append(entry)
                        
                # Perform 500 entries FIFO cap
                return filtered[-500:]
        except Exception as e:
            print(f"[ALONE GUI HISTORY] Failed to load: {e}")
            return []

    def save_history_async(self):
        import json
        import threading
        filepath = self.history_filepath
        data_to_write = list(self.history_data)
        
        def write_thread():
            try:
                path = os.path.dirname(filepath)
                os.makedirs(path, exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data_to_write, f, indent=2)
            except Exception as e:
                print(f"[ALONE GUI HISTORY] Off-thread write failed: {e}")
                
        threading.Thread(target=write_thread, daemon=True).start()

    def populate_history_gui(self):
        self.list_widget.clear()
        # Newer items are displayed at the top
        for entry in reversed(self.history_data):
            time_str = entry.get("timestamp", "")
            cmd_str = entry.get("command", "")
            outcome_str = entry.get("outcome", "")
            
            # Format: [HH:MM:SS] "command" → outcome
            display_text = f"[{time_str}] \"{cmd_str}\" → {outcome_str}"
            item = QListWidgetItem(display_text)
            self.list_widget.addItem(item)

    def on_command_received(self, cmd_text):
        import datetime
        self.pending_command = cmd_text
        self.pending_timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    def on_response_received(self, response_text):
        if self.pending_command:
            import datetime
            
            # Outcome formatting
            outcome = str(response_text).strip()
            # Trim the outcome if it's too wordy to look clean
            if "i apologize" in outcome.lower() and "mechanical hands" in outcome.lower():
                outcome = "Failed (Internal Error)"
            else:
                for garbage in ["Sir, ", "Sir.", "sir, ", "sir."]:
                    outcome = outcome.replace(garbage, "")
                outcome = outcome.strip()
                if len(outcome) > 55:
                    outcome = outcome[:52] + "..."
            
            signals.command_completed.emit(self.pending_timestamp, self.pending_command, outcome)
            self.pending_command = None

    def on_command_completed(self, timestamp, command, outcome):
        import datetime
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        entry = {
            "timestamp": timestamp,
            "command": command,
            "outcome": outcome,
            "date": date_str
        }
        
        # Add to local collection
        self.history_data.append(entry)
        if len(self.history_data) > 500:
            self.history_data.pop(0)
            
        # Save to JSON off the main thread
        self.save_history_async()
        
        # Insert at the very top of QListWidget (index 0)
        display_text = f"[{timestamp}] \"{command}\" → {outcome}"
        item = QListWidgetItem(display_text)
        self.list_widget.insertItem(0, item)

    def confirm_clear_history(self):
        confirm = HUDConfirmDialog(self.parent_win, "CLEAR HISTORY", "Are you sure you want to clear session history, Sir?")
        if confirm.exec_() == QDialog.Accepted:
            self.history_data.clear()
            self.list_widget.clear()
            self.save_history_async()
            signals.log_message.emit("System Action: Session history cleared by user request", "info")

    def toggle_minimized(self):
        self.is_minimized = not self.is_minimized
        self.settings.setValue("hist_minimized", self.is_minimized)
        
        if self.is_minimized:
            self.list_widget.hide()
            self.clear_btn.hide()
            self.toggle_btn.setText("▼")
            self.setFixedHeight(35)
        else:
            self.list_widget.show()
            self.clear_btn.show()
            self.toggle_btn.setText("▲")
            self.setFixedHeight(175)
            
        if self.parent_win and hasattr(self.parent_win, "adjust_window_size"):
            self.parent_win.adjust_window_size()


class AloneHUDWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = QPoint()
        self.init_ui()
        
        # Connect signals
        signals.status_changed.connect(self.set_status)
        signals.amplitude_received.connect(self.handle_amplitude)
        signals.user_command_received.connect(self.set_user_command)
        signals.response_received.connect(self.set_response)

    def init_ui(self):
        # Sleek, Frameless, Always-On-Top desktop configuration
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Base Layout setup
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # Premium Dark Sleek Frame Container Widget
        self.frame = QWidget(self)
        self.frame.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 10, 10, 225);
                border: 2px solid rgba(0, 212, 255, 80);
                border-radius: 12px;
            }
        """)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(15, 12, 15, 12)
        
        # --- Top Row: Status Indicator & Visualizers ---
        top_row = QHBoxLayout()
        
        self.status_label = QLabel("IDLE", self.frame)
        self.status_label.setFont(QFont("Outfit", 9, QFont.Bold))
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 180); border: none; background: transparent;")
        top_row.addWidget(self.status_label, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        
        # Audio visualizers (initially hidden)
        self.waveform = WaveformWidget(self.frame)
        self.waveform.setFixedHeight(50)
        self.waveform.setStyleSheet("border: none; background: transparent;")
        self.waveform.hide()
        top_row.addWidget(self.waveform)
        
        self.pulse = PulsingCircleWidget(self.frame)
        self.pulse.setFixedSize(60, 60)
        self.pulse.setStyleSheet("border: none; background: transparent;")
        self.pulse.hide()
        top_row.addWidget(self.pulse, alignment=Qt.AlignCenter)
        
        top_row.addStretch()
        
        # Small visualizer pad to balance HUD spacing when visualizers are hidden
        self.balancer = QWidget(self.frame)
        self.balancer.setFixedSize(60, 50)
        self.balancer.setStyleSheet("border: none; background: transparent;")
        top_row.addWidget(self.balancer)
        
        frame_layout.addLayout(top_row)
        
        # --- Text Display Rows ---
        self.user_label = QLabel("Awaiting command...", self.frame)
        self.user_label.setWordWrap(True)
        self.user_label.setFont(QFont("Inter", 9, QFont.Medium))
        self.user_label.setStyleSheet("color: rgba(255, 255, 255, 220); border: none; background: transparent;")
        frame_layout.addWidget(self.user_label)
        
        self.response_label = QLabel("A.L.O.N.E. online. Ready, Sir.", self.frame)
        self.response_label.setWordWrap(True)
        self.response_label.setFont(QFont("Inter", 9))
        self.response_label.setStyleSheet("color: #00D4FF; border: none; background: transparent;")
        frame_layout.addWidget(self.response_label)
        
        # Instantiate Collapsible Panels
        self.log_panel = LiveLogPanel(self)
        self.history_panel = HistoryPanel(self)
        
        # Add Stop Agent button at the bottom with a red HUD theme
        self.stop_btn = QPushButton("STOP AGENT", self)
        self.stop_btn.setFont(QFont("Outfit", 9, QFont.Bold))
        self.stop_btn.setFixedHeight(35)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 68, 68, 15);
                color: #FF4444;
                border: 1.5px solid rgba(255, 68, 68, 100);
                border-radius: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 68, 68, 40);
                color: #FF2222;
                border: 1.5px solid #FF2222;
            }
        """)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        
        main_layout.addWidget(self.frame)
        main_layout.addWidget(self.log_panel)
        main_layout.addWidget(self.history_panel)
        main_layout.addWidget(self.stop_btn)
        
        self.setLayout(main_layout)
        
        # Calculate dynamic size hint height
        self.adjust_window_size_initial()
        
        self.center_to_screen_bottom_right()
        self.setup_tray()

    def adjust_window_size_initial(self):
        h_frame = max(self.frame.sizeHint().height(), 160)
        h_log = self.log_panel.height()
        h_hist = self.history_panel.height()
        h_stop = self.stop_btn.height() if hasattr(self, 'stop_btn') else 0
        total_height = h_frame + h_log + h_hist + h_stop + 30
        self.setMinimumSize(400, total_height)
        self.setMaximumSize(400, total_height)
        self.resize(400, total_height)

    def adjust_window_size(self):
        old_geo = self.geometry()
        
        h_frame = max(self.frame.sizeHint().height(), 160)
        h_log = self.log_panel.height()
        h_hist = self.history_panel.height()
        h_stop = self.stop_btn.height() if hasattr(self, 'stop_btn') else 0
        
        total_height = h_frame + h_log + h_hist + h_stop + 30
        self.setMinimumSize(400, total_height)
        self.setMaximumSize(400, total_height)
        
        # Keep bottom-right anchor position of the HUD window completely stable
        new_y = old_geo.bottom() - total_height
        self.setGeometry(old_geo.x(), new_y, 400, total_height)



    def center_to_screen_bottom_right(self):
        # Dynamically place window at the bottom right corner above system tray
        screen = QApplication.primaryScreen().geometry()
        margin_x = 30
        margin_y = 60 # Leave vertical space for taskbars
        x = screen.width() - self.width() - margin_x
        y = screen.height() - self.height() - margin_y
        self.move(x, y)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Build simple fallback visual dot icon if PNG is missing
        pixmap = QPainter()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "tray_icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback dot icon
            from PyQt5.QtGui import QPixmap
            pm = QPixmap(16, 16)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            painter.setBrush(QBrush(QColor(0, 212, 255)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            self.tray_icon.setIcon(QIcon(pm))
            
        # Context Menu setups
        tray_menu = QMenu()
        
        open_action = QAction("Open ALONE", self)
        open_action.triggered.connect(self.show_hud)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(signals.open_settings.emit)
        
        memory_action = QAction("Memory Editor", self)
        memory_action.triggered.connect(self.open_memory_editor)
        
        quit_action = QAction("Quit ALONE", self)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(open_action)
        tray_menu.addAction(settings_action)
        tray_menu.addAction(memory_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)

    def open_memory_editor(self):
        from ui.memory_ui import AloneMemoryWindow
        self.memory_win = AloneMemoryWindow(self)
        self.memory_win.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_hud()

    def show_hud(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def set_status(self, status):
        status_upper = status.upper().strip()
        self.status_label.setText(status_upper)
        
        # Toggle component displays based on status state
        if status_upper == "LISTENING":
            self.status_label.setStyleSheet("color: #00D4FF; border: none; background: transparent;")
            self.waveform.show()
            self.pulse.hide()
            self.balancer.hide()
        elif status_upper == "THINKING":
            self.status_label.setStyleSheet("color: rgba(255, 255, 255, 140); border: none; background: transparent;")
            self.waveform.hide()
            self.pulse.show()
            self.balancer.hide()
        elif status_upper == "SPEAKING":
            self.status_label.setStyleSheet("color: #00D4FF; border: none; background: transparent;")
            self.waveform.hide()
            self.pulse.hide()
            self.balancer.show()
        else: # IDLE
            self.status_label.setStyleSheet("color: rgba(255, 255, 255, 180); border: none; background: transparent;")
            self.waveform.hide()
            self.pulse.hide()
            self.balancer.show()

    def handle_amplitude(self, rms):
        # Forward RMS volume spikes straight to visualizer
        if self.status_label.text() == "LISTENING":
            self.waveform.set_amplitude(rms)

    def set_user_command(self, text):
        self.user_label.setText(f"You: {text}")

    def set_response(self, text):
        self.response_label.setText(text)

    # --- Mouse-Drag handlers to reposition frameless overlay ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if not self.old_pos.isNull():
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = QPoint()

    def on_stop_clicked(self):
        confirm = HUDConfirmDialog(self, "STOP AGENT", "Are you sure you want to stop the agent, Sir?", red_theme=True)
        if confirm.exec_() == QDialog.Accepted:
            # Disappear from screen instantly
            self.hide()
            self.tray_icon.hide()
            QApplication.processEvents()
            # Execute clean shutdown sequence
            self.quit_app()

    def quit_app(self):
        self.tray_icon.hide()
        # Trigger background shutdown handlers safely
        from main import _shutdown_flag
        _shutdown_flag.set()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AloneHUDWindow()
    window.show()
    sys.exit(app.exec_())
