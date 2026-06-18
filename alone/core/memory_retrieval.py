from typing import List, Dict

class BaseMemoryProvider:
    def search(self, query: str) -> List[Dict]:
        pass

    def retrieve(self, query: str) -> str:
        pass

    def get_relevance(self, query: str) -> float:
        pass

class IdentityMemoryProvider(BaseMemoryProvider):
    def get_relevance(self, query: str) -> float:
        query_lower = query.lower()
        if any(k in query_lower for k in ["who am i", "my name", "my age", "my profile", "myself", "who i am"]):
            return 0.95
        if any(k in query_lower for k in ["name", "age", "profession", "location", "education", "job", "work"]):
            return 0.7
        return 0.1

    def search(self, query: str) -> List[Dict]:
        from core.human_memory.service import UserProfileService
        profile = UserProfileService.retrieve()
        relevance = self.get_relevance(query)
        results = []
        for key, val in profile.items():
            content = f"{key.title()}: {val}"
            q_words = [w for w in query.lower().split() if len(w) > 1]
            match_score = 0.0
            if q_words:
                matches = sum(1 for w in q_words if w in key.lower() or w in val.lower())
                match_score = matches / len(q_words)
            score = max(relevance, match_score)
            results.append({
                "memory_type": "identity",
                "content": content,
                "score": score
            })
        return results

    def retrieve(self, query: str) -> str:
        results = self.search(query)
        results = [r for r in results if r["score"] > 0.1]
        results.sort(key=lambda x: x["score"], reverse=True)
        return "\n".join([r["content"] for r in results])

class GoalMemoryProvider(BaseMemoryProvider):
    def get_relevance(self, query: str) -> float:
        query_lower = query.lower()
        if any(k in query_lower for k in ["what am i working towards", "my goals", "what are my goals", "working on", "working towards"]):
            return 0.95
        if any(k in query_lower for k in ["goal", "goals", "milestone", "milestones", "target", "targets", "achieve", "progress"]):
            return 0.7
        return 0.1

    def search(self, query: str) -> List[Dict]:
        from core.human_memory import database
        goals = database.get_goals()
        relevance = self.get_relevance(query)
        results = []
        for g in goals:
            title = g.get("title", "")
            desc = g.get("description", "") or ""
            status = g.get("status", "")
            progress = g.get("progress", 0)
            content = f"Goal: {title} | Status: {status} | Progress: {progress}% | Description: {desc}"
            
            q_words = [w for w in query.lower().split() if len(w) > 1]
            match_score = 0.0
            if q_words:
                matches = sum(1 for w in q_words if w in title.lower() or w in desc.lower())
                match_score = matches / len(q_words)
            score = max(relevance, match_score)
            results.append({
                "memory_type": "goal",
                "content": content,
                "score": score
            })
        return results

    def retrieve(self, query: str) -> str:
        results = self.search(query)
        results = [r for r in results if r["score"] > 0.1]
        results.sort(key=lambda x: x["score"], reverse=True)
        return "\n".join([r["content"] for r in results])

class RelationshipMemoryProvider(BaseMemoryProvider):
    def get_relevance(self, query: str) -> float:
        query_lower = query.lower()
        if any(k in query_lower for k in ["who is", "tell me about my", "relationship", "contact"]):
            return 0.8
        if any(k in query_lower for k in ["friend", "family", "mentor", "professor", "colleague", "teammate", "client", "contact"]):
            return 0.7
        return 0.1

    def search(self, query: str) -> List[Dict]:
        from core.human_memory import database
        relationships = database.get_relationships()
        relevance = self.get_relevance(query)
        results = []
        for r in relationships:
            name = r.get("name", "")
            rel_type = r.get("relation_type", "")
            notes = r.get("notes", "") or ""
            desc = r.get("description", "") or ""
            pref = r.get("preferences", "") or ""
            content = f"Contact: {name} ({rel_type}) | Description: {desc} | Preferences: {pref} | Notes: {notes}"
            
            q_words = [w for w in query.lower().split() if len(w) > 1]
            match_score = 0.0
            if q_words:
                matches = sum(1 for w in q_words if w in name.lower() or w in notes.lower() or w in desc.lower() or w in rel_type.lower())
                match_score = matches / len(q_words)
                if name.lower() in query.lower():
                    match_score = max(match_score, 0.95)
            score = max(relevance, match_score)
            results.append({
                "memory_type": "relationship",
                "content": content,
                "score": score
            })
        return results

    def retrieve(self, query: str) -> str:
        results = self.search(query)
        results = [r for r in results if r["score"] > 0.1]
        results.sort(key=lambda x: x["score"], reverse=True)
        return "\n".join([r["content"] for r in results])

class TaskMemoryProvider(BaseMemoryProvider):
    def get_relevance(self, query: str) -> float:
        query_lower = query.lower()
        if any(k in query_lower for k in ["what am i working on", "my tasks", "what are my tasks", "current tasks", "to do", "todo"]):
            return 0.95
        if any(k in query_lower for k in ["task", "tasks", "pending tasks", "action items"]):
            return 0.7
        return 0.1

    def search(self, query: str) -> List[Dict]:
        from core.human_memory import database
        tasks = database.get_tasks()
        relevance = self.get_relevance(query)
        results = []
        for t in tasks:
            title = t.get("title", "")
            desc = t.get("description", "") or ""
            status = t.get("status", "")
            priority = t.get("priority", "")
            due = t.get("due_date", "") or ""
            content = f"Task: {title} | Status: {status} | Priority: {priority} | Due Date: {due} | Description: {desc}"
            
            q_words = [w for w in query.lower().split() if len(w) > 1]
            match_score = 0.0
            if q_words:
                matches = sum(1 for w in q_words if w in title.lower() or w in desc.lower())
                match_score = matches / len(q_words)
            score = max(relevance, match_score)
            results.append({
                "memory_type": "task",
                "content": content,
                "score": score
            })
        return results

    def retrieve(self, query: str) -> str:
        results = self.search(query)
        results = [r for r in results if r["score"] > 0.1]
        results.sort(key=lambda x: x["score"], reverse=True)
        return "\n".join([r["content"] for r in results])

class MemoryRetrievalService:
    def __init__(self):
        self.providers = []

    def register_provider(self, provider: BaseMemoryProvider):
        self.providers.append(provider)

    def search(self, query: str) -> List[Dict]:
        results = []
        for provider in self.providers:
            results.extend(provider.search(query))
        return self.rank_results(results)

    def rank_results(self, results: List[Dict]) -> List[Dict]:
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def retrieve(self, query: str) -> Dict[str, List[str]]:
        return self.retrieve_context(query)

    def retrieve_context(self, query: str) -> Dict[str, List[str]]:
        ranked = self.search(query)
        context = {
            "identity": [],
            "goals": [],
            "relationships": [],
            "tasks": []
        }
        for r in ranked:
            if r["score"] > 0.1:
                m_type = r["memory_type"]
                if m_type == "identity":
                    context["identity"].append(r["content"])
                elif m_type == "goal":
                    context["goals"].append(r["content"])
                elif m_type == "relationship":
                    context["relationships"].append(r["content"])
                elif m_type == "task":
                    context["tasks"].append(r["content"])
        return context

# Singleton instance
memory_retrieval_service = MemoryRetrievalService()
memory_retrieval_service.register_provider(IdentityMemoryProvider())
memory_retrieval_service.register_provider(GoalMemoryProvider())
memory_retrieval_service.register_provider(RelationshipMemoryProvider())
memory_retrieval_service.register_provider(TaskMemoryProvider())
