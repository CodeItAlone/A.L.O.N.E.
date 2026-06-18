import os
import sqlite3
import threading
from datetime import datetime

# Path to the human memory database file
DB_DIR = os.path.expanduser("~/.alone")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "human_memory.db")

# Thread lock to prevent concurrent write locks in SQLite
db_lock = threading.Lock()

def get_connection():
    """Establishes and returns a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates tables if they do not exist."""
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. User Profile Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # 2. Preferences Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # 3. Projects Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT CHECK(status IN ('active', 'completed', 'paused', 'archived')) DEFAULT 'active',
                phase TEXT DEFAULT '',
                priority TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # 4. Goals Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT '',
                priority TEXT DEFAULT '',
                status TEXT CHECK(status IN ('pending', 'in_progress', 'achieved', 'failed')) DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                parent_goal_id TEXT REFERENCES goals(id) ON DELETE CASCADE,
                target_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # 5. Relationships Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                relation_type TEXT DEFAULT 'other',
                contact_info TEXT,
                description TEXT,
                preferences TEXT,
                notes TEXT,
                importance_score INTEGER DEFAULT 20,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 6. Project-Goal Linking Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_goals (
                project_id TEXT,
                goal_id TEXT,
                PRIMARY KEY (project_id, goal_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
            );
            """)

            # 7. Memory Change Log Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                action TEXT NOT NULL,
                original_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # Ensure phase, priority, is_deleted columns exist for older databases
            cursor.execute("PRAGMA table_info(projects)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "phase" not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN phase TEXT DEFAULT ''")
            if "priority" not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN priority TEXT DEFAULT ''")
            if "is_deleted" not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN is_deleted INTEGER DEFAULT 0")

            # Ensure category, priority, progress, is_deleted columns exist for older goals databases
            cursor.execute("PRAGMA table_info(goals)")
            goal_columns = [row["name"] for row in cursor.fetchall()]
            if "category" not in goal_columns:
                cursor.execute("ALTER TABLE goals ADD COLUMN category TEXT DEFAULT ''")
            if "priority" not in goal_columns:
                cursor.execute("ALTER TABLE goals ADD COLUMN priority TEXT DEFAULT ''")
            if "progress" not in goal_columns:
                cursor.execute("ALTER TABLE goals ADD COLUMN progress INTEGER DEFAULT 0")
            if "is_deleted" not in goal_columns:
                cursor.execute("ALTER TABLE goals ADD COLUMN is_deleted INTEGER DEFAULT 0")

            # Migrate relationships table to drop CHECK constraint and add new columns
            cursor.execute("PRAGMA table_info(relationships)")
            rel_columns = [row["name"] for row in cursor.fetchall()]
            if rel_columns and ("description" not in rel_columns or "preferences" not in rel_columns or "importance_score" not in rel_columns):
                # Drop old CHECK constraint by recreating table
                cursor.execute("ALTER TABLE relationships RENAME TO temp_relationships")
                cursor.execute("""
                CREATE TABLE relationships (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    relation_type TEXT DEFAULT 'other',
                    contact_info TEXT,
                    description TEXT,
                    preferences TEXT,
                    notes TEXT,
                    importance_score INTEGER DEFAULT 20,
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                # Copy data from temp_relationships
                cursor.execute("""
                INSERT INTO relationships (id, name, relation_type, contact_info, notes, created_at, updated_at)
                SELECT id, name, relation_type, contact_info, notes, created_at, updated_at FROM temp_relationships
                """)
                cursor.execute("DROP TABLE temp_relationships")
            else:
                # Ensure is_deleted column exists for relationships if table recreated previously
                if "is_deleted" not in rel_columns:
                    cursor.execute("ALTER TABLE relationships ADD COLUMN is_deleted INTEGER DEFAULT 0")

            # 8. Tasks Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                status TEXT DEFAULT 'PENDING',
                due_date TEXT,
                project_id TEXT,
                goal_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
            );
            """)

            # 9. Calendar Events Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                attendees TEXT,
                event_type TEXT,
                status TEXT CHECK(status IN ('scheduled', 'cancelled')) DEFAULT 'scheduled',
                created_at TEXT,
                updated_at TEXT
            );
            """)

            conn.commit()
        finally:
            conn.close()

# Initialize database tables on load
init_db()

# --- User Profile CRUD ---
def get_profile():
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_profile")
            rows = cursor.fetchall()
            res = {row["key"]: row["value"] for row in rows}
            for k, v in res.items():
                print(f"[MEMORY RETRIEVE] key='{k}', value='{v}'")
            return res
        finally:
            conn.close()

def set_profile_field(key, value):
    key_clean = key.lower().strip()
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_profile WHERE key = ?", (key_clean,))
            row = cursor.fetchone()
            exists = row is not None
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO user_profile (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """, (key_clean, value, now))
            conn.commit()
        finally:
            conn.close()
        
        if exists:
            print(f"[MEMORY UPDATE] key='{key_clean}', value='{value}'")
        else:
            print(f"[MEMORY SAVE] key='{key_clean}', value='{value}'")
            
    # Verify profile memory is actually persisted before responding
    verified_prof = get_profile()
    if verified_prof.get(key_clean) == value:
        print("[Profile Memory Validation Passed]")
    else:
        print("[Profile Memory Validation Failed]")

def delete_profile_field(key):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profile WHERE key = ?", (key.lower().strip(),))
            conn.commit()
        finally:
            conn.close()

# --- Preferences CRUD ---
def get_preferences(category=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if category:
                cursor.execute("SELECT key, value, category FROM preferences WHERE category = ?", (category,))
            else:
                cursor.execute("SELECT key, value, category FROM preferences")
            rows = cursor.fetchall()
            return {row["key"]: {"value": row["value"], "category": row["category"]} for row in rows}
        finally:
            conn.close()

def set_preference(key, value, category="general"):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO preferences (key, value, category, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=excluded.updated_at
            """, (key.lower().strip(), value, category, now))
            conn.commit()
        finally:
            conn.close()

def delete_preference(key):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM preferences WHERE key = ?", (key.lower().strip(),))
            conn.commit()
        finally:
            conn.close()

# --- Projects CRUD ---
def get_projects(status=None, include_deleted=False):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if status:
                if include_deleted:
                    cursor.execute("SELECT id, name, description, status, phase, priority, created_at, updated_at FROM projects WHERE status = ?", (status,))
                else:
                    cursor.execute("SELECT id, name, description, status, phase, priority, created_at, updated_at FROM projects WHERE status = ? AND is_deleted = 0", (status,))
            else:
                if include_deleted:
                    cursor.execute("SELECT id, name, description, status, phase, priority, created_at, updated_at FROM projects")
                else:
                    cursor.execute("SELECT id, name, description, status, phase, priority, created_at, updated_at FROM projects WHERE is_deleted = 0")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

def add_project(project_id, name, description, status="active", phase="", priority=""):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO projects (id, name, description, status, phase, priority, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, name, description, status, phase, priority, now, now))
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, ("project", project_id, "create", f"Name: {name}, Desc: {description}, Status: {status}", now))
            conn.commit()
        finally:
            conn.close()
        print(f"[MEMORY SAVE] project='{name}', id='{project_id}'")

def update_project(project_id, name, description, status, phase=None, priority=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get original
            cursor.execute("SELECT name, description, status, phase, priority FROM projects WHERE id = ?", (project_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            query = "UPDATE projects SET name = ?, description = ?, status = ?, updated_at = ?"
            params = [name, description, status, now]
            
            if phase is not None:
                query += ", phase = ?"
                params.append(phase)
            if priority is not None:
                query += ", priority = ?"
                params.append(priority)
                
            query += " WHERE id = ?"
            params.append(project_id)
            
            cursor.execute(query, tuple(params))
            
            # Log to change log
            new_val = f"Name: {name}, Desc: {description}, Status: {status}, Phase: {phase}, Priority: {priority}"
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("project", project_id, "update", str(orig_val), new_val, now))
            
            conn.commit()
        finally:
            conn.close()
        print(f"[MEMORY UPDATE] project='{name}', id='{project_id}'")

def delete_project(project_id):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("SELECT name, description, status FROM projects WHERE id = ?", (project_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("UPDATE projects SET is_deleted = 1 WHERE id = ?", (project_id,))
            
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("project", project_id, "delete", str(orig_val), "is_deleted=1", now))
            
            conn.commit()
        finally:
            conn.close()

# --- Goals CRUD ---
def get_goals(status=None, include_deleted=False):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if status:
                if include_deleted:
                    cursor.execute("SELECT id, title, description, category, priority, status, progress, parent_goal_id, target_date, created_at, updated_at FROM goals WHERE status = ?", (status,))
                else:
                    cursor.execute("SELECT id, title, description, category, priority, status, progress, parent_goal_id, target_date, created_at, updated_at FROM goals WHERE status = ? AND is_deleted = 0", (status,))
            else:
                if include_deleted:
                    cursor.execute("SELECT id, title, description, category, priority, status, progress, parent_goal_id, target_date, created_at, updated_at FROM goals")
                else:
                    cursor.execute("SELECT id, title, description, category, priority, status, progress, parent_goal_id, target_date, created_at, updated_at FROM goals WHERE is_deleted = 0")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

def add_goal(goal_id, title, description, status="pending", parent_goal_id=None, target_date=None, category="", priority="", progress=0):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO goals (id, title, description, category, priority, status, progress, parent_goal_id, target_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (goal_id, title, description, category, priority, status, progress, parent_goal_id, target_date, now, now))
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, ("goal", goal_id, "create", f"Title: {title}, Desc: {description}, Status: {status}, Progress: {progress}%", now))
            conn.commit()
        finally:
            conn.close()
        print(f"[MEMORY SAVE] goal='{title}', id='{goal_id}'")

def update_goal(goal_id, title, description, status, parent_goal_id=None, target_date=None, category=None, priority=None, progress=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get original
            cursor.execute("SELECT title, description, status, progress, category, priority, target_date FROM goals WHERE id = ?", (goal_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            query = "UPDATE goals SET title = ?, description = ?, status = ?, parent_goal_id = ?, target_date = ?, updated_at = ?"
            params = [title, description, status, parent_goal_id, target_date, now]
            
            if category is not None:
                query += ", category = ?"
                params.append(category)
            if priority is not None:
                query += ", priority = ?"
                params.append(priority)
            if progress is not None:
                query += ", progress = ?"
                params.append(progress)
                
            query += " WHERE id = ?"
            params.append(goal_id)
            
            cursor.execute(query, tuple(params))
            
            # Log to change log
            new_val = f"Title: {title}, Desc: {description}, Status: {status}, Progress: {progress}%, Category: {category}, Priority: {priority}, Target Date: {target_date}"
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("goal", goal_id, "update", str(orig_val), new_val, now))
            
            conn.commit()
        finally:
            conn.close()
        print(f"[MEMORY UPDATE] goal='{title}', id='{goal_id}'")

def delete_goal(goal_id):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("SELECT title, description, status FROM goals WHERE id = ?", (goal_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("UPDATE goals SET is_deleted = 1 WHERE id = ?", (goal_id,))
            
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("goal", goal_id, "delete", str(orig_val), "is_deleted=1", now))
            
            conn.commit()
        finally:
            conn.close()

# --- Relationships CRUD ---
def get_relationships(include_deleted=False):
    print(f"[RELATIONSHIP RETRIEVAL] Database Path: {DB_PATH}")
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            if include_deleted:
                cursor.execute("SELECT id, name, relation_type, contact_info, description, preferences, notes, importance_score, created_at, updated_at FROM relationships")
            else:
                cursor.execute("SELECT id, name, relation_type, contact_info, description, preferences, notes, importance_score, created_at, updated_at FROM relationships WHERE is_deleted = 0")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

def add_relationship(rel_id, name, relation_type, contact_info=None, notes=None, description=None, preferences=None, importance_score=20):
    print(f"[RELATIONSHIP SAVE] Database Path: {DB_PATH}")
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO relationships (id, name, relation_type, contact_info, description, preferences, notes, importance_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rel_id, name, relation_type, contact_info, description, preferences, notes, importance_score, now, now))
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, ("relationship", rel_id, "create", f"Name: {name}, Type: {relation_type}", now))
            conn.commit()
        finally:
            conn.close()
        print(f"[MEMORY SAVE] contact='{name}', id='{rel_id}'")

def update_relationship(rel_id, name, relation_type, contact_info=None, notes=None, description=None, preferences=None, importance_score=None):
    print(f"[RELATIONSHIP UPDATE] Database Path: {DB_PATH}")
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get original
            cursor.execute("SELECT name, relation_type, contact_info, notes, description, preferences, importance_score FROM relationships WHERE id = ?", (rel_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            query = "UPDATE relationships SET name = ?, relation_type = ?, notes = ?, updated_at = ?"
            params = [name, relation_type, notes, now]
            
            if contact_info is not None:
                query += ", contact_info = ?"
                params.append(contact_info)
            if description is not None:
                query += ", description = ?"
                params.append(description)
            if preferences is not None:
                query += ", preferences = ?"
                params.append(preferences)
            if importance_score is not None:
                query += ", importance_score = ?"
                params.append(importance_score)
                
            query += " WHERE id = ?"
            params.append(rel_id)
            
            cursor.execute(query, tuple(params))
            
            # Log to change log
            new_val = f"Name: {name}, Type: {relation_type}, Contact: {contact_info}, Notes: {notes}, Desc: {description}, Pref: {preferences}, Importance: {importance_score}"
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("relationship", rel_id, "update", str(orig_val), new_val, now))
            
            conn.commit()
        finally:
            conn.close()
        print(f"[MEMORY UPDATE] contact='{name}', id='{rel_id}'")

def delete_relationship(rel_id):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("SELECT name, relation_type FROM relationships WHERE id = ?", (rel_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("UPDATE relationships SET is_deleted = 1 WHERE id = ?", (rel_id,))
            
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("relationship", rel_id, "delete", str(orig_val), "is_deleted=1", now))
            
            conn.commit()
        finally:
            conn.close()

# --- Tasks CRUD ---
def get_tasks(status=None, priority=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT id, title, description, priority, status, due_date, project_id, goal_id, created_at, updated_at FROM tasks WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if priority:
                query += " AND priority = ?"
                params.append(priority)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

def add_task(task_id, title, description, priority="MEDIUM", status="PENDING", due_date=None, project_id=None, goal_id=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO tasks (id, title, description, priority, status, due_date, project_id, goal_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task_id, title, description, priority, status, due_date, project_id, goal_id, now, now))
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, ("task", task_id, "create", f"Title: {title}, Priority: {priority}, Status: {status}", now))
            conn.commit()
        finally:
            conn.close()
        print(f"[TASK CREATE] task='{title}', id='{task_id}'")

def update_task(task_id, title, description, priority, status, due_date=None, project_id=None, goal_id=None):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get original
            cursor.execute("SELECT title, description, priority, status, due_date, project_id, goal_id FROM tasks WHERE id = ?", (task_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("""
            UPDATE tasks
            SET title = ?, description = ?, priority = ?, status = ?, due_date = ?, project_id = ?, goal_id = ?, updated_at = ?
            WHERE id = ?
            """, (title, description, priority, status, due_date, project_id, goal_id, now, task_id))
            
            # Log to change log
            new_val = f"Title: {title}, Priority: {priority}, Status: {status}, Due: {due_date}, Proj: {project_id}, Goal: {goal_id}"
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("task", task_id, "update", str(orig_val), new_val, now))
            conn.commit()
        finally:
            conn.close()
        print(f"[TASK UPDATE] task='{title}', id='{task_id}'")

def delete_task(task_id):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("SELECT title, status FROM tasks WHERE id = ?", (task_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("task", task_id, "delete", str(orig_val), "deleted", now))
            conn.commit()
        finally:
            conn.close()
        print(f"[TASK DELETE] id='{task_id}'")

# --- Calendar Events CRUD ---
def get_calendar_events():
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, description, start_time, end_time, location, attendees, event_type, status, created_at, updated_at FROM calendar_events")
            rows = cursor.fetchall()
            events = [dict(row) for row in rows]
            print(f"[CALENDAR QUERY] count={len(events)}")
            return events
        finally:
            conn.close()

def add_calendar_event(event_id, title, description, start_time, end_time, location="", attendees="[]", event_type="meeting", status="scheduled"):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO calendar_events (id, title, description, start_time, end_time, location, attendees, event_type, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, title, description, start_time, end_time, location, attendees, event_type, status, now, now))
            
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, ("calendar", event_id, "create", f"Title: {title}, Start: {start_time}, End: {end_time}", now))
            
            conn.commit()
        finally:
            conn.close()
        print(f"[CALENDAR CREATE] event='{title}', id='{event_id}'")

def update_calendar_event(event_id, title, description, start_time, end_time, location, attendees, event_type, status):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get original
            cursor.execute("SELECT title, start_time, end_time, status FROM calendar_events WHERE id = ?", (event_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("""
            UPDATE calendar_events
            SET title = ?, description = ?, start_time = ?, end_time = ?, location = ?, attendees = ?, event_type = ?, status = ?, updated_at = ?
            WHERE id = ?
            """, (title, description, start_time, end_time, location, attendees, event_type, status, now, event_id))
            
            # Log to change log
            new_val = f"Title: {title}, Start: {start_time}, End: {end_time}, Status: {status}"
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("calendar", event_id, "update", str(orig_val), new_val, now))
            
            conn.commit()
        finally:
            conn.close()
        print(f"[CALENDAR UPDATE] event='{title}', id='{event_id}'")

def delete_calendar_event(event_id):
    with db_lock:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("SELECT title, status FROM calendar_events WHERE id = ?", (event_id,))
            orig_row = cursor.fetchone()
            orig_val = dict(orig_row) if orig_row else None
            
            cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
            
            # Log to change log
            cursor.execute("""
            INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ("calendar", event_id, "delete", str(orig_val), "deleted", now))
            conn.commit()
        finally:
            conn.close()
        print(f"[CALENDAR DELETE] id='{event_id}'")
