"""Type definitions for pydantic-ai-todo."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Todo(BaseModel):
    """A todo item for task tracking.

    Attributes:
        id: Unique identifier for the todo (auto-generated 8-char hex string).
        content: The task description in imperative form (e.g., 'Implement feature X').
        status: Task status - 'pending', 'in_progress', 'completed', or 'blocked'.
        active_form: Present continuous form shown during execution
            (e.g., 'Implementing feature X').
        parent_id: ID of parent todo for subtask hierarchy (None for root tasks).
        depends_on: List of todo IDs that must be completed before this task.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    content: str
    status: Literal["pending", "in_progress", "completed", "blocked"]
    active_form: str
    parent_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class TodoItem(BaseModel):
    """Input model for the write_todos tool.

    This is the model that agents use when calling write_todos.
    It has the same fields as Todo but with Field descriptions for LLM guidance.
    """

    id: str | None = Field(
        default=None,
        description="Unique identifier for the todo. Auto-generated if not provided.",
    )
    content: str = Field(
        ..., description="The task description in imperative form (e.g., 'Implement feature X')"
    )
    status: Literal["pending", "in_progress", "completed", "blocked"] = Field(
        ..., description="Task status: pending, in_progress, completed, or blocked"
    )
    active_form: str = Field(
        ...,
        description="Present continuous form during execution (e.g., 'Implementing feature X')",
    )
    parent_id: str | None = Field(
        default=None,
        description="ID of parent todo for subtask hierarchy. None for root tasks.",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of todo IDs that must be completed before this task.",
    )


class TodoStatusUpdate(BaseModel):
    """Input model for a single entry of the update_todo_statuses batch tool.

    Each entry pairs a todo ID with the status it should transition to.
    """

    todo_id: str = Field(..., description="The ID of the todo to update (from read_todos).")
    status: Literal["pending", "in_progress", "completed", "blocked"] = Field(
        ...,
        description="New status: pending, in_progress, completed, or blocked.",
    )
