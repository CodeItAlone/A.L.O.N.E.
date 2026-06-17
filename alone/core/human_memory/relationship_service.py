import uuid
from typing import List, Optional, Dict, Any
from core.human_memory.relationship_entity import Relationship
from core.human_memory.relationship_repository import relationship_repository
from core.human_memory import service as hm_vector_service

IMPORTANCE_MAP = {
    "MOTHER": 100,
    "FATHER": 100,
    "BROTHER": 90,
    "SISTER": 90,
    "MENTOR": 80,
    "PARTNER": 80,
    "PROFESSOR": 70,
    "FRIEND": 60,
    "TEAMMATE": 50,
    "COLLEAGUE": 40,
    "CLIENT": 40,
    "OTHER": 20
}

class RelationshipService:
    def __init__(self, repo=None):
        self.repo = repo or relationship_repository

    def create_relationship(self, name: str, relationship_type: str = "OTHER", 
                            description: Optional[str] = None, preferences: Optional[str] = None, 
                            notes: Optional[str] = None, importance_score: Optional[int] = None) -> Relationship:
        """Creates or merges relationship details to prevent duplicate records."""
        if not name:
            raise ValueError("Relationship name is required.")

        # Clean type
        rel_type_clean = relationship_type.upper().strip() if relationship_type else "OTHER"
        if rel_type_clean not in IMPORTANCE_MAP:
            rel_type_clean = "OTHER"

        # Calculate default importance score
        score = importance_score if importance_score is not None else IMPORTANCE_MAP.get(rel_type_clean, 20)

        # Check for existing relationship with the same name (case-insensitive)
        existing = self.repo.find_by_name(name)
        if existing:
            # Merge fields into existing record
            if rel_type_clean != "OTHER":
                existing.relationship_type = rel_type_clean
                existing.importance_score = IMPORTANCE_MAP.get(rel_type_clean, 20)
            
            if description:
                existing.description = description
                
            if preferences:
                if existing.preferences:
                    # Append unique preference items
                    existing_items = [p.strip().lower() for p in existing.preferences.split(",")]
                    new_items = [p.strip() for p in preferences.split(",") if p.strip().lower() not in existing_items]
                    if new_items:
                        existing.preferences += ", " + ", ".join(new_items)
                else:
                    existing.preferences = preferences
                    
            if notes:
                if existing.notes:
                    if notes.lower().strip() not in existing.notes.lower():
                        existing.notes += ". " + notes.strip()
                else:
                    existing.notes = notes
            
            saved_rel = self.repo.save(existing)
            self._sync_vector(saved_rel)
            return saved_rel

        # Otherwise, create a new record
        rel_id = str(uuid.uuid4())[:8]
        rel = Relationship(
            id=rel_id,
            name=name,
            relationship_type=rel_type_clean,
            description=description,
            preferences=preferences,
            notes=notes,
            importance_score=score
        )
        saved_rel = self.repo.save(rel)
        self._sync_vector(saved_rel)
        return saved_rel

    def get_relationship(self, rel_id: str) -> Optional[Relationship]:
        """Retrieves a relationship by ID."""
        return self.repo.find_by_id(rel_id)

    def get_all_relationships(self) -> List[Relationship]:
        """Retrieves all relationships."""
        return self.repo.find_all()

    def update_relationship(self, rel_id: str, name: Optional[str] = None, 
                            relationship_type: Optional[str] = None, description: Optional[str] = None, 
                            preferences: Optional[str] = None, notes: Optional[str] = None, 
                            importance_score: Optional[int] = None) -> Relationship:
        """Updates and validates an existing relationship record."""
        rel = self.repo.find_by_id(rel_id)
        if not rel:
            raise ValueError(f"Relationship with ID {rel_id} not found.")

        if name is not None:
            rel.name = name
        if relationship_type is not None:
            rel_type_clean = relationship_type.upper().strip()
            if rel_type_clean in IMPORTANCE_MAP:
                rel.relationship_type = rel_type_clean
                if importance_score is None:
                    rel.importance_score = IMPORTANCE_MAP[rel_type_clean]
        if description is not None:
            rel.description = description
        if preferences is not None:
            rel.preferences = preferences
        if notes is not None:
            rel.notes = notes
        if importance_score is not None:
            rel.importance_score = importance_score

        saved_rel = self.repo.save(rel)
        self._sync_vector(saved_rel)
        return saved_rel

    def delete_relationship(self, rel_id: str) -> bool:
        """Deletes a relationship and removes from vector store."""
        success = self.repo.delete(rel_id)
        try:
            hm_vector_service.delete_relationship_vector(rel_id)
        except Exception:
            pass
        return success

    def find_by_name(self, name: str) -> Optional[Relationship]:
        return self.repo.find_by_name(name)

    def find_by_type(self, rel_type: str) -> List[Relationship]:
        return self.repo.find_by_type(rel_type)

    def find_important_relationships(self, threshold: int = 50) -> List[Relationship]:
        return self.repo.find_important_relationships(threshold)

    def search_relationships(self, query: str) -> List[Relationship]:
        return self.repo.search_relationships(query)

    def process_natural_language_relationship(self, llm, user_message: str) -> Dict[str, Any]:
        """Runs the extraction pipeline and processes the extracted relationship data."""
        from core.human_memory.relationship_extractor import relationship_extractor
        extracted = relationship_extractor.extract(llm, user_message)
        if not extracted or "name" not in extracted or not extracted["name"]:
            return {"success": False, "error": "No person name could be extracted from statement."}
        
        rel = self.create_relationship(
            name=extracted["name"],
            relationship_type=extracted.get("relationshipType") or "OTHER",
            description=extracted.get("description"),
            preferences=extracted.get("preferences"),
            notes=extracted.get("notes")
        )
        return {"success": True, "relationship": rel.to_dict(), "extracted": extracted}

    def _sync_vector(self, rel: Relationship):
        """Syncs the relationship details with ChromaDB vector store."""
        try:
            # Map parameters for compatibility
            contact_info = rel.preferences or ""
            notes = f"Desc: {rel.description or ''}. Notes: {rel.notes or ''}."
            hm_vector_service.sync_relationship_to_vector(
                rel_id=rel.id,
                name=rel.name,
                relation_type=rel.relationship_type,
                contact_info=contact_info,
                notes=notes
            )
        except Exception as e:
            print(f"[RelationshipService Warning] Failed to sync relationship vector: {e}")

# Singleton instance
relationship_service = RelationshipService()
