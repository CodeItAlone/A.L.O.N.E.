import os
import uuid
from core.memory import client, embedding_fn
from core.human_memory import database

# Initialize ChromaDB vector collections for human memory classes
try:
    profile_vector_col = client.get_or_create_collection(
        name="alone_profile_vector",
        embedding_function=embedding_fn
    )
    projects_vector_col = client.get_or_create_collection(
        name="alone_projects_vector",
        embedding_function=embedding_fn
    )
    goals_vector_col = client.get_or_create_collection(
        name="alone_goals_vector",
        embedding_function=embedding_fn
    )
    relationships_vector_col = client.get_or_create_collection(
        name="alone_relationships_vector",
        embedding_function=embedding_fn
    )
except Exception as e:
    print(f"[!] Error initializing ChromaDB collections for Human Memory: {e}")
    profile_vector_col = None
    projects_vector_col = None
    goals_vector_col = None
    relationships_vector_col = None

# --- Profile Vector Sync ---
def sync_profile_to_vector():
    if profile_vector_col is None:
        return
    try:
        profile_data = database.get_profile()
        # Delete existing profile vector keys
        data = profile_vector_col.get()
        if data and data["ids"]:
            profile_vector_col.delete(ids=data["ids"])
            
        # Add updated profile values
        for key, val in profile_data.items():
            doc_text = f"User Profile Field - {key}: {val}"
            profile_vector_col.add(
                documents=[doc_text],
                metadatas=[{"key": key, "type": "profile"}],
                ids=[f"prof_{key}"]
            )
    except Exception as e:
        print(f"[Memory Warning] Failed to sync profile to vector store: {e}")

# --- Projects Vector Sync ---
def sync_project_to_vector(project_id, name, description, status):
    if projects_vector_col is None:
        return
    try:
        doc_text = f"Project: {name}. Description: {description or 'None'}. Status: {status}."
        projects_vector_col.upsert(
            documents=[doc_text],
            metadatas=[{"project_id": project_id, "type": "project", "name": name, "status": status}],
            ids=[f"proj_{project_id}"]
        )
    except Exception as e:
        print(f"[Memory Warning] Failed to sync project '{name}' to vector store: {e}")

def delete_project_vector(project_id):
    if projects_vector_col is None:
        return
    try:
        projects_vector_col.delete(ids=[f"proj_{project_id}"])
    except Exception as e:
        print(f"[Memory Warning] Failed to delete project vector '{project_id}': {e}")

# --- Goals Vector Sync ---
def sync_goal_to_vector(goal_id, title, description, status, parent_goal_id=None, target_date=None, category="", priority="", progress=0, project_ids=None):
    if goals_vector_col is None:
        return
    try:
        doc_text = f"Goal: {title}. Description: {description or 'None'}. Status: {status}."
        if category:
            doc_text += f" Category: {category}."
        if priority:
            doc_text += f" Priority: {priority}."
        if progress is not None:
            doc_text += f" Progress: {progress}%."
        if target_date:
            doc_text += f" Target Date: {target_date}."
        if project_ids:
            doc_text += f" Linked Projects: {', '.join(project_ids)}."
        
        meta = {
            "goal_id": goal_id, 
            "type": "goal", 
            "title": title, 
            "status": status,
            "category": category or "",
            "priority": priority or "",
            "progress": int(progress or 0)
        }
        if parent_goal_id:
            meta["parent_goal_id"] = parent_goal_id
        if project_ids:
            meta["project_ids"] = ",".join(project_ids)
            
        goals_vector_col.upsert(
            documents=[doc_text],
            metadatas=[meta],
            ids=[f"goal_{goal_id}"]
        )
    except Exception as e:
        print(f"[Memory Warning] Failed to sync goal '{title}' to vector store: {e}")

def delete_goal_vector(goal_id):
    if goals_vector_col is None:
        return
    try:
        goals_vector_col.delete(ids=[f"goal_{goal_id}"])
    except Exception as e:
        print(f"[Memory Warning] Failed to delete goal vector '{goal_id}': {e}")

# --- Relationships Vector Sync ---
def sync_relationship_to_vector(rel_id, name, relation_type, contact_info, notes):
    if relationships_vector_col is None:
        return
    try:
        doc_text = f"Contact/Relationship: {name}. Relation: {relation_type}. Contact Info: {contact_info or 'None'}. Notes: {notes or 'None'}."
        relationships_vector_col.upsert(
            documents=[doc_text],
            metadatas=[{"relationship_id": rel_id, "type": "relationship", "name": name, "relation_type": relation_type}],
            ids=[f"rel_{rel_id}"]
        )
    except Exception as e:
        print(f"[Memory Warning] Failed to sync relationship '{name}' to vector store: {e}")

def delete_relationship_vector(rel_id):
    if relationships_vector_col is None:
        return
    try:
        relationships_vector_col.delete(ids=[f"rel_{rel_id}"])
    except Exception as e:
        print(f"[Memory Warning] Failed to delete relationship vector '{rel_id}': {e}")

# --- Context Retrieval Service ---
def get_active_context_summary() -> str:
    """Builds a rich, structured text description of user profile, active projects, goals, and relationships."""
    try:
        # Load user profile
        profile = database.get_profile()
        profile_lines = []
        for k, v in profile.items():
            profile_lines.append(f"  * {k.title()}: {v}")
        profile_str = "\n".join(profile_lines) if profile_lines else "  * None configured."

        # Load active projects
        projects = database.get_projects(status="active")
        projects_lines = []
        for p in projects:
            projects_lines.append(f"  * Project: {p['name']} | Status: {p['status']}\n    Desc: {p['description'] or 'No description'}")
        projects_str = "\n".join(projects_lines) if projects_lines else "  * No active projects."

        # Load current active/pending goals
        from core.human_memory.goal_repository import goal_repository
        goals = goal_repository.find_all()
        active_goals = [g for g in goals if g.status in ("pending", "in_progress")]
        projects_map = {p["id"]: p["name"] for p in database.get_projects()}
        
        goals_lines = []
        for g in active_goals:
            target = f" | Target: {g.targetDate}" if g.targetDate else ""
            cat_str = f" | Category: {g.category}" if g.category else ""
            prio_str = f" | Priority: {g.priority}" if g.priority else ""
            prog_str = f" | Progress: {g.progress}%"
            
            proj_names = [projects_map[pid] for pid in g.projectIds if pid in projects_map]
            proj_str = f" | Projects: {', '.join(proj_names)}" if proj_names else ""
            
            goals_lines.append(f"  * Goal: {g.title} | Status: {g.status}{prog_str}{cat_str}{prio_str}{target}{proj_str}\n    Desc: {g.description or 'No description'}")
        goals_str = "\n".join(goals_lines) if goals_lines else "  * No active goals."

        # Load relationships
        relationships = database.get_relationships()
        rel_lines = []
        for r in relationships:
            rel_lines.append(f"  * Contact: {r['name']} ({r['relation_type']})\n    Notes: {r['notes'] or 'No notes'}")
        rel_str = "\n".join(rel_lines) if rel_lines else "  * No contacts logged."

        # Format context prompt
        formatted = (
            "=== STRUCTURED HUMAN MEMORY CONTEXT ===\n"
            f"[User Profile details]:\n{profile_str}\n\n"
            f"[Active Projects]:\n{projects_str}\n\n"
            f"[Active Goals & Milestones]:\n{goals_str}\n\n"
            f"[Contacts & Relationships]:\n{rel_str}\n"
            "========================================"
        )
        return formatted
    except Exception as e:
        print(f"[Memory Warning] Context summary compilation failed: {e}")
        return ""

def search_human_memory(query: str, top_k: int = 2) -> str:
    """Performs semantic search across projects, goals, and relationships, returning matches."""
    results_text = []
    
    # 1. Search Projects
    if projects_vector_col:
        try:
            res = projects_vector_col.query(query_texts=[query], n_results=top_k)
            if res and res["documents"] and res["documents"][0]:
                results_text.append("Matched Projects:\n" + "\n".join([f"  - {doc}" for doc in res["documents"][0]]))
        except Exception:
            pass
            
    # 2. Search Goals
    if goals_vector_col:
        try:
            res = goals_vector_col.query(query_texts=[query], n_results=top_k)
            if res and res["documents"] and res["documents"][0]:
                results_text.append("Matched Goals:\n" + "\n".join([f"  - {doc}" for doc in res["documents"][0]]))
        except Exception:
            pass

    # 3. Search Relationships
    if relationships_vector_col:
        try:
            res = relationships_vector_col.query(query_texts=[query], n_results=top_k)
            if res and res["documents"] and res["documents"][0]:
                results_text.append("Matched Contacts:\n" + "\n".join([f"  - {doc}" for doc in res["documents"][0]]))
        except Exception:
            pass
            
    if not results_text:
        return ""
        
    return "=== SEMANTIC MEMORY MATCHES ===\n" + "\n\n".join(results_text) + "\n==============================="


class UserProfileService:
    @staticmethod
    def extract(llm, text: str) -> dict:
        """Extracts user profile details from natural language text as a JSON dictionary."""
        prompt = (
            "You are a precise metadata extractor for a personal assistant.\n"
            "Analyze the following statement and extract personal attributes about the user (e.g. name, education, profession, role, hobbies, age, etc.).\n"
            "Do not extract system configuration details or preferences (like preferred code editors, paths, IDEs, or languages).\n"
            "Return ONLY a valid JSON object map of key-value pairs representing these profile attributes (keys and values must be strings).\n"
            "If no attributes are found, return an empty JSON object {}.\n\n"
            f"User Statement: \"{text}\"\n"
            "JSON Output:"
        )
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="You are a precise metadata extractor. You respond with ONLY a valid JSON object."),
            HumanMessage(content=prompt)
        ]
        try:
            response = llm.invoke(messages)
            content = response.content.strip()
            # Clean possible markdown wrap (```json ... ```)
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            import json
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"[Memory Warning] User profile extraction failed: {e}")
        return {}

    @staticmethod
    def save(extracted: dict) -> bool:
        """Saves user profile attributes to the database, syncing with vector store, logging results and performing post-write verification."""
        if not extracted:
            return False
            
        # Log detected profile
        print("[PROFILE DETECTED]")
        for k, v in extracted.items():
            print(f"{k}={v}")
            
        # Determine if it's an update of any existing fields
        existing = database.get_profile()
        is_update = any(k.lower().strip() in existing for k in extracted)
        
        # Save attributes
        for k, v in extracted.items():
            database.set_profile_field(k, v)
            
        # Sync with ChromaDB vector store
        sync_profile_to_vector()
        
        # Log save / update status
        if is_update:
            print("[PROFILE UPDATE]")
        else:
            print("[PROFILE SAVE]")
        print("success=True")
        
        # Post-write verification
        verified = database.get_profile()
        verify_passed = True
        print("[PROFILE VERIFY]")
        for k, v in extracted.items():
            key_clean = k.lower().strip()
            db_val = verified.get(key_clean)
            print(f"{k}={v}")
            if db_val != v:
                verify_passed = False
                
        if verify_passed:
            print("status=PASS")
        else:
            print("status=FAIL")
            
        return verify_passed

    @staticmethod
    def retrieve() -> dict:
        """Retrieves user profile attributes from the database and logs retrieval."""
        profile = database.get_profile()
        print("[PROFILE RETRIEVE]")
        for k, v in profile.items():
            print(f"{k}={v}")
        return profile


