from typing import List
from core.human_memory.relationship_service import relationship_service

class RelationshipMemoryProvider:
    def retrieve(self, query: str) -> str:
        """Searches Relationship Memory (both DB and vector) for semantically relevant matches."""
        # Log retrieval action
        print(f"[RELATIONSHIP RETRIEVAL] Query: '{query}'")
        
        # Search DB
        db_results = relationship_service.search_relationships(query)
        
        # If matches are found in DB, format them nicely
        if db_results:
            lines = []
            for r in db_results:
                pref_part = f" | Preferences: {r.preferences}" if r.preferences else ""
                desc_part = f" | Description: {r.description}" if r.description else ""
                note_part = f" | Notes: {r.notes}" if r.notes else ""
                lines.append(f"  - {r.name} is your {r.relationship_type.lower()}{desc_part}{pref_part}{note_part}")
            return "Matched Contacts:\n" + "\n".join(lines)
            
        return ""

# Singleton instance
relationship_memory_provider = RelationshipMemoryProvider()
