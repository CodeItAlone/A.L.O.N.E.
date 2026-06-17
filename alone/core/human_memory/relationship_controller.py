from typing import List, Optional, Dict, Any
from core.human_memory.relationship_service import relationship_service
from core.human_memory.relationship_entity import Relationship

class RelationshipController:
    def __init__(self, service=None):
        self.service = service or relationship_service

    def create_relationship(self, name: str, relationship_type: str = "OTHER", 
                            description: Optional[str] = None, preferences: Optional[str] = None, 
                            notes: Optional[str] = None, importance_score: Optional[int] = None) -> Dict[str, Any]:
        try:
            rel = self.service.create_relationship(
                name=name,
                relationship_type=relationship_type,
                description=description,
                preferences=preferences,
                notes=notes,
                importance_score=importance_score
            )
            return {"success": True, "relationship": rel.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_relationship(self, rel_id: str) -> Dict[str, Any]:
        rel = self.service.get_relationship(rel_id)
        if not rel:
            return {"success": False, "error": f"Relationship with ID {rel_id} not found."}
        return {"success": True, "relationship": rel.to_dict()}

    def get_relationships(self, relationship_type: Optional[str] = None) -> Dict[str, Any]:
        try:
            if relationship_type:
                rels = self.service.find_by_type(relationship_type)
            else:
                rels = self.service.get_all_relationships()
            return {"success": True, "relationships": [r.to_dict() for r in rels]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_relationship(self, rel_id: str, name: Optional[str] = None, 
                            relationship_type: Optional[str] = None, description: Optional[str] = None, 
                            preferences: Optional[str] = None, notes: Optional[str] = None, 
                            importance_score: Optional[int] = None) -> Dict[str, Any]:
        try:
            rel = self.service.update_relationship(
                rel_id=rel_id,
                name=name,
                relationship_type=relationship_type,
                description=description,
                preferences=preferences,
                notes=notes,
                importance_score=importance_score
            )
            return {"success": True, "relationship": rel.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_relationship(self, rel_id: str) -> Dict[str, Any]:
        try:
            success = self.service.delete_relationship(rel_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_relationships(self, query: str) -> Dict[str, Any]:
        try:
            rels = self.service.search_relationships(query)
            return {"success": True, "relationships": [r.to_dict() for r in rels]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_natural_language_relationship(self, llm, user_message: str) -> Dict[str, Any]:
        try:
            return self.service.process_natural_language_relationship(llm, user_message)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_request(self, method: str, path: str, body: dict = None) -> dict:
        """Dispatches request to simulate HTTP routes."""
        method = method.upper().strip()
        path = path.strip()
        body = body or {}

        # GET /relationships/search?q=...
        if method == "GET" and path.startswith("/relationships/search"):
            query = body.get("query") or body.get("q") or ""
            return self.search_relationships(query)

        # GET /relationships/{id}
        if method == "GET" and path.startswith("/relationships/") and len(path.split("/")) > 2:
            rel_id = path.split("/")[-1]
            return self.get_relationship(rel_id)

        # GET /relationships
        if method == "GET" and path == "/relationships":
            rel_type = body.get("relationshipType") or body.get("relationship_type")
            return self.get_relationships(relationship_type=rel_type)

        # POST /relationships
        if method == "POST" and path == "/relationships":
            name = body.get("name")
            if not name:
                return {"success": False, "error": "name is required"}
            return self.create_relationship(
                name=name,
                relationship_type=body.get("relationshipType") or body.get("relationship_type") or "OTHER",
                description=body.get("description"),
                preferences=body.get("preferences"),
                notes=body.get("notes"),
                importance_score=body.get("importanceScore") or body.get("importance_score")
            )

        # PUT /relationships/{id}
        if method == "PUT" and path.startswith("/relationships/") and len(path.split("/")) > 2:
            rel_id = path.split("/")[-1]
            return self.update_relationship(
                rel_id=rel_id,
                name=body.get("name"),
                relationship_type=body.get("relationshipType") or body.get("relationship_type"),
                description=body.get("description"),
                preferences=body.get("preferences"),
                notes=body.get("notes"),
                importance_score=body.get("importanceScore") or body.get("importance_score")
            )

        # DELETE /relationships/{id}
        if method == "DELETE" and path.startswith("/relationships/") and len(path.split("/")) > 2:
            rel_id = path.split("/")[-1]
            return self.delete_relationship(rel_id)

        return {"success": False, "error": f"Route {method} {path} not found"}

# Singleton instance
relationship_controller = RelationshipController()
