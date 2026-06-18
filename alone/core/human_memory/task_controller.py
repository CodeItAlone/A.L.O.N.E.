from typing import List, Optional, Dict, Any
from core.human_memory.task_service import task_service

class TaskController:
    def __init__(self, service=None):
        self.service = service or task_service

    def create_task(self, title: str, description: Optional[str] = None, 
                    priority: str = "MEDIUM", status: str = "PENDING", 
                    due_date: Optional[str] = None, project_id: Optional[str] = None, 
                    goal_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates a Task and returns it as a dictionary."""
        try:
            task = self.service.create_task(
                title=title,
                description=description,
                priority=priority,
                status=status,
                due_date=due_date,
                project_id=project_id,
                goal_id=goal_id
            )
            return {"success": True, "task": task.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Retrieves a single Task by ID."""
        tasks = self.service.get_tasks()
        task = next((t for t in tasks if t.id == task_id), None)
        if not task:
            return {"success": False, "error": f"Task with ID {task_id} not found."}
        return {"success": True, "task": task.to_dict()}

    def get_tasks(self) -> Dict[str, Any]:
        """Retrieves all Tasks."""
        try:
            tasks = self.service.get_tasks()
            return {"success": True, "tasks": [t.to_dict() for t in tasks]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pending_tasks(self) -> Dict[str, Any]:
        """Retrieves pending Tasks."""
        try:
            tasks = self.service.get_pending_tasks()
            return {"success": True, "tasks": [t.to_dict() for t in tasks]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_overdue_tasks(self) -> Dict[str, Any]:
        """Retrieves overdue Tasks."""
        try:
            tasks = self.service.get_overdue_tasks()
            return {"success": True, "tasks": [t.to_dict() for t in tasks]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Updates a Task."""
        try:
            task = self.service.update_task(task_id, **kwargs)
            if not task:
                return {"success": False, "error": f"Task with ID {task_id} not found."}
            return {"success": True, "task": task.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Completes a Task."""
        try:
            task = self.service.complete_task(task_id)
            if not task:
                return {"success": False, "error": f"Task with ID {task_id} not found."}
            return {"success": True, "task": task.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Deletes a Task."""
        try:
            success = self.service.delete_task(task_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_natural_language_task(self, llm, user_message: str) -> Dict[str, Any]:
        """Extracts task attributes from natural language instruction and creates the task."""
        try:
            prompt = (
                "You are an NLP metadata extractor. Given the following user instruction, extract a clean JSON dictionary representing a new task.\n"
                "Fields to extract:\n"
                "- title: The short action statement (required, e.g. 'finish Spring Boot API')\n"
                "- description: Optional context (or null)\n"
                "- priority: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL' (default 'MEDIUM')\n"
                "- status: 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED' (default 'PENDING')\n"
                "- due_date: YYYY-MM-DD if a deadline/date is specified, else null\n\n"
                "Respond with ONLY the valid JSON block and no other text.\n\n"
                f"Instruction: '{user_message}'\n"
                "JSON:"
            )
            from langchain_core.messages import SystemMessage, HumanMessage
            import json
            import re
            
            messages = [
                SystemMessage(content="You only output valid JSON representing the extracted task metadata."),
                HumanMessage(content=prompt)
            ]
            response = llm.invoke(messages)
            clean_res = response.content.strip()
            
            # Use regex to extract JSON block in case LLM prepends markdown blocks
            match = re.search(r"\{.*\}", clean_res, re.DOTALL)
            if match:
                extracted = json.loads(match.group(0))
            else:
                extracted = json.loads(clean_res)
                
            if not extracted or "title" not in extracted or not extracted["title"]:
                return {"success": False, "error": "No task title could be extracted."}
                
            task = self.service.create_task(
                title=extracted["title"],
                description=extracted.get("description"),
                priority=extracted.get("priority", "MEDIUM"),
                status=extracted.get("status", "PENDING"),
                due_date=extracted.get("due_date")
            )
            return {"success": True, "task": task.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Singleton instance
task_controller = TaskController()
