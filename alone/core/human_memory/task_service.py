import uuid
import datetime
from typing import List, Optional
from core.human_memory.task_entity import Task
from core.human_memory.task_repository import task_repository

class TaskService:
    def create_task(self, title: str, description: Optional[str] = None, 
                    priority: str = "MEDIUM", status: str = "PENDING", 
                    due_date: Optional[str] = None, project_id: Optional[str] = None, 
                    goal_id: Optional[str] = None) -> Task:
        """Creates and persists a new Task."""
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority.upper(),
            status=status.upper(),
            due_date=due_date,
            project_id=project_id,
            goal_id=goal_id
        )
        task_repository.create_task(task)
        print(f"[TASK CREATE] Created Task ID: {task_id}, Title: '{title}'")
        return task

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Marks a Task as COMPLETED."""
        task = task_repository.find_by_id(task_id)
        if task:
            task.status = "COMPLETED"
            task_repository.update_task(task)
            print(f"[TASK COMPLETE] Completed Task ID: {task_id}")
            return task
        return None

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """Marks a Task as CANCELLED."""
        task = task_repository.find_by_id(task_id)
        if task:
            task.status = "CANCELLED"
            task_repository.update_task(task)
            print(f"[TASK UPDATE] Cancelled Task ID: {task_id}")
            return task
        return None

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Updates properties of a Task dynamically."""
        task = task_repository.find_by_id(task_id)
        if not task:
            return None
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                if key in ("priority", "status") and value:
                    setattr(task, key, value.upper())
                else:
                    setattr(task, key, value)
                    
        task_repository.update_task(task)
        print(f"[TASK UPDATE] Updated Task ID: {task_id}")
        return task

    def delete_task(self, task_id: str) -> bool:
        """Deletes a Task by its ID."""
        res = task_repository.delete_task(task_id)
        print(f"[TASK DELETE] Deleted Task ID: {task_id}")
        return res

    def get_tasks(self) -> List[Task]:
        """Retrieves all Tasks."""
        print("[TASK RETRIEVE] Retrieving all tasks")
        return task_repository.find_all()

    def get_pending_tasks(self) -> List[Task]:
        """Retrieves PENDING and IN_PROGRESS tasks."""
        print("[TASK RETRIEVE] Retrieving pending and in-progress tasks")
        all_tasks = task_repository.find_all()
        return [t for t in all_tasks if t.status in ("PENDING", "IN_PROGRESS")]

    def get_overdue_tasks(self) -> List[Task]:
        """Retrieves all non-completed tasks whose due date has passed."""
        print("[TASK RETRIEVE] Retrieving overdue tasks")
        all_tasks = task_repository.find_all()
        today = datetime.date.today().strftime("%Y-%m-%d")
        overdue = []
        for t in all_tasks:
            if t.status in ("PENDING", "IN_PROGRESS") and t.due_date:
                # Basic string comparison for YYYY-MM-DD
                if t.due_date < today:
                    overdue.append(t)
        return overdue

# Singleton instance
task_service = TaskService()
