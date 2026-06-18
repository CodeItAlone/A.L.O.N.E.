from datetime import datetime
from typing import List, Optional
from core.human_memory.task_entity import Task

class TaskRepository:
    def create_task(self, task: Task) -> Task:
        """Persists a new Task in the database."""
        from core.human_memory import database
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not task.created_at:
            task.created_at = now
        if not task.updated_at:
            task.updated_at = now
        database.add_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date,
            project_id=task.project_id,
            goal_id=task.goal_id
        )
        return task

    def update_task(self, task: Task) -> Task:
        """Updates an existing Task in the database."""
        from core.human_memory import database
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.updated_at = now
        database.update_task(
            task_id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date,
            project_id=task.project_id,
            goal_id=task.goal_id
        )
        return task

    def delete_task(self, task_id: str) -> bool:
        """Deletes a Task by ID."""
        from core.human_memory import database
        database.delete_task(task_id)
        return True

    def find_by_id(self, task_id: str) -> Optional[Task]:
        """Finds a Task by its ID."""
        tasks = self.find_all()
        for t in tasks:
            if t.id == task_id:
                return t
        return None

    def find_all(self) -> List[Task]:
        """Retrieves all Tasks from the database."""
        from core.human_memory import database
        rows = database.get_tasks()
        return [Task.from_dict(row) for row in rows]

    def find_by_status(self, status: str) -> List[Task]:
        """Finds Tasks filtered by status."""
        from core.human_memory import database
        rows = database.get_tasks(status=status)
        return [Task.from_dict(row) for row in rows]

    def find_by_priority(self, priority: str) -> List[Task]:
        """Finds Tasks filtered by priority."""
        from core.human_memory import database
        rows = database.get_tasks(priority=priority)
        return [Task.from_dict(row) for row in rows]

# Singleton instance
task_repository = TaskRepository()
