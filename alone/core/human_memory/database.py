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
            status TEXT CHECK(status IN ('pending', 'in_progress', 'achieved', 'failed')) DEFAULT 'pending',
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
            relation_type TEXT CHECK(relation_type IN ('colleague', 'friend', 'client', 'family', 'other')) DEFAULT 'other',
            contact_info TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Ensure phase and priority columns exist for older databases
        cursor.execute("PRAGMA table_info(projects)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "phase" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN phase TEXT DEFAULT ''")
        if "priority" not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN priority TEXT DEFAULT ''")

        conn.commit()
        conn.close()

# Initialize database tables on load
init_db()

# --- User Profile CRUD ---
def get_profile():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_profile")
        rows = cursor.fetchall()
        conn.close()
        res = {row["key"]: row["value"] for row in rows}
        for k, v in res.items():
            print(f"[MEMORY RETRIEVE] key='{k}', value='{v}'")
        return res

def set_profile_field(key, value):
    key_clean = key.lower().strip()
    with db_lock:
        conn = get_connection()
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
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_profile WHERE key = ?", (key.lower().strip(),))
        conn.commit()
        conn.close()

# --- Preferences CRUD ---
def get_preferences(category=None):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        if category:
            cursor.execute("SELECT key, value, category FROM preferences WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT key, value, category FROM preferences")
        rows = cursor.fetchall()
        conn.close()
        return {row["key"]: {"value": row["value"], "category": row["category"]} for row in rows}

def set_preference(key, value, category="general"):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO preferences (key, value, category, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=excluded.updated_at
        """, (key.lower().strip(), value, category, now))
        conn.commit()
        conn.close()

def delete_preference(key):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM preferences WHERE key = ?", (key.lower().strip(),))
        conn.commit()
        conn.close()

# --- Projects CRUD ---
def get_projects(status=None):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT id, name, description, status, phase, priority, created_at, updated_at FROM projects WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT id, name, description, status, phase, priority, created_at, updated_at FROM projects")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

def add_project(project_id, name, description, status="active", phase="", priority=""):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO projects (id, name, description, status, phase, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, name, description, status, phase, priority, now, now))
        conn.commit()
        conn.close()
        print(f"[MEMORY SAVE] project='{name}', id='{project_id}'")

def update_project(project_id, name, description, status, phase=None, priority=None):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
        conn.commit()
        conn.close()
        print(f"[MEMORY UPDATE] project='{name}', id='{project_id}'")

def delete_project(project_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()

# --- Goals CRUD ---
def get_goals(status=None):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT id, title, description, status, parent_goal_id, target_date, created_at, updated_at FROM goals WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT id, title, description, status, parent_goal_id, target_date, created_at, updated_at FROM goals")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

def add_goal(goal_id, title, description, status="pending", parent_goal_id=None, target_date=None):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO goals (id, title, description, status, parent_goal_id, target_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (goal_id, title, description, status, parent_goal_id, target_date, now, now))
        conn.commit()
        conn.close()
        print(f"[MEMORY SAVE] goal='{title}', id='{goal_id}'")

def update_goal(goal_id, title, description, status, parent_goal_id=None, target_date=None):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        UPDATE goals SET title = ?, description = ?, status = ?, parent_goal_id = ?, target_date = ?, updated_at = ? WHERE id = ?
        """, (title, description, status, parent_goal_id, target_date, now, goal_id))
        conn.commit()
        conn.close()
        print(f"[MEMORY UPDATE] goal='{title}', id='{goal_id}'")

def delete_goal(goal_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()

# --- Relationships CRUD ---
def get_relationships():
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, relation_type, contact_info, notes, created_at, updated_at FROM relationships")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

def add_relationship(rel_id, name, relation_type, contact_info, notes):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO relationships (id, name, relation_type, contact_info, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (rel_id, name, relation_type, contact_info, notes, now, now))
        conn.commit()
        conn.close()
        print(f"[MEMORY SAVE] contact='{name}', id='{rel_id}'")

def update_relationship(rel_id, name, relation_type, contact_info, notes):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        UPDATE relationships SET name = ?, relation_type = ?, contact_info = ?, notes = ?, updated_at = ? WHERE id = ?
        """, (name, relation_type, contact_info, notes, now, rel_id))
        conn.commit()
        conn.close()
        print(f"[MEMORY UPDATE] contact='{name}', id='{rel_id}'")

def delete_relationship(rel_id):
    with db_lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relationships WHERE id = ?", (rel_id,))
        conn.commit()
        conn.close()
