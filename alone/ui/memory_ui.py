import os
import sys
import uuid

# Ensure the 'alone' folder is added to sys.path so 'core' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (QDialog, QLabel, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QLineEdit, QComboBox, QTextEdit,
                             QMessageBox, QHeaderView)

from core.human_memory import database, service
from core.preferences_service import preference_service

class AloneMemoryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("A.L.O.N.E. - Memory Editor")
        self.resize(650, 520)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        
        # Cyberpunk style sheet matching Settings and HUD
        self.setStyleSheet("""
            QDialog {
                background-color: #0A0A0A;
                border: 1px solid rgba(0, 212, 255, 100);
            }
            QLabel {
                color: #FFFFFF;
                background: transparent;
            }
            QTabWidget::pane {
                border: 1px solid rgba(0, 212, 255, 50);
                background: #0A0A0A;
            }
            QTabBar::tab {
                background: #161616;
                color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(0, 212, 255, 40);
                padding: 8px 16px;
                font-family: 'Outfit';
                font-size: 9pt;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #0A0A0A;
                color: #00D4FF;
                border-bottom-color: #0A0A0A;
                border-top: 2px solid #00D4FF;
            }
            QTableWidget {
                background-color: #0F0F0F;
                color: #FFFFFF;
                border: 1px solid rgba(0, 212, 255, 45);
                gridline-color: rgba(255, 255, 255, 15);
                font-family: 'Consolas';
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #161616;
                color: #00D4FF;
                padding: 4px;
                border: 1px solid rgba(0, 212, 255, 30);
                font-family: 'Outfit';
                font-weight: bold;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #161616;
                color: #FFFFFF;
                border: 1px solid rgba(0, 212, 255, 80);
                border-radius: 2px;
                padding: 6px;
                font-family: 'Inter';
            }
            QPushButton {
                background-color: #161616;
                color: #00D4FF;
                border: 1px solid #00D4FF;
                border-radius: 4px;
                padding: 6px 14px;
                font-family: 'Outfit';
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #00D4FF;
                color: #0A0A0A;
            }
            QPushButton#delete_btn {
                border-color: #FF4444;
                color: #FF4444;
            }
            QPushButton#delete_btn:hover {
                background-color: #FF4444;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header Title
        title_label = QLabel("HUMAN MEMORY DATABASE EDITOR", self)
        title_label.setFont(QFont("Outfit", 12, QFont.Bold))
        title_label.setStyleSheet("color: #00D4FF;")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Tabs Layout
        self.tabs = QTabWidget(self)
        
        self.profile_tab = self.create_key_value_tab(is_preferences=False)
        self.preferences_tab = self.create_key_value_tab(is_preferences=True)
        self.projects_tab = self.create_projects_tab()
        self.goals_tab = self.create_goals_tab()
        self.relationships_tab = self.create_relationships_tab()
        self.tasks_tab = self.create_tasks_tab()

        self.tabs.addTab(self.profile_tab, "User Profile")
        self.tabs.addTab(self.preferences_tab, "Preferences")
        self.tabs.addTab(self.projects_tab, "Projects")
        self.tabs.addTab(self.goals_tab, "Goals")
        self.tabs.addTab(self.relationships_tab, "Relationships")
        self.tabs.addTab(self.tasks_tab, "Tasks")

        layout.addWidget(self.tabs)

        # Footer Close Button
        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Done", self)
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self.setLayout(layout)

        # Load data initially
        self.load_profile_data()
        self.load_preferences_data()
        self.load_projects_data()
        self.load_goals_data()
        self.load_relationships_data()
        self.load_tasks_data()

    # --- KEY-VALUE TABS CREATOR (PROFILE & PREFERENCES) ---
    def create_key_value_tab(self, is_preferences):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Key", "Value"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)

        if is_preferences:
            self.pref_table = table
        else:
            self.profile_table = table

        # Bottom row form and controls
        controls = QHBoxLayout()
        key_input = QLineEdit()
        key_input.setPlaceholderText("Key (e.g. user_name)")
        val_input = QLineEdit()
        val_input.setPlaceholderText("Value (e.g. JARVIS)")
        
        add_btn = QPushButton("Save Field")
        if is_preferences:
            add_btn.clicked.connect(lambda: self.save_preference_field(key_input, val_input))
        else:
            add_btn.clicked.connect(lambda: self.save_profile_field(key_input, val_input))

        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("delete_btn")
        if is_preferences:
            del_btn.clicked.connect(lambda: self.delete_preference_field(key_input, val_input))
        else:
            del_btn.clicked.connect(lambda: self.delete_profile_field(key_input, val_input))

        controls.addWidget(key_input)
        controls.addWidget(val_input)
        controls.addWidget(add_btn)
        controls.addWidget(del_btn)
        layout.addLayout(controls)

        # Bind row selection to form autofill
        table.itemSelectionChanged.connect(lambda: self.autofill_key_value(table, key_input, val_input))

        return tab

    def autofill_key_value(self, table, key_input, val_input):
        selected = table.selectedItems()
        if len(selected) >= 2:
            key_input.setText(selected[0].text())
            val_input.setText(selected[1].text())

    # --- PROFILE CRUD UI ---
    def load_profile_data(self):
        self.profile_table.setRowCount(0)
        profile = database.get_profile()
        for row_idx, (key, value) in enumerate(profile.items()):
            self.profile_table.insertRow(row_idx)
            self.profile_table.setItem(row_idx, 0, QTableWidgetItem(key))
            self.profile_table.setItem(row_idx, 1, QTableWidgetItem(value))

    def save_profile_field(self, key_input, val_input):
        key = key_input.text().strip()
        val = val_input.text().strip()
        if not key or not val:
            QMessageBox.warning(self, "Invalid Inputs", "Please enter both key and value, Sir.")
            return
        database.set_profile_field(key, val)
        service.sync_profile_to_vector()
        self.load_profile_data()
        key_input.clear()
        val_input.clear()

    def delete_profile_field(self, key_input, val_input):
        key = key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "No Field Selected", "Please select a field to delete, Sir.")
            return
        database.delete_profile_field(key)
        service.sync_profile_to_vector()
        self.load_profile_data()
        key_input.clear()
        val_input.clear()

    # --- PREFERENCES CRUD UI ---
    def load_preferences_data(self):
        self.pref_table.setRowCount(0)
        prefs = database.get_preferences()
        for row_idx, (key, data) in enumerate(prefs.items()):
            self.pref_table.insertRow(row_idx)
            self.pref_table.setItem(row_idx, 0, QTableWidgetItem(key))
            self.pref_table.setItem(row_idx, 1, QTableWidgetItem(data["value"]))

    def save_preference_field(self, key_input, val_input):
        key = key_input.text().strip()
        val = val_input.text().strip()
        if not key or not val:
            QMessageBox.warning(self, "Invalid Inputs", "Please enter both key and value, Sir.")
            return
        preference_service.save_preference(key, val)
        self.load_preferences_data()
        key_input.clear()
        val_input.clear()

    def delete_preference_field(self, key_input, val_input):
        key = key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "No Field Selected", "Please select a field to delete, Sir.")
            return
        preference_service.delete_preference(key)
        self.load_preferences_data()
        key_input.clear()
        val_input.clear()

    # --- PROJECTS TAB CREATOR ---
    def create_projects_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Projects Table
        self.proj_table = QTableWidget(0, 4)
        self.proj_table.setHorizontalHeaderLabels(["ID", "Name", "Description", "Status"])
        self.proj_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.proj_table)

        # Form Controls
        form = QVBoxLayout()
        row1 = QHBoxLayout()
        self.proj_name_input = QLineEdit()
        self.proj_name_input.setPlaceholderText("Project Name")
        self.proj_status_combo = QComboBox()
        self.proj_status_combo.addItems(["active", "completed", "paused", "archived"])
        row1.addWidget(self.proj_name_input)
        row1.addWidget(self.proj_status_combo)
        form.addLayout(row1)

        self.proj_desc_input = QTextEdit()
        self.proj_desc_input.setPlaceholderText("Description...")
        self.proj_desc_input.setFixedHeight(50)
        form.addWidget(self.proj_desc_input)

        # Action Buttons
        actions = QHBoxLayout()
        self.proj_id_label = QLabel("New Project (Auto-ID)")
        self.proj_id_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 8pt;")
        
        save_btn = QPushButton("Save Project")
        save_btn.clicked.connect(self.save_project)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("delete_btn")
        del_btn.clicked.connect(self.delete_project)

        actions.addWidget(self.proj_id_label)
        actions.addStretch()
        actions.addWidget(save_btn)
        actions.addWidget(del_btn)
        form.addLayout(actions)
        layout.addLayout(form)

        # Bind row selection
        self.proj_table.itemSelectionChanged.connect(self.autofill_project)

        return tab

    def autofill_project(self):
        selected = self.proj_table.selectedItems()
        if len(selected) >= 4:
            self.proj_id_label.setText(selected[0].text())
            self.proj_name_input.setText(selected[1].text())
            self.proj_desc_input.setPlainText(selected[2].text())
            self.proj_status_combo.setCurrentText(selected[3].text())

    def load_projects_data(self):
        self.proj_table.setRowCount(0)
        projects = database.get_projects()
        for row_idx, p in enumerate(projects):
            self.proj_table.insertRow(row_idx)
            self.proj_table.setItem(row_idx, 0, QTableWidgetItem(p["id"]))
            self.proj_table.setItem(row_idx, 1, QTableWidgetItem(p["name"]))
            self.proj_table.setItem(row_idx, 2, QTableWidgetItem(p["description"]))
            self.proj_table.setItem(row_idx, 3, QTableWidgetItem(p["status"]))

    def save_project(self):
        proj_id = self.proj_id_label.text()
        name = self.proj_name_input.text().strip()
        desc = self.proj_desc_input.toPlainText().strip()
        status = self.proj_status_combo.currentText()

        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a project name, Sir.")
            return

        if "New Project" in proj_id:
            proj_id = str(uuid.uuid4())[:8]
            database.add_project(proj_id, name, desc, status)
        else:
            database.update_project(proj_id, name, desc, status)

        service.sync_project_to_vector(proj_id, name, desc, status)
        self.load_projects_data()
        
        # Reset Inputs
        self.proj_id_label.setText("New Project (Auto-ID)")
        self.proj_name_input.clear()
        self.proj_desc_input.clear()

    def delete_project(self):
        proj_id = self.proj_id_label.text()
        if "New Project" in proj_id:
            QMessageBox.warning(self, "No Project Selected", "Please select a project to delete, Sir.")
            return
        database.delete_project(proj_id)
        service.delete_project_vector(proj_id)
        self.load_projects_data()
        
        # Reset Inputs
        self.proj_id_label.setText("New Project (Auto-ID)")
        self.proj_name_input.clear()
        self.proj_desc_input.clear()

    # --- GOALS TAB CREATOR ---
    def create_goals_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Goals Table
        self.goals_table = QTableWidget(0, 5)
        self.goals_table.setHorizontalHeaderLabels(["ID", "Title", "Description", "Status", "Target Date"])
        self.goals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.goals_table)

        # Form Controls
        form = QVBoxLayout()
        row1 = QHBoxLayout()
        self.goal_title_input = QLineEdit()
        self.goal_title_input.setPlaceholderText("Goal Title")
        self.goal_status_combo = QComboBox()
        self.goal_status_combo.addItems(["pending", "in_progress", "achieved", "failed"])
        self.goal_target_input = QLineEdit()
        self.goal_target_input.setPlaceholderText("Target Date (e.g. 2026-12-31)")
        row1.addWidget(self.goal_title_input)
        row1.addWidget(self.goal_status_combo)
        row1.addWidget(self.goal_target_input)
        form.addLayout(row1)

        self.goal_desc_input = QTextEdit()
        self.goal_desc_input.setPlaceholderText("Description/Sub-tasks...")
        self.goal_desc_input.setFixedHeight(50)
        form.addWidget(self.goal_desc_input)

        # Action Buttons
        actions = QHBoxLayout()
        self.goal_id_label = QLabel("New Goal (Auto-ID)")
        self.goal_id_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 8pt;")
        
        save_btn = QPushButton("Save Goal")
        save_btn.clicked.connect(self.save_goal)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("delete_btn")
        del_btn.clicked.connect(self.delete_goal)

        actions.addWidget(self.goal_id_label)
        actions.addStretch()
        actions.addWidget(save_btn)
        actions.addWidget(del_btn)
        form.addLayout(actions)
        layout.addLayout(form)

        # Bind row selection
        self.goals_table.itemSelectionChanged.connect(self.autofill_goal)

        return tab

    def autofill_goal(self):
        selected = self.goals_table.selectedItems()
        if len(selected) >= 5:
            self.goal_id_label.setText(selected[0].text())
            self.goal_title_input.setText(selected[1].text())
            self.goal_desc_input.setPlainText(selected[2].text())
            self.goal_status_combo.setCurrentText(selected[3].text())
            self.goal_target_input.setText(selected[4].text())

    def load_goals_data(self):
        self.goals_table.setRowCount(0)
        goals = database.get_goals()
        for row_idx, g in enumerate(goals):
            self.goals_table.insertRow(row_idx)
            self.goals_table.setItem(row_idx, 0, QTableWidgetItem(g["id"]))
            self.goals_table.setItem(row_idx, 1, QTableWidgetItem(g["title"]))
            self.goals_table.setItem(row_idx, 2, QTableWidgetItem(g["description"]))
            self.goals_table.setItem(row_idx, 3, QTableWidgetItem(g["status"]))
            self.goals_table.setItem(row_idx, 4, QTableWidgetItem(g["target_date"] or ""))

    def save_goal(self):
        goal_id = self.goal_id_label.text()
        title = self.goal_title_input.text().strip()
        desc = self.goal_desc_input.toPlainText().strip()
        status = self.goal_status_combo.currentText()
        target = self.goal_target_input.text().strip() or None

        if not title:
            QMessageBox.warning(self, "Invalid Input", "Please enter a goal title, Sir.")
            return

        if "New Goal" in goal_id:
            goal_id = str(uuid.uuid4())[:8]
            database.add_goal(goal_id, title, desc, status, target_date=target)
        else:
            database.update_goal(goal_id, title, desc, status, target_date=target)

        service.sync_goal_to_vector(goal_id, title, desc, status, target_date=target)
        self.load_goals_data()
        
        # Reset Inputs
        self.goal_id_label.setText("New Goal (Auto-ID)")
        self.goal_title_input.clear()
        self.goal_desc_input.clear()
        self.goal_target_input.clear()

    def delete_goal(self):
        goal_id = self.goal_id_label.text()
        if "New Goal" in goal_id:
            QMessageBox.warning(self, "No Goal Selected", "Please select a goal to delete, Sir.")
            return
        database.delete_goal(goal_id)
        service.delete_goal_vector(goal_id)
        self.load_goals_data()
        
        # Reset Inputs
        self.goal_id_label.setText("New Goal (Auto-ID)")
        self.goal_title_input.clear()
        self.goal_desc_input.clear()
        self.goal_target_input.clear()

    # --- RELATIONSHIPS TAB CREATOR ---
    def create_relationships_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Relationships Table
        self.rel_table = QTableWidget(0, 5)
        self.rel_table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Contact Info", "Notes"])
        self.rel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.rel_table)

        # Form Controls
        form = QVBoxLayout()
        row1 = QHBoxLayout()
        self.rel_name_input = QLineEdit()
        self.rel_name_input.setPlaceholderText("Contact Name")
        self.rel_type_combo = QComboBox()
        self.rel_type_combo.addItems(["other", "colleague", "friend", "client", "family"])
        self.rel_contact_input = QLineEdit()
        self.rel_contact_input.setPlaceholderText("Contact Info (e.g. Email/WhatsApp)")
        row1.addWidget(self.rel_name_input)
        row1.addWidget(self.rel_type_combo)
        row1.addWidget(self.rel_contact_input)
        form.addLayout(row1)

        self.rel_notes_input = QTextEdit()
        self.rel_notes_input.setPlaceholderText("Interaction logs, profile details, memory triggers...")
        self.rel_notes_input.setFixedHeight(50)
        form.addWidget(self.rel_notes_input)

        # Action Buttons
        actions = QHBoxLayout()
        self.rel_id_label = QLabel("New Profile (Auto-ID)")
        self.rel_id_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 8pt;")
        
        save_btn = QPushButton("Save Contact")
        save_btn.clicked.connect(self.save_relationship)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("delete_btn")
        del_btn.clicked.connect(self.delete_relationship)

        actions.addWidget(self.rel_id_label)
        actions.addStretch()
        actions.addWidget(save_btn)
        actions.addWidget(del_btn)
        form.addLayout(actions)
        layout.addLayout(form)

        # Bind row selection
        self.rel_table.itemSelectionChanged.connect(self.autofill_relationship)

        return tab

    def autofill_relationship(self):
        selected = self.rel_table.selectedItems()
        if len(selected) >= 5:
            self.rel_id_label.setText(selected[0].text())
            self.rel_name_input.setText(selected[1].text())
            self.rel_type_combo.setCurrentText(selected[2].text())
            self.rel_contact_input.setText(selected[3].text())
            self.rel_notes_input.setPlainText(selected[4].text())

    def load_relationships_data(self):
        self.rel_table.setRowCount(0)
        rels = database.get_relationships()
        for row_idx, r in enumerate(rels):
            self.rel_table.insertRow(row_idx)
            self.rel_table.setItem(row_idx, 0, QTableWidgetItem(r["id"]))
            self.rel_table.setItem(row_idx, 1, QTableWidgetItem(r["name"]))
            self.rel_table.setItem(row_idx, 2, QTableWidgetItem(r["relation_type"]))
            self.rel_table.setItem(row_idx, 3, QTableWidgetItem(r["contact_info"] or ""))
            self.rel_table.setItem(row_idx, 4, QTableWidgetItem(r["notes"] or ""))

    def save_relationship(self):
        rel_id = self.rel_id_label.text()
        name = self.rel_name_input.text().strip()
        rel_type = self.rel_type_combo.currentText()
        contact = self.rel_contact_input.text().strip() or None
        notes = self.rel_notes_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a contact name, Sir.")
            return

        if "New Profile" in rel_id:
            rel_id = str(uuid.uuid4())[:8]
            database.add_relationship(rel_id, name, rel_type, contact, notes)
        else:
            database.update_relationship(rel_id, name, rel_type, contact, notes)

        service.sync_relationship_to_vector(rel_id, name, rel_type, contact, notes)
        self.load_relationships_data()
        
        # Reset Inputs
        self.rel_id_label.setText("New Profile (Auto-ID)")
        self.rel_name_input.clear()
        self.rel_notes_input.clear()
        self.rel_contact_input.clear()

    def delete_relationship(self):
        rel_id = self.rel_id_label.text()
        if "New Profile" in rel_id:
            QMessageBox.warning(self, "No Contact Selected", "Please select a contact to delete, Sir.")
            return
        database.delete_relationship(rel_id)
        service.delete_relationship_vector(rel_id)
        self.load_relationships_data()
        
        # Reset Inputs
        self.rel_id_label.setText("New Profile (Auto-ID)")
        self.rel_name_input.clear()
        self.rel_notes_input.clear()
        self.rel_contact_input.clear()

    # --- TASKS TAB CREATOR ---
    def create_tasks_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tasks Table
        self.tasks_table = QTableWidget(0, 8)
        self.tasks_table.setHorizontalHeaderLabels(["ID", "Title", "Description", "Priority", "Status", "Due Date", "Project ID", "Goal ID"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tasks_table)

        # Form Controls
        form = QVBoxLayout()
        row1 = QHBoxLayout()
        self.task_title_input = QLineEdit()
        self.task_title_input.setPlaceholderText("Task Title")
        self.task_priority_combo = QComboBox()
        self.task_priority_combo.addItems(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.task_priority_combo.setCurrentText("MEDIUM")
        self.task_status_combo = QComboBox()
        self.task_status_combo.addItems(["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"])
        self.task_status_combo.setCurrentText("PENDING")
        self.task_due_input = QLineEdit()
        self.task_due_input.setPlaceholderText("Due Date (e.g. YYYY-MM-DD)")
        
        row1.addWidget(self.task_title_input)
        row1.addWidget(self.task_priority_combo)
        row1.addWidget(self.task_status_combo)
        row1.addWidget(self.task_due_input)
        form.addLayout(row1)

        row2 = QHBoxLayout()
        self.task_project_input = QLineEdit()
        self.task_project_input.setPlaceholderText("Linked Project ID (Optional)")
        self.task_goal_input = QLineEdit()
        self.task_goal_input.setPlaceholderText("Linked Goal ID (Optional)")
        row2.addWidget(self.task_project_input)
        row2.addWidget(self.task_goal_input)
        form.addLayout(row2)

        self.task_desc_input = QTextEdit()
        self.task_desc_input.setPlaceholderText("Description/Sub-tasks...")
        self.task_desc_input.setFixedHeight(50)
        form.addWidget(self.task_desc_input)

        # Action Buttons
        actions = QHBoxLayout()
        self.task_id_label = QLabel("New Task (Auto-ID)")
        self.task_id_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 8pt;")
        
        save_btn = QPushButton("Save Task")
        save_btn.clicked.connect(self.save_task)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("delete_btn")
        del_btn.clicked.connect(self.delete_task)

        actions.addWidget(self.task_id_label)
        actions.addStretch()
        actions.addWidget(save_btn)
        actions.addWidget(del_btn)
        form.addLayout(actions)
        layout.addLayout(form)

        # Bind row selection
        self.tasks_table.itemSelectionChanged.connect(self.autofill_task)

        return tab

    def autofill_task(self):
        selected = self.tasks_table.selectedItems()
        if len(selected) >= 8:
            self.task_id_label.setText(selected[0].text())
            self.task_title_input.setText(selected[1].text())
            self.task_desc_input.setPlainText(selected[2].text())
            self.task_priority_combo.setCurrentText(selected[3].text())
            self.task_status_combo.setCurrentText(selected[4].text())
            self.task_due_input.setText(selected[5].text())
            self.task_project_input.setText(selected[6].text())
            self.task_goal_input.setText(selected[7].text())

    def load_tasks_data(self):
        self.tasks_table.setRowCount(0)
        tasks = database.get_tasks()
        for row_idx, t in enumerate(tasks):
            self.tasks_table.insertRow(row_idx)
            self.tasks_table.setItem(row_idx, 0, QTableWidgetItem(t["id"]))
            self.tasks_table.setItem(row_idx, 1, QTableWidgetItem(t["title"]))
            self.tasks_table.setItem(row_idx, 2, QTableWidgetItem(t["description"] or ""))
            self.tasks_table.setItem(row_idx, 3, QTableWidgetItem(t["priority"]))
            self.tasks_table.setItem(row_idx, 4, QTableWidgetItem(t["status"]))
            self.tasks_table.setItem(row_idx, 5, QTableWidgetItem(t["due_date"] or ""))
            self.tasks_table.setItem(row_idx, 6, QTableWidgetItem(t["project_id"] or ""))
            self.tasks_table.setItem(row_idx, 7, QTableWidgetItem(t["goal_id"] or ""))

    def save_task(self):
        task_id = self.task_id_label.text()
        title = self.task_title_input.text().strip()
        desc = self.task_desc_input.toPlainText().strip() or None
        priority = self.task_priority_combo.currentText()
        status = self.task_status_combo.currentText()
        due = self.task_due_input.text().strip() or None
        project = self.task_project_input.text().strip() or None
        goal = self.task_goal_input.text().strip() or None

        if not title:
            QMessageBox.warning(self, "Invalid Input", "Please enter a task title, Sir.")
            return

        if "New Task" in task_id:
            task_id = str(uuid.uuid4())[:8]
            database.add_task(task_id, title, desc, priority, status, due, project, goal)
        else:
            database.update_task(task_id, title, desc, priority, status, due, project, goal)

        self.load_tasks_data()
        
        # Reset Inputs
        self.task_id_label.setText("New Task (Auto-ID)")
        self.task_title_input.clear()
        self.task_desc_input.clear()
        self.task_due_input.clear()
        self.task_project_input.clear()
        self.task_goal_input.clear()

    def delete_task(self):
        task_id = self.task_id_label.text()
        if "New Task" in task_id:
            QMessageBox.warning(self, "No Task Selected", "Please select a task to delete, Sir.")
            return
        database.delete_task(task_id)
        self.load_tasks_data()
        
        # Reset Inputs
        self.task_id_label.setText("New Task (Auto-ID)")
        self.task_title_input.clear()
        self.task_desc_input.clear()
        self.task_due_input.clear()
        self.task_project_input.clear()
        self.task_goal_input.clear()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = AloneMemoryWindow()
    window.show()
    sys.exit(app.exec_())
