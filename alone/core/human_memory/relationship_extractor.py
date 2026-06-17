import json
from typing import Dict, Any

class RelationshipExtractor:
    @staticmethod
    def extract(llm, text: str) -> dict:
        """Extracts relationship data from natural language statements using LangChain/Ollama."""
        prompt = (
            "You are a precise metadata extractor for a personal assistant.\n"
            "Analyze the user's message and extract information about a person and their relationship to the user.\n"
            "Extract details matching these fields (if not specified, use null):\n"
            "- name: The name of the person (string, REQUIRED)\n"
            "- relationshipType: One of ['FRIEND', 'FAMILY', 'BROTHER', 'SISTER', 'MOTHER', 'FATHER', 'MENTOR', 'PROFESSOR', 'COLLEAGUE', 'CLIENT', 'PARTNER', 'TEAMMATE', 'OTHER'] (string or null)\n"
            "- description: A short description of who they are (string or null)\n"
            "- preferences: Likes, preferences, hobbies, technologies they prefer, or interests (string or null)\n"
            "- notes: Job details, work facts, projects they work on, or any other notes (string or null)\n"
            "- action: Set to 'update' if the statement is updating an existing fact/preference/note about a known person (e.g. 'Rahul likes React' or 'Rahul works on frontend'), or 'create' if introducing a new relationship.\n\n"
            "Return ONLY a valid JSON object with these exact keys. If a relationship/person cannot be extracted, return an empty object {}.\n\n"
            f"User Statement: \"{text}\"\n"
            "JSON Output:"
        )
        
        # Log extraction query
        print(f"[RELATIONSHIP EXTRACTION] Input text: '{text}'")
        
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="You are a precise metadata extractor. You respond with ONLY a valid JSON object."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = llm.invoke(messages)
            content = response.content.strip()
            # Clean possible markdown wrap
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            data = json.loads(content)
            if isinstance(data, dict):
                if "name" in data and data["name"]:
                    # Clean type to uppercase
                    if "relationshipType" in data and data["relationshipType"]:
                        data["relationshipType"] = data["relationshipType"].upper().strip()
                    return data
        except Exception as e:
            print(f"[Memory Warning] Relationship extraction failed: {e}")
        return {}

# Singleton instance
relationship_extractor = RelationshipExtractor()
