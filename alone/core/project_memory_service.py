import uuid
from datetime import datetime
from core.human_memory import database

class ProjectMemoryService:
    def create_project(self, name, description="", phase="", priority="", status="active", project_id=None):
        """Creates a new project record in SQLite and marks it active."""
        if not project_id:
            project_id = str(uuid.uuid4())[:8]
        
        database.add_project(project_id, name, description, status, phase, priority)
        
        # Save as the current active project in preferences
        try:
            from core.preferences_service import preference_service
            preference_service.save_preference("active_project_id", project_id)
        except Exception as e:
            print(f"[ProjectMemoryService Warning] Failed to set active project preference: {e}")
            
        return self.get_project(project_id)

    def get_project(self, project_id_or_name):
        """Retrieves a project by ID or case-insensitive name match."""
        projects = database.get_projects()
        
        # 1. Match by ID
        for p in projects:
            if p["id"] == project_id_or_name:
                return p
                
        # 2. Match by Name (case-insensitive)
        name_clean = str(project_id_or_name).lower().strip()
        for p in projects:
            if p["name"].lower().strip() == name_clean:
                return p
                
        return None

    def get_active_projects(self):
        """Returns all projects that are currently active."""
        return database.get_projects(status="active")

    def update_project(self, project_id_or_name, name=None, description=None, phase=None, priority=None, status=None):
        """Updates project fields in SQLite."""
        p = self.get_project(project_id_or_name)
        if not p:
            raise ValueError(f"Project '{project_id_or_name}' not found.")
            
        project_id = p["id"]
        updated_name = name if name is not None else p["name"]
        updated_description = description if description is not None else p["description"]
        updated_status = status if status is not None else p["status"]
        updated_phase = phase if phase is not None else p["phase"]
        updated_priority = priority if priority is not None else p["priority"]
        
        database.update_project(
            project_id,
            updated_name,
            updated_description,
            updated_status,
            phase=updated_phase,
            priority=updated_priority
        )
        return self.get_project(project_id)

    def archive_project(self, project_id_or_name):
        """Converts project status to archived."""
        return self.update_project(project_id_or_name, status="archived")

    def delete_project(self, project_id_or_name):
        """Deletes a project record from SQLite."""
        p = self.get_project(project_id_or_name)
        if not p:
            raise ValueError(f"Project '{project_id_or_name}' not found.")
            
        database.delete_project(p["id"])
        
        # Clean up active project preference if deleted
        try:
            from core.preferences_service import preference_service
            active_id = preference_service.get_preference("active_project_id")
            if active_id == p["id"]:
                preference_service.delete_preference("active_project_id")
        except Exception:
            pass
            
        return True

    def get_active_project_context(self) -> str:
        """Retrieves and formats active project context for dynamic injection into agent executor inputs."""
        try:
            from core.preferences_service import preference_service
            active_id = preference_service.get_preference("active_project_id")
        except Exception:
            active_id = None
            
        project = None
        if active_id:
            project = self.get_project(active_id)
            
        if not project:
            active_projects = self.get_active_projects()
            if len(active_projects) == 1:
                project = active_projects[0]
                try:
                    preference_service.save_preference("active_project_id", project["id"])
                except Exception:
                    pass
            elif len(active_projects) > 1:
                # Sort by updated_at descending to choose the most recently updated one
                try:
                    active_projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                except Exception:
                    pass
                project = active_projects[0]
                try:
                    preference_service.save_preference("active_project_id", project["id"])
                except Exception:
                    pass
                    
        if not project:
            return ""
            
        lines = [
            "Current Project:",
            project["name"],
            "",
            "Phase:",
            project["phase"] or "N/A",
            "",
            "Priority:",
            project["priority"] or "N/A"
        ]
        return "\n".join(lines)

# Singleton instance
project_memory_service = ProjectMemoryService()
