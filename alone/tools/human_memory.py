import uuid
from langchain_core.tools import tool
from core.human_memory import database, service

@tool
def search_human_memory(query: str) -> str:
    """
    Searches user's structured long-term memory (projects, goals, contacts, user profile)
    for records semantically relevant to the search query.
    """
    try:
        result = service.search_human_memory(query)
        if not result:
            return "No matching human memory records found, Sir."
        return result
    except Exception as e:
        return f"Failed to search human memory: {e}, Sir."

@tool
def manage_goals(action: str, title: str = "", desc: str = "", status: str = "", target_date: str = "", goal_id: str = "") -> str:
    """
    Manages user goals and milestones.
    Parameters:
      - action: Must be 'add', 'update', 'delete', or 'list'
      - title: Title of the goal (required for 'add')
      - desc: Description of the goal / sub-tasks
      - status: One of ['pending', 'in_progress', 'achieved', 'failed']
      - target_date: Completion deadline (e.g. YYYY-MM-DD)
      - goal_id: Goal ID (required for 'update' or 'delete')
    """
    action = action.lower().strip()
    try:
        if action == "list":
            goals = database.get_goals()
            if not goals:
                return "No goals found, Sir."
            lines = []
            for g in goals:
                target = f" | Target: {g['target_date']}" if g['target_date'] else ""
                lines.append(f"- ID: {g['id']} | Title: {g['title']} | Status: {g['status']}{target}\n  Desc: {g['description'] or 'None'}")
            return "Current Goals:\n" + "\n".join(lines)
            
        elif action == "add":
            if not title:
                return "Error: Goal title is required for action 'add', Sir."
            gid = str(uuid.uuid4())[:8]
            g_status = status or "pending"
            database.add_goal(gid, title, desc, g_status, target_date=target_date)
            service.sync_goal_to_vector(gid, title, desc, g_status, target_date=target_date)
            return f"Successfully added goal '{title}' with ID: {gid}, Sir."
            
        elif action == "update":
            if not goal_id:
                return "Error: goal_id is required for action 'update', Sir."
            # Retrieve existing
            goals = database.get_goals()
            existing = [g for g in goals if g["id"] == goal_id]
            if not existing:
                return f"Error: Goal with ID {goal_id} not found, Sir."
            g = existing[0]
            new_title = title or g["title"]
            new_desc = desc or g["description"]
            new_status = status or g["status"]
            new_target = target_date or g["target_date"]
            
            database.update_goal(goal_id, new_title, new_desc, new_status, target_date=new_target)
            service.sync_goal_to_vector(goal_id, new_title, new_desc, new_status, target_date=new_target)
            return f"Successfully updated goal '{new_title}' (ID: {goal_id}), Sir."
            
        elif action == "delete":
            if not goal_id:
                return "Error: goal_id is required for action 'delete', Sir."
            database.delete_goal(goal_id)
            service.delete_goal_vector(goal_id)
            return f"Successfully deleted goal with ID: {goal_id}, Sir."
            
        else:
            return f"Error: Invalid action '{action}'. Use 'list', 'add', 'update', or 'delete', Sir."
    except Exception as e:
        return f"Failed to manage goals: {e}, Sir."

@tool
def manage_projects(action: str, name: str = "", desc: str = "", status: str = "", project_id: str = "") -> str:
    """
    Manages user projects.
    Parameters:
      - action: Must be 'add', 'update', 'delete', or 'list'
      - name: Name of the project (required for 'add')
      - desc: Description of the project
      - status: One of ['active', 'completed', 'paused', 'archived']
      - project_id: Project ID (required for 'update' or 'delete')
    """
    action = action.lower().strip()
    try:
        if action == "list":
            projects = database.get_projects()
            if not projects:
                return "No projects found, Sir."
            lines = []
            for p in projects:
                lines.append(f"- ID: {p['id']} | Name: {p['name']} | Status: {p['status']}\n  Desc: {p['description'] or 'None'}")
            return "Current Projects:\n" + "\n".join(lines)
            
        elif action == "add":
            if not name:
                return "Error: Project name is required for action 'add', Sir."
            pid = str(uuid.uuid4())[:8]
            p_status = status or "active"
            database.add_project(pid, name, desc, p_status)
            service.sync_project_to_vector(pid, name, desc, p_status)
            return f"Successfully added project '{name}' with ID: {pid}, Sir."
            
        elif action == "update":
            if not project_id:
                return "Error: project_id is required for action 'update', Sir."
            projects = database.get_projects()
            existing = [p for p in projects if p["id"] == project_id]
            if not existing:
                return f"Error: Project with ID {project_id} not found, Sir."
            p = existing[0]
            new_name = name or p["name"]
            new_desc = desc or p["description"]
            new_status = status or p["status"]
            
            database.update_project(project_id, new_name, new_desc, new_status)
            service.sync_project_to_vector(project_id, new_name, new_desc, new_status)
            return f"Successfully updated project '{new_name}' (ID: {project_id}), Sir."
            
        elif action == "delete":
            if not project_id:
                return "Error: project_id is required for action 'delete', Sir."
            database.delete_project(project_id)
            service.delete_project_vector(project_id)
            return f"Successfully deleted project with ID: {project_id}, Sir."
            
        else:
            return f"Error: Invalid action '{action}'. Use 'list', 'add', 'update', or 'delete', Sir."
    except Exception as e:
        return f"Failed to manage projects: {e}, Sir."

@tool
def manage_contacts(action: str, name: str = "", relation_type: str = "", contact_info: str = "", notes: str = "", contact_id: str = "") -> str:
    """
    Manages relationship profiles and user contacts.
    Parameters:
      - action: Must be 'add', 'update', 'delete', or 'list'
      - name: Name of the contact (required for 'add')
      - relation_type: One of ['colleague', 'friend', 'client', 'family', 'other']
      - contact_info: E.g., email address, social handle, phone number
      - notes: Special details, interaction logs, or notes about the contact
      - contact_id: Contact ID (required for 'update' or 'delete')
    """
    action = action.lower().strip()
    try:
        if action == "list":
            rels = database.get_relationships()
            if not rels:
                return "No contacts found, Sir."
            lines = []
            for r in rels:
                lines.append(f"- ID: {r['id']} | Name: {r['name']} ({r['relation_type']}) | Contact Info: {r['contact_info'] or 'None'}\n  Notes: {r['notes'] or 'None'}")
            return "Contacts & Relationships:\n" + "\n".join(lines)
            
        elif action == "add":
            if not name:
                return "Error: Contact name is required for action 'add', Sir."
            cid = str(uuid.uuid4())[:8]
            rtype = relation_type or "other"
            database.add_relationship(cid, name, rtype, contact_info, notes)
            service.sync_relationship_to_vector(cid, name, rtype, contact_info, notes)
            return f"Successfully added contact '{name}' with ID: {cid}, Sir."
            
        elif action == "update":
            if not contact_id:
                return "Error: contact_id is required for action 'update', Sir."
            rels = database.get_relationships()
            existing = [r for r in rels if r["id"] == contact_id]
            if not existing:
                return f"Error: Contact with ID {contact_id} not found, Sir."
            r = existing[0]
            new_name = name or r["name"]
            new_type = relation_type or r["relation_type"]
            new_info = contact_info or r["contact_info"]
            new_notes = notes or r["notes"]
            
            database.update_relationship(contact_id, new_name, new_type, new_info, new_notes)
            service.sync_relationship_to_vector(contact_id, new_name, new_type, new_info, new_notes)
            return f"Successfully updated contact '{new_name}' (ID: {contact_id}), Sir."
            
        elif action == "delete":
            if not contact_id:
                return "Error: contact_id is required for action 'delete', Sir."
            database.delete_relationship(contact_id)
            service.delete_relationship_vector(contact_id)
            return f"Successfully deleted contact with ID: {contact_id}, Sir."
            
        else:
            return f"Error: Invalid action '{action}'. Use 'list', 'add', 'update', or 'delete', Sir."
    except Exception as e:
        return f"Failed to manage contacts: {e}, Sir."
