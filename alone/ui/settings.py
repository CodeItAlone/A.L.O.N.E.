import os
import sys
import yaml
import platform
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout, 
                             QComboBox, QSlider, QLineEdit, QCheckBox, 
                             QPushButton, QApplication)

class AloneSettingsWindow(QDialog):
    def __init__(self, parent=None, config_path=None):
        super().__init__(parent)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if config_path is None:
            self.config_path = os.path.join(base_dir, "config.yaml")
        else:
            self.config_path = config_path
        
        # Load local path safeguards
        if not os.path.exists(self.config_path):
            if os.path.exists("config.yaml"):
                self.config_path = "config.yaml"
            elif os.path.exists("../config.yaml"):
                self.config_path = "../config.yaml"
                
        self.config = self.load_config()
        self.init_ui()

    def load_config(self):
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"[Settings Warning] Failed to load config: {e}")
            return {}

    def save_config(self):
        try:
            # 1. Gather UI field values
            model = self.model_combo.currentText()
            speed = self.speed_slider.value()
            wake_word = self.wake_word_input.text().strip().lower().replace(" ", "_")
            startup_enabled = self.startup_checkbox.isChecked()
            
            # 2. Update config object
            self.config["model"] = model
            if "voice" not in self.config:
                self.config["voice"] = {}
            self.config["voice"]["rate"] = speed
            self.config["voice"]["wake_word"] = wake_word
            
            # 3. Synchronize startup batch trigger
            self.sync_startup(startup_enabled)
            
            # 4. Save back to YAML file
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
                
            print(f"[Settings] Configuration saved successfully to {self.config_path}.")
            self.accept() # Close dialog
        except Exception as e:
            print(f"[Settings Error] Failed to save config: {e}")

    def sync_startup(self, enable):
        # Build registry or Startup Folder boot shortcuts
        if platform.system() == "Windows":
            try:
                startup_folder = os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
                shortcut_path = os.path.join(startup_folder, "ALONE.lnk")
                
                if enable:
                    if not os.path.exists(shortcut_path):
                        # Create startup shortcut via setup script triggering
                        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        bat_setup = os.path.join(script_dir, "install", "setup.bat")
                        if os.path.exists(bat_setup):
                            os.system(f'"{bat_setup}"')
                else:
                    if os.path.exists(shortcut_path):
                        os.remove(shortcut_path)
            except Exception as ex:
                print(f"[Startup Warning] Failed to sync Windows startup shortcut: {ex}")

    def init_ui(self):
        self.setWindowTitle("A.L.O.N.E. - Settings")
        self.resize(380, 420)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        # Color palettes matched to HUD window
        self.setStyleSheet("""
            QDialog {
                background-color: #0A0A0A;
                border: 1px solid rgba(0, 212, 255, 100);
            }
            QLabel {
                color: #FFFFFF;
                background: transparent;
            }
            QComboBox {
                background-color: #161616;
                color: #FFFFFF;
                border: 1px solid rgba(0, 212, 255, 100);
                border-radius: 4px;
                padding: 6px;
                min-width: 150px;
            }
            QComboBox QAbstractItemView {
                background-color: #161616;
                color: #FFFFFF;
                selection-background-color: #00D4FF;
                selection-color: #0A0A0A;
            }
            QSlider::groove:horizontal {
                border: 1px solid #161616;
                height: 6px;
                background: #161616;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #00D4FF;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #00D4FF;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #161616;
                color: #FFFFFF;
                border: 1px solid rgba(0, 212, 255, 100);
                border-radius: 4px;
                padding: 6px;
            }
            QCheckBox {
                color: #FFFFFF;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid rgba(0, 212, 255, 100);
                border-radius: 3px;
                background-color: #161616;
            }
            QCheckBox::indicator:checked {
                background-color: #00D4FF;
                image: url(checked.png); /* PyQt will render fallback background color if missing */
            }
            QPushButton {
                background-color: #161616;
                color: #00D4FF;
                border: 1.5px solid #00D4FF;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00D4FF;
                color: #0A0A0A;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        # Window Header
        header = QLabel("A.L.O.N.E. CONFIGURATION", self)
        header.setFont(QFont("Outfit", 12, QFont.Bold))
        header.setStyleSheet("color: #00D4FF; background: transparent;")
        layout.addWidget(header, alignment=Qt.AlignCenter)
        
        # Divider Line
        divider = QLabel(self)
        divider.setFixedHeight(2)
        divider.setStyleSheet("background-color: rgba(0, 212, 255, 40); border: none;")
        layout.addWidget(divider)

        # 1. Model Selection Box
        row1 = QHBoxLayout()
        label1 = QLabel("Brain Model:", self)
        label1.setFont(QFont("Inter", 10, QFont.Medium))
        row1.addWidget(label1)
        
        self.model_combo = QComboBox(self)
        self.model_combo.addItems(["llama3.1:8b", "mistral:7b", "codellama:7b", "llama3.1"])
        # Find and set current config model selection
        cur_model = self.config.get("model", "llama3.1:8b")
        idx = self.model_combo.findText(cur_model)
        if idx != -1:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.addItem(cur_model)
            self.model_combo.setCurrentText(cur_model)
        row1.addWidget(self.model_combo)
        layout.addLayout(row1)

        # 2. TTS Voice speed slider
        row2 = QVBoxLayout()
        row2_top = QHBoxLayout()
        label2 = QLabel("Speech Voice Speed:", self)
        label2.setFont(QFont("Inter", 10, QFont.Medium))
        row2_top.addWidget(label2)
        
        self.speed_val_label = QLabel("175 WPM", self)
        self.speed_val_label.setStyleSheet("color: #00D4FF;")
        row2_top.addWidget(self.speed_val_label, alignment=Qt.AlignRight)
        row2.addLayout(row2_top)
        
        self.speed_slider = QSlider(Qt.Horizontal, self)
        self.speed_slider.setRange(100, 250)
        cur_speed = self.config.get("voice", {}).get("rate", 175)
        self.speed_slider.setValue(cur_speed)
        self.speed_val_label.setText(f"{cur_speed} WPM")
        self.speed_slider.valueChanged.connect(lambda v: self.speed_val_label.setText(f"{v} WPM"))
        row2.addWidget(self.speed_slider)
        layout.addLayout(row2)

        # 3. Wake Word Input Line
        row3 = QHBoxLayout()
        label3 = QLabel("Wake Word Trigger:", self)
        label3.setFont(QFont("Inter", 10, QFont.Medium))
        row3.addWidget(label3)
        
        self.wake_word_input = QLineEdit(self)
        cur_ww = self.config.get("voice", {}).get("wake_word", "hey_alone")
        self.wake_word_input.setText(cur_ww)
        row3.addWidget(self.wake_word_input)
        layout.addLayout(row3)

        # 4. Windows Startup Checkbox
        row4 = QHBoxLayout()
        self.startup_checkbox = QCheckBox("Automatically launch on system startup", self)
        self.startup_checkbox.setFont(QFont("Inter", 9))
        
        # Check if startup shortcut is currently present in directory
        has_startup = False
        try:
            if platform.system() == "Windows":
                shortcut_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "ALONE.lnk")
                has_startup = os.path.exists(shortcut_path)
        except Exception:
            pass
        self.startup_checkbox.setChecked(has_startup)
        row4.addWidget(self.startup_checkbox)
        layout.addLayout(row4)
        
        # Divider Line
        divider2 = QLabel(self)
        divider2.setFixedHeight(2)
        divider2.setStyleSheet("background-color: rgba(0, 212, 255, 40); border: none;")
        layout.addWidget(divider2)

        # 5. Buttons footer
        footer = QHBoxLayout()
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        
        manage_mem_btn = QPushButton("Manage Memory", self)
        manage_mem_btn.clicked.connect(self.open_memory_editor)
        
        save_btn = QPushButton("Save Settings", self)
        save_btn.clicked.connect(self.save_config)
        
        footer.addWidget(cancel_btn)
        footer.addWidget(manage_mem_btn)
        footer.addWidget(save_btn)
        layout.addLayout(footer)

        self.setLayout(layout)

    def open_memory_editor(self):
        from ui.memory_ui import AloneMemoryWindow
        self.memory_win = AloneMemoryWindow(self)
        self.memory_win.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AloneSettingsWindow()
    window.show()
    sys.exit(app.exec_())
