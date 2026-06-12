"""Tests for pydantic_ai_todo.types module."""

import pytest
from pydantic import ValidationError

from pydantic_ai_todo import Todo, TodoItem


class TestTodo:
    """Tests for Todo model."""

    def test_create_todo(self) -> None:
        """Test creating a valid todo."""
        todo = Todo(
            content="Implement feature X",
            status="pending",
            active_form="Implementing feature X",
        )
        assert todo.content == "Implement feature X"
        assert todo.status == "pending"
        assert todo.active_form == "Implementing feature X"
        assert len(todo.id) == 8  # auto-generated id

    def test_todo_with_custom_id(self) -> None:
        """Test creating a todo with custom id."""
        todo = Todo(
            id="abc12345",
            content="Task",
            status="pending",
            active_form="Working",
        )
        assert todo.id == "abc12345"

    def test_todo_id_auto_generated(self) -> None:
        """Test that each todo gets a unique auto-generated id."""
        todo1 = Todo(content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(content="Task 2", status="pending", active_form="Working")
        assert todo1.id != todo2.id

    def test_todo_status_values(self) -> None:
        """Test all valid status values."""
        for status in ["pending", "in_progress", "completed", "blocked"]:
            todo = Todo(content="Task", status=status, active_form="Working")  # type: ignore[arg-type]
            assert todo.status == status

    def test_todo_parent_id_default(self) -> None:
        """Test that parent_id defaults to None."""
        todo = Todo(content="Task", status="pending", active_form="Working")
        assert todo.parent_id is None

    def test_todo_parent_id_set(self) -> None:
        """Test setting parent_id."""
        todo = Todo(content="Task", status="pending", active_form="Working", parent_id="parent123")
        assert todo.parent_id == "parent123"

    def test_todo_depends_on_default(self) -> None:
        """Test that depends_on defaults to empty list."""
        todo = Todo(content="Task", status="pending", active_form="Working")
        assert todo.depends_on == []

    def test_todo_depends_on_set(self) -> None:
        """Test setting depends_on."""
        todo = Todo(
            content="Task", status="pending", active_form="Working", depends_on=["task1", "task2"]
        )
        assert todo.depends_on == ["task1", "task2"]

    def test_todo_invalid_status(self) -> None:
        """Test that invalid status raises validation error."""
        with pytest.raises(ValidationError):
            Todo(content="Task", status="invalid", active_form="Working")  # type: ignore[arg-type]

    def test_todo_model_dump(self) -> None:
        """Test serialization to dict."""
        todo = Todo(
            content="Task",
            status="in_progress",
            active_form="Working",
        )
        data = todo.model_dump()
        assert data["content"] == "Task"
        assert data["status"] == "in_progress"
        assert data["active_form"] == "Working"
        assert "id" in data
        assert len(data["id"]) == 8  # 8-char hex string


class TestTodoItem:
    """Tests for TodoItem model."""

    def test_create_todo_item(self) -> None:
        """Test creating a valid todo item."""
        item = TodoItem(
            content="Implement feature X",
            status="pending",
            active_form="Implementing feature X",
        )
        assert item.content == "Implement feature X"
        assert item.status == "pending"
        assert item.active_form == "Implementing feature X"

    def test_todo_item_status_defaults_to_pending(self) -> None:
        """status is optional and defaults to 'pending' so plan creation
        doesn't cost an extra validation round-trip."""
        item = TodoItem(content="Implement feature X", active_form="Implementing feature X")
        assert item.status == "pending"

    def test_todo_item_status_not_required_in_schema(self) -> None:
        """With a default, status must not be advertised as required."""
        schema = TodoItem.model_json_schema()
        assert "status" not in schema.get("required", [])

    def test_todo_item_field_descriptions(self) -> None:
        """Test that fields have descriptions for LLM guidance."""
        schema = TodoItem.model_json_schema()
        props = schema["properties"]

        assert "description" in props["content"]
        assert "description" in props["status"]
        assert "description" in props["active_form"]

    def test_todo_item_invalid_status(self) -> None:
        """Test that invalid status raises validation error."""
        with pytest.raises(ValidationError):
            TodoItem(content="Task", status="invalid", active_form="Working")  # type: ignore[arg-type]
