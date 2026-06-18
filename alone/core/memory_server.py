import http.server
import socketserver
import json
import os
import urllib.parse
import threading
from datetime import datetime
from core.human_memory import database
from core.preferences_service import preference_service

PORT = 8080
HTML_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "templates", "index.html")

class MemoryHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default request logging to keep console clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # 1. UI Routes
        if path in ["/memory", "/memory/", "/memory/explorer", "/memory/goals", "/memory/relationships", "/memory/profile", "/memory/preferences", "/memory/projects", "/memory/tasks", "/memory/calendar"]:
            self.serve_html()
            return

        # 2. API: GET /api/memory
        if path == "/api/memory":
            self.handle_get_memory()
            return

        # 3. API: GET /api/memory/search
        if path == "/api/memory/search":
            self.handle_search_memory(query_params)
            return

        # 4. API: GET /api/tasks
        if path == "/api/tasks":
            self.handle_get_tasks()
            return

        # 5. API: GET /api/calendar
        if path == "/api/calendar":
            self.handle_get_calendar()
            return

        # Fallback
        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read JSON body
        content_length = int(self.headers.get('Content-Length', 0))
        body_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            body = json.loads(body_data)
        except Exception:
            body = {}

        # POST /api/tasks
        if path == "/api/tasks":
            self.handle_create_task(body)
            return

        # POST /api/calendar
        if path == "/api/calendar":
            self.handle_create_calendar(body)
            return

        # POST /api/memory/restore/{type}/{id}
        if path.startswith("/api/memory/restore/"):
            parts = path.split("/")
            if len(parts) >= 6:
                m_type = parts[4]
                m_id = parts[5]
                self.handle_restore_memory(m_type, m_id)
                return

        # POST /api/memory/{type}
        if path.startswith("/api/memory/"):
            parts = path.split("/")
            if len(parts) >= 4:
                m_type = parts[3]
                self.handle_create_memory(m_type, body)
                return

        self.send_error(404, "Not Found")

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get('Content-Length', 0))
        body_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            body = json.loads(body_data)
        except Exception:
            body = {}

        # PUT /api/tasks/{id}
        if path.startswith("/api/tasks/"):
            parts = path.split("/")
            if len(parts) >= 4:
                t_id = parts[3]
                self.handle_update_task(t_id, body)
                return

        # PUT /api/calendar/{id}
        if path.startswith("/api/calendar/"):
            parts = path.split("/")
            if len(parts) >= 4:
                c_id = parts[3]
                self.handle_update_calendar(c_id, body)
                return

        # PUT /api/memory/{type}/{id}
        if path.startswith("/api/memory/"):
            parts = path.split("/")
            if len(parts) >= 5:
                m_type = parts[3]
                m_id = parts[4]
                self.handle_update_memory(m_type, m_id, body)
                return

        self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # DELETE /api/tasks/{id}
        if path.startswith("/api/tasks/"):
            parts = path.split("/")
            if len(parts) >= 4:
                t_id = parts[3]
                self.handle_delete_task(t_id)
                return

        # DELETE /api/calendar/{id}
        if path.startswith("/api/calendar/"):
            parts = path.split("/")
            if len(parts) >= 4:
                c_id = parts[3]
                self.handle_delete_calendar(c_id)
                return

        # DELETE /api/memory/{type}/{id}
        if path.startswith("/api/memory/"):
            parts = path.split("/")
            if len(parts) >= 5:
                m_type = parts[3]
                m_id = parts[4]
                self.handle_delete_memory(m_type, m_id)
                return

        self.send_error(404, "Not Found")

    def serve_html(self):
        if not os.path.exists(HTML_FILE_PATH):
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Templates directory or index.html missing.")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        with open(HTML_FILE_PATH, "rb") as f:
            self.wfile.write(f.read())

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def handle_get_memory(self):
        try:
            identity_data = database.get_profile()
            preferences_raw = database.get_preferences()
            preferences_data = {k: v["value"] for k, v in preferences_raw.items()}
            
            goals = database.get_goals(include_deleted=True)
            relationships = database.get_relationships(include_deleted=True)
            projects = database.get_projects(include_deleted=True)
            tasks = database.get_tasks()
            calendar_events = database.get_calendar_events()

            # Change log
            with database.db_lock:
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id, memory_type, memory_id, action, original_value, new_value, timestamp FROM memory_change_log ORDER BY timestamp DESC")
                change_log = [dict(row) for row in cursor.fetchall()]
                conn.close()

            # Compile stats
            active_goals = sum(1 for g in goals if g.get("is_deleted") == 0)
            active_rels = sum(1 for r in relationships if r.get("is_deleted") == 0)
            active_projs = sum(1 for p in projects if p.get("is_deleted") == 0)
            active_tasks = len(tasks)
            active_cal = len(calendar_events)
            total_active = len(identity_data) + len(preferences_data) + active_goals + active_rels + active_projs + active_tasks + active_cal

            # Most active memory type based on logs
            type_counts = {}
            for log in change_log:
                t = log.get("memory_type")
                type_counts[t] = type_counts.get(t, 0) + 1
            most_active = max(type_counts, key=type_counts.get) if type_counts else "None"

            last_updated = change_log[0]["timestamp"] if change_log else "Never"

            stats = {
                "total_memories": total_active,
                "goals_count": active_goals,
                "relationships_count": active_rels,
                "projects_count": active_projs,
                "tasks_count": active_tasks,
                "calendar_count": active_cal,
                "identity_count": len(identity_data),
                "preferences_count": len(preferences_data),
                "most_active_type": most_active,
                "last_updated": last_updated
            }

            self.send_json({
                "identity": [{"key": k, "value": v} for k, v in identity_data.items()],
                "preferences": [{"key": k, "value": v} for k, v in preferences_data.items()],
                "goals": goals,
                "relationships": relationships,
                "projects": projects,
                "tasks": tasks,
                "calendar": calendar_events,
                "change_log": change_log,
                "stats": stats
            })
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_get_tasks(self):
        try:
            tasks = database.get_tasks()
            self.send_json(tasks)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_create_task(self, body):
        import uuid
        try:
            m_id = str(uuid.uuid4())[:8]
            title = body.get("title")
            desc = body.get("description", "")
            priority = body.get("priority", "MEDIUM")
            status = body.get("status", "PENDING")
            due_date = body.get("due_date")
            project_id = body.get("project_id")
            goal_id = body.get("goal_id")
            
            database.add_task(m_id, title, desc, priority, status, due_date, project_id, goal_id)
            self.send_json({"success": True, "id": m_id})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_update_task(self, t_id, body):
        try:
            title = body.get("title")
            desc = body.get("description", "")
            priority = body.get("priority", "MEDIUM")
            status = body.get("status", "PENDING")
            due_date = body.get("due_date")
            project_id = body.get("project_id")
            goal_id = body.get("goal_id")
            
            database.update_task(t_id, title, desc, priority, status, due_date, project_id, goal_id)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_delete_task(self, t_id):
        try:
            database.delete_task(t_id)
            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_get_calendar(self):
        try:
            events = database.get_calendar_events()
            self.send_json(events)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_create_calendar(self, body):
        from core.human_memory.calendar_controller import calendar_controller
        try:
            title = body.get("title")
            start = body.get("start_time") or body.get("startTime")
            end = body.get("end_time") or body.get("endTime")
            desc = body.get("description", "")
            location = body.get("location", "")
            attendees = body.get("attendees", [])
            event_type = body.get("event_type") or body.get("eventType", "meeting")
            status = body.get("status", "scheduled")
            force = body.get("force", False)
            
            res = calendar_controller.create_event(
                title=title,
                start_time=start,
                end_time=end,
                description=desc,
                location=location,
                attendees=attendees,
                event_type=event_type,
                status=status,
                force=force
            )
            self.send_json(res)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_update_calendar(self, c_id, body):
        from core.human_memory.calendar_controller import calendar_controller
        try:
            title = body.get("title")
            start = body.get("start_time") or body.get("startTime")
            end = body.get("end_time") or body.get("endTime")
            desc = body.get("description", "")
            location = body.get("location", "")
            attendees = body.get("attendees", [])
            event_type = body.get("event_type") or body.get("eventType", "meeting")
            status = body.get("status", "scheduled")
            
            res = calendar_controller.update_event(
                event_id=c_id,
                title=title,
                start_time=start,
                end_time=end,
                description=desc,
                location=location,
                attendees=attendees,
                event_type=event_type,
                status=status
            )
            self.send_json(res)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_delete_calendar(self, c_id):
        from core.human_memory.calendar_controller import calendar_controller
        try:
            res = calendar_controller.delete_event(c_id)
            self.send_json(res)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_search_memory(self, query_params):
        q = query_params.get("q", [""])[0]
        try:
            from core.memory_retrieval import memory_retrieval_service
            results = memory_retrieval_service.search(q)
            self.send_json({"results": results})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_create_memory(self, m_type, body):
        import uuid
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            m_id = str(uuid.uuid4())[:8]

            if m_type == "goal":
                title = body.get("title")
                desc = body.get("description", "")
                status = body.get("status", "pending")
                progress = int(body.get("progress", 0))
                target = body.get("target_date")
                database.add_goal(m_id, title, desc, status, target_date=target, progress=progress)
                from core.human_memory import service as hm_service
                hm_service.sync_goal_to_vector(m_id, title, desc, status, target_date=target, progress=progress)
            elif m_type == "relationship":
                name = body.get("name")
                relation = body.get("relation_type", "other")
                contact = body.get("contact_info", "")
                notes = body.get("notes", "")
                database.add_relationship(m_id, name, relation, contact_info=contact, notes=notes)
                from core.human_memory import service as hm_service
                hm_service.sync_relationship_to_vector(m_id, name, relation, contact, notes)
            elif m_type == "project":
                name = body.get("name")
                desc = body.get("description", "")
                status = body.get("status", "active")
                database.add_project(m_id, name, desc, status)
                from core.human_memory import service as hm_service
                hm_service.sync_project_to_vector(m_id, name, desc, status)
            elif m_type == "identity":
                key = body.get("key")
                val = body.get("value")
                database.set_profile_field(key, val)
                m_id = key
            elif m_type == "preference":
                key = body.get("key")
                val = body.get("value")
                preference_service.save_preference(key, val)
                m_id = key
            else:
                self.send_json({"success": False, "error": f"Invalid type {m_type}"}, 400)
                return

            self.send_json({"success": True, "id": m_id})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_update_memory(self, m_type, m_id, body):
        try:
            if m_type == "goal":
                title = body.get("title")
                desc = body.get("description", "")
                status = body.get("status", "pending")
                progress = int(body.get("progress", 0))
                target = body.get("target_date")
                database.update_goal(m_id, title, desc, status, target_date=target, progress=progress)
                from core.human_memory import service as hm_service
                hm_service.sync_goal_to_vector(m_id, title, desc, status, target_date=target, progress=progress)
            elif m_type == "relationship":
                name = body.get("name")
                relation = body.get("relation_type", "other")
                contact = body.get("contact_info", "")
                notes = body.get("notes", "")
                database.update_relationship(m_id, name, relation, contact_info=contact, notes=notes)
                from core.human_memory import service as hm_service
                hm_service.sync_relationship_to_vector(m_id, name, relation, contact, notes)
            elif m_type == "project":
                name = body.get("name")
                desc = body.get("description", "")
                status = body.get("status", "active")
                database.update_project(m_id, name, desc, status)
                from core.human_memory import service as hm_service
                hm_service.sync_project_to_vector(m_id, name, desc, status)
            elif m_type == "identity":
                # key is m_id
                val = body.get("value")
                # Fetch original for log
                orig = database.get_profile().get(m_id)
                database.set_profile_field(m_id, val)
                # Log edit
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with database.db_lock:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, ("identity", m_id, "update", str(orig), val, now))
                    conn.commit()
                    conn.close()
            elif m_type == "preference":
                val = body.get("value")
                orig = database.get_preferences().get(m_id, {}).get("value")
                preference_service.save_preference(m_id, val)
                # Log edit
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with database.db_lock:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, ("preference", m_id, "update", str(orig), val, now))
                    conn.commit()
                    conn.close()
            else:
                self.send_json({"success": False, "error": f"Invalid type {m_type}"}, 400)
                return

            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_delete_memory(self, m_type, m_id):
        try:
            if m_type == "goal":
                database.delete_goal(m_id)
                from core.human_memory import service as hm_service
                hm_service.delete_goal_vector(m_id)
            elif m_type == "relationship":
                database.delete_relationship(m_id)
                from core.human_memory import service as hm_service
                hm_service.delete_relationship_vector(m_id)
            elif m_type == "project":
                database.delete_project(m_id)
                from core.human_memory import service as hm_service
                hm_service.delete_project_vector(m_id)
            elif m_type == "identity":
                orig = database.get_profile().get(m_id)
                database.delete_profile_field(m_id)
                from core.human_memory import service as hm_service
                hm_service.sync_profile_to_vector()
                # Log deletion
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with database.db_lock:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, ("identity", m_id, "delete", str(orig), "deleted", now))
                    conn.commit()
                    conn.close()
            elif m_type == "preference":
                orig = database.get_preferences().get(m_id, {}).get("value")
                preference_service.delete_preference(m_id)
                # Log deletion
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with database.db_lock:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO memory_change_log (memory_type, memory_id, action, original_value, new_value, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, ("preference", m_id, "delete", str(orig), "deleted", now))
                    conn.commit()
                    conn.close()
            else:
                self.send_json({"success": False, "error": f"Invalid type {m_type}"}, 400)
                return

            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def handle_restore_memory(self, m_type, m_id):
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            table_map = {"goal": "goals", "relationship": "relationships", "project": "projects"}
            table = table_map.get(m_type)
            if not table:
                self.send_json({"success": False, "error": f"Cannot restore type {m_type}"}, 400)
                return

            with database.db_lock:
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute(f"UPDATE {table} SET is_deleted = 0 WHERE id = ?", (m_id,))
                # Log restore
                cursor.execute("""
                INSERT INTO memory_change_log (memory_type, memory_id, action, new_value, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (m_type, m_id, "restore", "is_deleted=0", now))
                conn.commit()
                conn.close()

            # Sync vectors back
            from core.human_memory import service as hm_service
            if m_type == "goal":
                goals = database.get_goals(include_deleted=True)
                g = next((x for x in goals if x["id"] == m_id), None)
                if g:
                    hm_service.sync_goal_to_vector(m_id, g["title"], g["description"], g["status"], target_date=g["target_date"], progress=g["progress"])
            elif m_type == "relationship":
                rels = database.get_relationships(include_deleted=True)
                r = next((x for x in rels if x["id"] == m_id), None)
                if r:
                    hm_service.sync_relationship_to_vector(m_id, r["name"], r["relation_type"], r["contact_info"], r["notes"])
            elif m_type == "project":
                projs = database.get_projects(include_deleted=True)
                p = next((x for x in projs if x["id"] == m_id), None)
                if p:
                    hm_service.sync_project_to_vector(m_id, p["name"], p["description"], p["status"])

            self.send_json({"success": True})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

_server = None

def start_server():
    global _server
    if _server is None:
        handler = MemoryHTTPRequestHandler
        _server = ThreadingHTTPServer(('localhost', PORT), handler)
        t = threading.Thread(target=_server.serve_forever, daemon=True, name="MemoryWebServer")
        t.start()
        print(f"[VOICE UX] Memory Web UI Server running on http://localhost:{PORT}/memory")

def stop_server():
    global _server
    if _server:
        _server.shutdown()
        _server.server_close()
        _server = None
        print("Memory Web UI Server stopped")
