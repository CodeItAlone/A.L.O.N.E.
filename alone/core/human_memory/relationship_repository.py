import sqlite3
from datetime import datetime
from typing import List, Optional
from core.human_memory.database import get_connection, db_lock
from core.human_memory.relationship_entity import Relationship

class RelationshipRepository:
    def save(self, rel: Relationship) -> Relationship:
        """Saves or updates a Relationship record using database.py CRUD/raw queries."""
        from core.human_memory import database
        
        all_rels = database.get_relationships()
        exists = any(r["id"] == rel.id for r in all_rels)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if exists:
            database.update_relationship(
                rel_id=rel.id,
                name=rel.name,
                relation_type=rel.relationship_type,
                notes=rel.notes,
                description=rel.description,
                preferences=rel.preferences,
                importance_score=rel.importance_score
            )
            rel.updated_at = now
        else:
            if not rel.created_at:
                rel.created_at = now
            if not rel.updated_at:
                rel.updated_at = now
            database.add_relationship(
                rel_id=rel.id,
                name=rel.name,
                relation_type=rel.relationship_type,
                notes=rel.notes,
                description=rel.description,
                preferences=rel.preferences,
                importance_score=rel.importance_score
            )
        return rel

    def find_by_id(self, rel_id: str) -> Optional[Relationship]:
        """Finds a Relationship by ID."""
        all_rels = self.find_all()
        for r in all_rels:
            if r.id == rel_id:
                return r
        return None

    def find_all(self) -> List[Relationship]:
        """Retrieves all relationships."""
        from core.human_memory import database
        rows = database.get_relationships()
        return [Relationship.from_dict(row) for row in rows]

    def delete(self, rel_id: str) -> bool:
        """Deletes a Relationship by ID."""
        from core.human_memory import database
        database.delete_relationship(rel_id)
        return True

    def find_by_name(self, name: str) -> Optional[Relationship]:
        """Finds a Relationship by case-insensitive name match."""
        all_rels = self.find_all()
        for r in all_rels:
            if r.name.lower().strip() == name.lower().strip():
                return r
        return None

    def find_by_type(self, rel_type: str) -> List[Relationship]:
        """Finds all relationships matching a specific type."""
        all_rels = self.find_all()
        return [r for r in all_rels if r.relationship_type.upper().strip() == rel_type.upper().strip()]

    def find_important_relationships(self, threshold: int = 50) -> List[Relationship]:
        """Finds all relationships with importance_score >= threshold."""
        all_rels = self.find_all()
        return [r for r in all_rels if r.importance_score >= threshold]

    def search_relationships(self, query: str) -> List[Relationship]:
        """Performs simple local keyword search across name, description, preferences, and notes."""
        q = query.lower().strip()
        all_rels = self.find_all()
        results = []
        for r in all_rels:
            name_match = q in r.name.lower()
            desc_match = r.description and q in r.description.lower()
            pref_match = r.preferences and q in r.preferences.lower()
            note_match = r.notes and q in r.notes.lower()
            type_match = q in r.relationship_type.lower()
            if name_match or desc_match or pref_match or note_match or type_match:
                results.append(r)
        return results

# Singleton instance
relationship_repository = RelationshipRepository()
