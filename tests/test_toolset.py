"""Tests for pydantic_ai_todo.toolset module."""

from typing import Any

import pytest
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import RunUsage

from pydantic_ai_todo import (
    AsyncMemoryStorage,
    Todo,
    TodoItem,
    TodoStatusUpdate,
    TodoStorage,
    create_todo_toolset,
    get_todo_system_prompt,
    get_todo_system_prompt_async,
)


def _ctx(deps: Any = None) -> RunContext[Any]:
    """Build a minimal RunContext for invoking tool functions directly in tests."""
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


class TestCreateTodoToolset:
    """Tests for create_todo_toolset factory."""

    def test_returns_function_toolset(self) -> None:
        """Test that factory returns a FunctionToolset."""
        toolset = create_todo_toolset()
        assert isinstance(toolset, FunctionToolset)

    def test_toolset_has_read_todos_tool(self) -> None:
        """Test that toolset has read_todos tool."""
        toolset = create_todo_toolset()
        assert "read_todos" in toolset.tools

    def test_toolset_has_write_todos_tool(self) -> None:
        """Test that toolset has write_todos tool."""
        toolset = create_todo_toolset()
        assert "write_todos" in toolset.tools

    def test_toolset_has_add_todo_tool(self) -> None:
        """Test that toolset has add_todo tool."""
        toolset = create_todo_toolset()
        assert "add_todo" in toolset.tools

    def test_toolset_has_update_todo_status_tool(self) -> None:
        """Test that toolset has update_todo_status tool."""
        toolset = create_todo_toolset()
        assert "update_todo_status" in toolset.tools

    def test_toolset_has_remove_todo_tool(self) -> None:
        """Test that toolset has remove_todo tool."""
        toolset = create_todo_toolset()
        assert "remove_todo" in toolset.tools

    def test_toolset_with_custom_id(self) -> None:
        """Test creating toolset with custom ID."""
        toolset = create_todo_toolset(id="my-todos")
        assert toolset.id == "my-todos"

    def test_toolset_with_custom_storage(self) -> None:
        """Test creating toolset with custom storage."""
        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)
        assert toolset is not None

    def test_default_storage_isolation(self) -> None:
        """Test that each toolset has isolated storage by default."""
        toolset1 = create_todo_toolset()
        toolset2 = create_todo_toolset()
        # They should be different instances
        assert toolset1 is not toolset2


class TestReadTodos:
    """Tests for read_todos tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_read_empty_todos(self, toolset: FunctionToolset[Any]) -> None:
        """Test reading when no todos exist."""
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "No todos" in result

    async def test_read_todos_with_items(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test reading todos with items."""
        storage.todos = [
            Todo(id="id1", content="Task 1", status="pending", active_form="Working on Task 1"),
            Todo(id="id2", content="Task 2", status="in_progress", active_form="Working on Task 2"),
            Todo(id="id3", content="Task 3", status="completed", active_form="Working on Task 3"),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]

        assert "Task 1" in result
        assert "Task 2" in result
        assert "Task 3" in result
        assert "[ ]" in result  # pending icon
        assert "[*]" in result  # in_progress icon
        assert "[x]" in result  # completed icon
        # Verify IDs are shown
        assert "[id1]" in result
        assert "[id2]" in result
        assert "[id3]" in result

    async def test_read_todos_summary(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that read_todos includes summary."""
        storage.todos = [
            Todo(content="Task 1", status="pending", active_form="Working"),
            Todo(content="Task 2", status="pending", active_form="Working"),
            Todo(content="Task 3", status="completed", active_form="Working"),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]

        assert "1 completed" in result
        assert "2 pending" in result


class TestWriteTodos:
    """Tests for write_todos tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_write_todos(self, storage: TodoStorage, toolset: FunctionToolset[Any]) -> None:
        """Test writing todos."""
        write_todos = toolset.tools["write_todos"]

        items = [
            TodoItem(content="Task 1", status="pending", active_form="Working on Task 1"),
            TodoItem(content="Task 2", status="in_progress", active_form="Working on Task 2"),
        ]

        result = await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].content == "Task 1"
        assert storage.todos[1].status == "in_progress"
        assert "Updated 2 todos" in result

    async def test_write_todos_overwrites(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that write_todos overwrites existing todos."""
        storage.todos = [
            Todo(content="Old task", status="pending", active_form="Working"),
        ]

        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(content="New task", status="completed", active_form="Working"),
        ]
        await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 1
        assert storage.todos[0].content == "New task"

    async def test_write_todos_returns_summary(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that write_todos returns status summary."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(content="Task 1", status="pending", active_form="Working"),
            TodoItem(content="Task 2", status="in_progress", active_form="Working"),
            TodoItem(content="Task 3", status="completed", active_form="Working"),
        ]
        result = await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert "3 todos" in result
        assert "1 completed" in result
        assert "1 in progress" in result
        assert "1 pending" in result

    async def test_write_todos_with_custom_id(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with custom IDs preserves them."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="custom1", content="Task 1", status="pending", active_form="Working"),
            TodoItem(id="custom2", content="Task 2", status="pending", active_form="Working"),
        ]
        await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].id == "custom1"
        assert storage.todos[1].id == "custom2"


class TestGetTodoSystemPrompt:
    """Tests for get_todo_system_prompt function."""

    def test_prompt_without_storage(self) -> None:
        """Test system prompt without storage."""
        prompt = get_todo_system_prompt()
        assert "Task Management" in prompt
        assert "write_todos" in prompt

    def test_prompt_with_empty_storage(self) -> None:
        """Test system prompt with empty storage."""
        storage = TodoStorage()
        prompt = get_todo_system_prompt(storage)
        assert "Task Management" in prompt
        # Should not include "Current Todos" section
        assert "Current Todos" not in prompt

    def test_prompt_with_todos(self) -> None:
        """Test system prompt includes current todos."""
        storage = TodoStorage()
        storage.todos = [
            Todo(content="Task 1", status="pending", active_form="Working"),
            Todo(content="Task 2", status="in_progress", active_form="Working"),
        ]

        prompt = get_todo_system_prompt(storage)

        assert "Current Todos" in prompt
        assert "Task 1" in prompt
        assert "Task 2" in prompt
        assert "[ ]" in prompt  # pending
        assert "[*]" in prompt  # in_progress

    def test_prompt_todos_status_icons(self) -> None:
        """Test that prompt shows correct status icons."""
        storage = TodoStorage()
        storage.todos = [
            Todo(content="Pending", status="pending", active_form="Working"),
            Todo(content="In Progress", status="in_progress", active_form="Working"),
            Todo(content="Completed", status="completed", active_form="Working"),
        ]

        prompt = get_todo_system_prompt(storage)

        assert "[ ]" in prompt
        assert "Pending" in prompt
        assert "[*]" in prompt
        assert "In Progress" in prompt
        assert "[x]" in prompt
        assert "Completed" in prompt


class TestAddTodo:
    """Tests for add_todo tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_add_todo_to_empty_list(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a todo to an empty list."""
        add_todo = toolset.tools["add_todo"]
        result = await add_todo.function(  # type: ignore[call-arg]
            _ctx(), content="New task", active_form="Working on new task"
        )

        assert len(storage.todos) == 1
        assert storage.todos[0].content == "New task"
        assert storage.todos[0].active_form == "Working on new task"
        assert storage.todos[0].status == "pending"
        assert "Added todo" in result
        assert storage.todos[0].id in result

    async def test_add_todo_to_existing_list(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a todo to an existing list."""
        storage.todos = [
            Todo(content="Existing task", status="pending", active_form="Working"),
        ]

        add_todo = toolset.tools["add_todo"]
        await add_todo.function(_ctx(), content="New task", active_form="Working on new task")  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].content == "Existing task"
        assert storage.todos[1].content == "New task"

    async def test_add_todo_returns_id(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that add_todo returns the new todo's ID."""
        add_todo = toolset.tools["add_todo"]
        result = await add_todo.function(_ctx(), content="Task", active_form="Working")  # type: ignore[call-arg]

        assert "ID:" in result
        assert storage.todos[0].id in result


class TestUpdateTodoStatus:
    """Tests for update_todo_status tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_update_status_to_in_progress(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status to in_progress."""
        todo = Todo(id="abc123", content="Task", status="pending", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="abc123", status="in_progress")  # type: ignore[call-arg]

        assert storage.todos[0].status == "in_progress"
        assert "Updated todo" in result
        assert "in_progress" in result

    async def test_update_status_to_completed(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status to completed."""
        todo = Todo(id="abc123", content="Task", status="in_progress", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="abc123", status="completed")  # type: ignore[call-arg]

        assert storage.todos[0].status == "completed"
        assert "completed" in result

    async def test_update_status_to_pending(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status back to pending."""
        todo = Todo(id="abc123", content="Task", status="in_progress", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="abc123", status="pending")  # type: ignore[call-arg]

        assert storage.todos[0].status == "pending"
        assert "pending" in result

    async def test_update_status_not_found_empty(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status for non-existent todo in empty list."""
        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="nonexistent", status="completed")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_update_status_not_found_with_items(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status for non-existent todo when other todos exist."""
        storage.todos = [
            Todo(id="other1", content="Task 1", status="pending", active_form="Working"),
            Todo(id="other2", content="Task 2", status="pending", active_form="Working"),
        ]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="nonexistent", status="completed")  # type: ignore[call-arg]

        assert "not found" in result
        # Verify other todos unchanged
        assert len(storage.todos) == 2
        assert all(t.status == "pending" for t in storage.todos)

    async def test_update_status_invalid_status(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating with invalid status."""
        todo = Todo(id="abc123", content="Task", status="pending", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="abc123", status="invalid")  # type: ignore[call-arg]

        assert "Invalid status" in result
        assert storage.todos[0].status == "pending"  # unchanged


class TestRemoveTodo:
    """Tests for remove_todo tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    async def test_remove_existing_todo(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing an existing todo."""
        todo = Todo(id="abc123", content="Task to remove", status="pending", active_form="Working")
        storage.todos = [todo]

        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(_ctx(), todo_id="abc123")  # type: ignore[call-arg]

        assert len(storage.todos) == 0
        assert "Removed todo" in result
        assert "abc123" in result

    async def test_remove_todo_from_multiple(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing one todo from multiple."""
        storage.todos = [
            Todo(id="id1", content="Task 1", status="pending", active_form="Working"),
            Todo(id="id2", content="Task 2", status="pending", active_form="Working"),
            Todo(id="id3", content="Task 3", status="pending", active_form="Working"),
        ]

        remove_todo = toolset.tools["remove_todo"]
        await remove_todo.function(_ctx(), todo_id="id2")  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[0].id == "id1"
        assert storage.todos[1].id == "id3"

    async def test_remove_nonexistent_todo(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing a non-existent todo."""
        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(_ctx(), todo_id="nonexistent")  # type: ignore[call-arg]

        assert "not found" in result


class TestAsyncStorageToolset:
    """Tests for toolset with async storage."""

    @pytest.fixture
    def storage(self) -> AsyncMemoryStorage:
        """Create an async storage instance."""
        return AsyncMemoryStorage()

    @pytest.fixture
    def toolset(self, storage: AsyncMemoryStorage) -> FunctionToolset[Any]:
        """Create a toolset with async storage."""
        return create_todo_toolset(async_storage=storage)

    def test_returns_function_toolset(self, toolset: FunctionToolset[Any]) -> None:
        """Test that factory returns a FunctionToolset."""
        assert isinstance(toolset, FunctionToolset)

    def test_toolset_has_all_tools(self, toolset: FunctionToolset[Any]) -> None:
        """Test that toolset has all expected tools."""
        assert "read_todos" in toolset.tools
        assert "write_todos" in toolset.tools
        assert "add_todo" in toolset.tools
        assert "update_todo_status" in toolset.tools
        assert "remove_todo" in toolset.tools

    async def test_read_empty_todos(self, toolset: FunctionToolset[Any]) -> None:
        """Test reading when no todos exist."""
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "No todos" in result

    async def test_write_and_read_todos(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing and reading todos with async storage."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(content="Task 1", status="pending", active_form="Working on Task 1"),
            TodoItem(content="Task 2", status="in_progress", active_form="Working on Task 2"),
        ]
        await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        # Verify in storage
        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[0].content == "Task 1"
        assert todos[1].status == "in_progress"

        # Verify via read
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "Task 1" in result
        assert "Task 2" in result

    async def test_add_todo(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a todo with async storage."""
        add_todo = toolset.tools["add_todo"]
        result = await add_todo.function(_ctx(), content="New task", active_form="Working")  # type: ignore[call-arg]

        assert "Added todo" in result
        todos = await storage.get_todos()
        assert len(todos) == 1
        assert todos[0].content == "New task"

    async def test_update_todo_status(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating todo status with async storage."""
        # Add a todo first
        todo = Todo(id="test123", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="test123", status="completed")  # type: ignore[call-arg]

        assert "Updated todo" in result
        updated = await storage.get_todo("test123")
        assert updated is not None
        assert updated.status == "completed"

    async def test_update_todo_status_not_found(self, toolset: FunctionToolset[Any]) -> None:
        """Test updating non-existent todo."""
        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="nonexistent", status="completed")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_remove_todo(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test removing a todo with async storage."""
        # Add a todo first
        todo = Todo(id="test123", content="Task to remove", status="pending", active_form="Working")
        await storage.add_todo(todo)

        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(_ctx(), todo_id="test123")  # type: ignore[call-arg]

        assert "Removed todo" in result
        assert "test123" in result

        todos = await storage.get_todos()
        assert len(todos) == 0

    async def test_remove_todo_not_found(self, toolset: FunctionToolset[Any]) -> None:
        """Test removing non-existent todo."""
        remove_todo = toolset.tools["remove_todo"]
        result = await remove_todo.function(_ctx(), todo_id="nonexistent")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_write_todos_with_custom_id(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with custom IDs preserves them (async)."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="custom1", content="Task 1", status="pending", active_form="Working"),
            TodoItem(id="custom2", content="Task 2", status="pending", active_form="Working"),
        ]
        await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[0].id == "custom1"
        assert todos[1].id == "custom2"


class TestGetTodoSystemPromptAsync:
    """Tests for get_todo_system_prompt_async function."""

    async def test_prompt_without_storage(self) -> None:
        """Test system prompt without storage."""
        prompt = await get_todo_system_prompt_async()
        assert "Task Management" in prompt
        assert "write_todos" in prompt

    async def test_prompt_with_empty_storage(self) -> None:
        """Test system prompt with empty storage."""
        storage = AsyncMemoryStorage()
        prompt = await get_todo_system_prompt_async(storage)
        assert "Task Management" in prompt
        assert "Current Todos" not in prompt

    async def test_prompt_with_todos(self) -> None:
        """Test system prompt includes current todos."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(content="Task 1", status="pending", active_form="Working"))
        await storage.add_todo(Todo(content="Task 2", status="in_progress", active_form="Working"))

        prompt = await get_todo_system_prompt_async(storage)

        assert "Current Todos" in prompt
        assert "Task 1" in prompt
        assert "Task 2" in prompt
        assert "[ ]" in prompt  # pending
        assert "[*]" in prompt  # in_progress

    async def test_prompt_todos_status_icons(self) -> None:
        """Test that prompt shows correct status icons."""
        storage = AsyncMemoryStorage()
        await storage.add_todo(Todo(content="Pending", status="pending", active_form="Working"))
        await storage.add_todo(
            Todo(content="In Progress", status="in_progress", active_form="Working")
        )
        await storage.add_todo(Todo(content="Completed", status="completed", active_form="Working"))

        prompt = await get_todo_system_prompt_async(storage)

        assert "[ ]" in prompt
        assert "Pending" in prompt
        assert "[*]" in prompt
        assert "In Progress" in prompt
        assert "[x]" in prompt
        assert "Completed" in prompt


class TestSubtasksEnabled:
    """Tests for toolset with enable_subtasks=True."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    def test_toolset_has_add_subtask_tool(self, toolset: FunctionToolset[Any]) -> None:
        """Test that toolset with subtasks has add_subtask tool."""
        assert "add_subtask" in toolset.tools

    def test_toolset_has_set_dependency_tool(self, toolset: FunctionToolset[Any]) -> None:
        """Test that toolset with subtasks has set_dependency tool."""
        assert "set_dependency" in toolset.tools

    def test_toolset_has_get_available_tasks_tool(self, toolset: FunctionToolset[Any]) -> None:
        """Test that toolset with subtasks has get_available_tasks tool."""
        assert "get_available_tasks" in toolset.tools

    def test_toolset_without_subtasks_has_no_extra_tools(self) -> None:
        """Test that toolset without subtasks doesn't have subtask tools."""
        toolset = create_todo_toolset()
        assert "add_subtask" not in toolset.tools
        assert "set_dependency" not in toolset.tools
        assert "get_available_tasks" not in toolset.tools


class TestAddSubtask:
    """Tests for add_subtask tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_add_subtask(self, storage: TodoStorage, toolset: FunctionToolset[Any]) -> None:
        """Test adding a subtask to an existing todo."""
        parent = Todo(id="parent1", content="Parent task", status="pending", active_form="Working")
        storage.todos = [parent]

        add_subtask = toolset.tools["add_subtask"]
        result = await add_subtask.function(_ctx(),
            parent_id="parent1",  # pyright: ignore[reportCallIssue]
            content="Subtask",
            active_form="Working on subtask",
        )

        assert len(storage.todos) == 2
        assert "Added subtask" in result
        subtask = storage.todos[1]
        assert subtask.parent_id == "parent1"
        assert subtask.content == "Subtask"

    async def test_add_subtask_parent_not_found(self, toolset: FunctionToolset[Any]) -> None:
        """Test adding subtask to non-existent parent."""
        add_subtask = toolset.tools["add_subtask"]
        result = await add_subtask.function(_ctx(),
            parent_id="nonexistent",  # pyright: ignore[reportCallIssue]
            content="Subtask",
            active_form="Working",
        )

        assert "not found" in result


class TestSetDependency:
    """Tests for set_dependency tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_set_dependency(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test setting a dependency between todos."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        storage.todos = [todo1, todo2]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "Added dependency" in result
        assert "task1" in storage.todos[1].depends_on

    async def test_set_dependency_auto_blocks(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that setting dependency on incomplete task auto-blocks."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        storage.todos = [todo1, todo2]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "blocked" in result.lower()
        assert storage.todos[1].status == "blocked"

    async def test_set_dependency_not_blocked_if_completed(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that dependency on completed task doesn't block."""
        todo1 = Todo(id="task1", content="Task 1", status="completed", active_form="Working")
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        storage.todos = [todo1, todo2]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "blocked" not in result.lower()
        assert storage.todos[1].status == "pending"

    async def test_set_dependency_self_reference(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that a todo cannot depend on itself."""
        todo = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        storage.todos = [todo]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task1", depends_on_id="task1")  # type: ignore[call-arg]

        assert "cannot depend on itself" in result.lower()

    async def test_set_dependency_cycle_detection(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that cycle dependencies are prevented."""
        todo1 = Todo(
            id="task1",
            content="Task 1",
            status="pending",
            active_form="Working",
            depends_on=["task2"],
        )
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        storage.todos = [todo1, todo2]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "cycle" in result.lower()

    async def test_set_dependency_transitive_cycle_detection(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that transitive cycle dependencies are prevented."""
        # A -> B -> C, then try to add C -> A
        todo1 = Todo(
            id="task1",
            content="Task 1",
            status="pending",
            active_form="Working",
            depends_on=["task2"],
        )
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task3"],
        )
        todo3 = Todo(id="task3", content="Task 3", status="pending", active_form="Working")
        storage.todos = [todo1, todo2, todo3]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task3", depends_on_id="task1")  # type: ignore[call-arg]

        assert "cycle" in result.lower()

    async def test_set_dependency_diamond_shape(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test diamond-shaped dependencies (A depends on B and C, both depend on D)."""
        todo_a = Todo(
            id="A",
            content="Task A",
            status="pending",
            active_form="Working",
            depends_on=["B", "C"],
        )
        todo_b = Todo(
            id="B",
            content="Task B",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_c = Todo(
            id="C",
            content="Task C",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_d = Todo(id="D", content="Task D", status="pending", active_form="Working")
        storage.todos = [todo_a, todo_b, todo_c, todo_d]

        # Adding D -> A would create a cycle through both B and C
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="D", depends_on_id="A")  # type: ignore[call-arg]

        assert "cycle" in result.lower()

    async def test_set_dependency_diamond_no_cycle(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test diamond-shaped graph where dependency is allowed (no cycle).

        This tests the "already visited" branch in cycle detection.
        Graph: A depends on B and C, both B and C depend on D.
        Adding A -> F (where F is unrelated) should be allowed, even though
        the traversal visits D twice through different paths.
        """
        todo_a = Todo(
            id="A",
            content="Task A",
            status="pending",
            active_form="Working",
            depends_on=["B", "C"],
        )
        todo_b = Todo(
            id="B",
            content="Task B",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_c = Todo(
            id="C",
            content="Task C",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_d = Todo(id="D", content="Task D", status="completed", active_form="Working")
        todo_f = Todo(id="F", content="Task F", status="completed", active_form="Working")
        storage.todos = [todo_a, todo_b, todo_c, todo_d, todo_f]

        # Adding F -> A is allowed (no cycle) - F is unrelated to A's dependency graph
        # Traversal from A: A -> B -> D (visited) -> C -> D (already visited!)
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="F", depends_on_id="A")  # type: ignore[call-arg]

        # Should succeed (no cycle detected)
        assert "Added dependency" in result
        # Verify F now depends on A
        todo_f_updated = next(t for t in storage.todos if t.id == "F")
        assert "A" in todo_f_updated.depends_on

    async def test_set_dependency_with_dangling_reference(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test cycle detection with dangling reference in depends_on.

        This covers the branch where a todo in depends_on list doesn't exist.
        """
        # A depends on B (which doesn't exist)
        todo_a = Todo(
            id="A",
            content="Task A",
            status="pending",
            active_form="Working",
            depends_on=["nonexistent"],
        )
        todo_c = Todo(id="C", content="Task C", status="completed", active_form="Working")
        storage.todos = [todo_a, todo_c]

        # Adding C -> A should traverse A's dependencies, hit "nonexistent" (not found), continue
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="C", depends_on_id="A")  # type: ignore[call-arg]

        # Should succeed (no cycle)
        assert "Added dependency" in result

    async def test_set_dependency_already_exists(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that duplicate dependencies are rejected."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task1"],
        )
        storage.todos = [todo1, todo2]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "already exists" in result.lower()

    async def test_set_dependency_todo_not_found(self, toolset: FunctionToolset[Any]) -> None:
        """Test dependency when todo not found."""
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="nonexistent", depends_on_id="other")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_set_dependency_depends_on_not_found(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test dependency when depends_on todo not found."""
        todo = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        storage.todos = [todo]

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task1", depends_on_id="nonexistent")  # type: ignore[call-arg]

        assert "not found" in result


class TestGetAvailableTasks:
    """Tests for get_available_tasks tool."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_get_available_tasks_all_available(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test getting available tasks when none are blocked."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="pending", active_form="Working"),
            Todo(id="task2", content="Task 2", status="in_progress", active_form="Working"),
        ]

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "Task 1" in result
        assert "Task 2" in result

    async def test_get_available_tasks_excludes_blocked(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that blocked tasks are excluded."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="pending", active_form="Working"),
            Todo(id="task2", content="Task 2", status="blocked", active_form="Working"),
        ]

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "Task 1" in result
        assert "Task 2" not in result

    async def test_get_available_tasks_excludes_completed(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that completed tasks are excluded."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="completed", active_form="Working"),
            Todo(id="task2", content="Task 2", status="pending", active_form="Working"),
        ]

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "Task 1" not in result
        assert "Task 2" in result

    async def test_get_available_tasks_excludes_tasks_with_incomplete_deps(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that tasks with incomplete dependencies are excluded."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Task 2",
                status="pending",
                active_form="Working",
                depends_on=["task1"],
            ),
        ]

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "Task 1" in result
        assert "Task 2" not in result

    async def test_get_available_tasks_none_available(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test message when no tasks are available."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="completed", active_form="Working"),
        ]

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "No available tasks" in result


class TestReadTodosHierarchical:
    """Tests for read_todos with hierarchical view."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_read_todos_flat_view(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test reading todos in flat view."""
        storage.todos = [
            Todo(id="task1", content="Parent", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Child",
                status="pending",
                active_form="Working",
                parent_id="task1",
            ),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=False)  # type: ignore[call-arg]

        assert "Parent" in result
        assert "Child" in result
        assert "(subtask of: task1)" in result

    async def test_read_todos_hierarchical_view(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test reading todos in hierarchical view."""
        storage.todos = [
            Todo(id="task1", content="Parent", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Child",
                status="pending",
                active_form="Working",
                parent_id="task1",
            ),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=True)  # type: ignore[call-arg]

        assert "hierarchical view" in result.lower()
        assert "Parent" in result
        assert "Child" in result

    async def test_read_todos_hierarchical_with_dependencies(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test hierarchical view shows dependencies."""
        storage.todos = [
            Todo(id="task1", content="Parent", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Child with dep",
                status="pending",
                active_form="Working",
                parent_id="task1",
                depends_on=["task3"],
            ),
            Todo(id="task3", content="Dependency", status="pending", active_form="Working"),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=True)  # type: ignore[call-arg]

        assert "depends on: task3" in result

    async def test_read_todos_hierarchical_nested_subtasks(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test hierarchical view with nested subtasks."""
        storage.todos = [
            Todo(id="task1", content="Root", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Level 1",
                status="pending",
                active_form="Working",
                parent_id="task1",
            ),
            Todo(
                id="task3",
                content="Level 2",
                status="pending",
                active_form="Working",
                parent_id="task2",
            ),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=True)  # type: ignore[call-arg]

        assert "Root" in result
        assert "Level 1" in result
        assert "Level 2" in result

    async def test_read_todos_empty_with_subtasks(self, toolset: FunctionToolset[Any]) -> None:
        """Test reading empty todo list with subtasks enabled."""
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "No todos" in result

    async def test_read_todos_shows_blocked_status(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that blocked status is shown in read_todos."""
        storage.todos = [
            Todo(id="task1", content="Blocked Task", status="blocked", active_form="Working"),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]

        assert "[!]" in result
        assert "blocked" in result.lower()

    async def test_read_todos_shows_dependencies(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that dependencies are shown in read_todos."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Task 2",
                status="pending",
                active_form="Working",
                depends_on=["task1"],
            ),
        ]

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]

        assert "depends on: task1" in result


class TestWriteTodosWithSubtasks:
    """Tests for write_todos with subtasks enabled."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_write_todos_with_parent_id(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with parent_id."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="task1", content="Parent", status="pending", active_form="Working"),
            TodoItem(
                id="task2",
                content="Child",
                status="pending",
                active_form="Working",
                parent_id="task1",
            ),
        ]
        await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[1].parent_id == "task1"

    async def test_write_todos_with_depends_on(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with depends_on."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="task1", content="First", status="pending", active_form="Working"),
            TodoItem(
                id="task2",
                content="Second",
                status="pending",
                active_form="Working",
                depends_on=["task1"],
            ),
        ]
        await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert len(storage.todos) == 2
        assert storage.todos[1].depends_on == ["task1"]

    async def test_write_todos_with_blocked_status(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test writing todos with blocked status shows in summary."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(id="task1", content="Blocked", status="blocked", active_form="Working"),
            TodoItem(id="task2", content="Pending", status="pending", active_form="Working"),
        ]
        result = await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert "1 blocked" in result


class TestUpdateTodoStatusWithSubtasks:
    """Tests for update_todo_status with subtasks enabled."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_update_status_to_blocked(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test updating status to blocked."""
        todo = Todo(id="task1", content="Task", status="pending", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task1", status="blocked")  # type: ignore[call-arg]

        assert storage.todos[0].status == "blocked"
        assert "blocked" in result

    async def test_cannot_start_blocked_task(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that tasks with incomplete dependencies cannot be started."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task1"],
        )
        storage.todos = [todo1, todo2]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task2", status="in_progress")  # type: ignore[call-arg]

        assert "Cannot start" in result
        assert "incomplete dependencies" in result
        assert storage.todos[1].status == "pending"

    async def test_can_start_task_with_completed_deps(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that tasks with completed dependencies can be started."""
        todo1 = Todo(id="task1", content="Task 1", status="completed", active_form="Working")
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task1"],
        )
        storage.todos = [todo1, todo2]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task2", status="in_progress")  # type: ignore[call-arg]

        assert storage.todos[1].status == "in_progress"
        assert "in_progress" in result

    async def test_update_status_invalid_with_subtasks(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test invalid status with subtasks enabled."""
        todo = Todo(id="task1", content="Task", status="pending", active_form="Working")
        storage.todos = [todo]

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task1", status="invalid")  # type: ignore[call-arg]

        assert "Invalid status" in result


class TestAsyncSubtasksToolset:
    """Tests for async toolset with subtasks enabled."""

    @pytest.fixture
    def storage(self) -> AsyncMemoryStorage:
        """Create an async storage instance."""
        return AsyncMemoryStorage()

    @pytest.fixture
    def toolset(self, storage: AsyncMemoryStorage) -> FunctionToolset[Any]:
        """Create an async toolset with subtasks enabled."""
        return create_todo_toolset(async_storage=storage, enable_subtasks=True)

    def test_toolset_has_subtask_tools(self, toolset: FunctionToolset[Any]) -> None:
        """Test that async toolset with subtasks has all subtask tools."""
        assert "add_subtask" in toolset.tools
        assert "set_dependency" in toolset.tools
        assert "get_available_tasks" in toolset.tools

    async def test_add_subtask_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test adding a subtask with async storage."""
        parent = Todo(id="parent1", content="Parent", status="pending", active_form="Working")
        await storage.add_todo(parent)

        add_subtask = toolset.tools["add_subtask"]
        result = await add_subtask.function(_ctx(),
            parent_id="parent1",  # pyright: ignore[reportCallIssue]
            content="Subtask",
            active_form="Working",
        )

        assert "Added subtask" in result
        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[1].parent_id == "parent1"

    async def test_add_subtask_parent_not_found_async(self, toolset: FunctionToolset[Any]) -> None:
        """Test adding subtask to non-existent parent with async storage."""
        add_subtask = toolset.tools["add_subtask"]
        result = await add_subtask.function(_ctx(),
            parent_id="nonexistent",  # pyright: ignore[reportCallIssue]
            content="Subtask",
            active_form="Working",
        )

        assert "not found" in result

    async def test_set_dependency_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test setting dependency with async storage."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "Added dependency" in result
        todo = await storage.get_todo("task2")
        assert todo is not None
        assert "task1" in todo.depends_on

    async def test_set_dependency_self_reference_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test self-dependency with async storage."""
        todo = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        await storage.add_todo(todo)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task1", depends_on_id="task1")  # type: ignore[call-arg]

        assert "cannot depend on itself" in result.lower()

    async def test_set_dependency_cycle_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test cycle detection with async storage."""
        todo1 = Todo(
            id="task1",
            content="Task 1",
            status="pending",
            active_form="Working",
            depends_on=["task2"],
        )
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "cycle" in result.lower()

    async def test_set_dependency_diamond_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test diamond-shaped dependencies with async storage."""
        todo_a = Todo(
            id="A",
            content="Task A",
            status="pending",
            active_form="Working",
            depends_on=["B", "C"],
        )
        todo_b = Todo(
            id="B",
            content="Task B",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_c = Todo(
            id="C",
            content="Task C",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_d = Todo(id="D", content="Task D", status="pending", active_form="Working")
        await storage.add_todo(todo_a)
        await storage.add_todo(todo_b)
        await storage.add_todo(todo_c)
        await storage.add_todo(todo_d)

        # Adding D -> A would create a cycle through both B and C
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="D", depends_on_id="A")  # type: ignore[call-arg]

        assert "cycle" in result.lower()

    async def test_set_dependency_diamond_no_cycle_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test diamond-shaped graph where dependency is allowed (no cycle) with async.

        This tests the "already visited" branch in cycle detection.
        """
        todo_a = Todo(
            id="A",
            content="Task A",
            status="pending",
            active_form="Working",
            depends_on=["B", "C"],
        )
        todo_b = Todo(
            id="B",
            content="Task B",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_c = Todo(
            id="C",
            content="Task C",
            status="pending",
            active_form="Working",
            depends_on=["D"],
        )
        todo_d = Todo(id="D", content="Task D", status="completed", active_form="Working")
        todo_f = Todo(id="F", content="Task F", status="completed", active_form="Working")
        await storage.add_todo(todo_a)
        await storage.add_todo(todo_b)
        await storage.add_todo(todo_c)
        await storage.add_todo(todo_d)
        await storage.add_todo(todo_f)

        # Adding F -> A is allowed (no cycle)
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="F", depends_on_id="A")  # type: ignore[call-arg]

        # Should succeed
        assert "Added dependency" in result
        todo_f_updated = await storage.get_todo("F")
        assert todo_f_updated is not None
        assert "A" in todo_f_updated.depends_on

    async def test_set_dependency_with_dangling_reference_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test cycle detection with dangling reference in depends_on (async)."""
        todo_a = Todo(
            id="A",
            content="Task A",
            status="pending",
            active_form="Working",
            depends_on=["nonexistent"],
        )
        todo_c = Todo(id="C", content="Task C", status="completed", active_form="Working")
        await storage.add_todo(todo_a)
        await storage.add_todo(todo_c)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="C", depends_on_id="A")  # type: ignore[call-arg]

        assert "Added dependency" in result

    async def test_set_dependency_already_exists_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test duplicate dependency with async storage."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task1"],
        )
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "already exists" in result.lower()

    async def test_set_dependency_not_found_async(self, toolset: FunctionToolset[Any]) -> None:
        """Test dependency when todo not found with async storage."""
        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="nonexistent", depends_on_id="other")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_set_dependency_depends_on_not_found_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test dependency when depends_on not found with async storage."""
        todo = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        await storage.add_todo(todo)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task1", depends_on_id="nonexistent")  # type: ignore[call-arg]

        assert "not found" in result

    async def test_set_dependency_auto_blocks_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that setting dependency on incomplete task auto-blocks with async storage."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "blocked" in result.lower()
        todo = await storage.get_todo("task2")
        assert todo is not None
        assert todo.status == "blocked"

    async def test_set_dependency_completed_dep_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test setting dependency on completed task with async storage."""
        todo1 = Todo(id="task1", content="Task 1", status="completed", active_form="Working")
        todo2 = Todo(id="task2", content="Task 2", status="pending", active_form="Working")
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        set_dep = toolset.tools["set_dependency"]
        result = await set_dep.function(_ctx(), todo_id="task2", depends_on_id="task1")  # type: ignore[call-arg]

        assert "blocked" not in result.lower()
        todo = await storage.get_todo("task2")
        assert todo is not None
        assert todo.status == "pending"

    async def test_get_available_tasks_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test get_available_tasks with async storage."""
        await storage.add_todo(
            Todo(id="task1", content="Available", status="pending", active_form="Working")
        )
        await storage.add_todo(
            Todo(id="task2", content="Blocked", status="blocked", active_form="Working")
        )

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "Available" in result
        assert "Blocked" not in result

    async def test_get_available_tasks_with_deps_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test get_available_tasks excludes tasks with incomplete deps."""
        await storage.add_todo(
            Todo(id="task1", content="Available", status="pending", active_form="Working")
        )
        await storage.add_todo(
            Todo(
                id="task2",
                content="Dependent",
                status="pending",
                active_form="Working",
                depends_on=["task1"],
            )
        )

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "Available" in result
        assert "Dependent" not in result

    async def test_get_available_tasks_none_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test get_available_tasks when none available."""
        await storage.add_todo(
            Todo(id="task1", content="Completed", status="completed", active_form="Working")
        )

        get_available = toolset.tools["get_available_tasks"]
        result = await get_available.function(_ctx())  # type: ignore[call-arg]

        assert "No available tasks" in result

    async def test_read_todos_hierarchical_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test hierarchical view with async storage."""
        await storage.add_todo(
            Todo(id="task1", content="Parent", status="pending", active_form="Working")
        )
        await storage.add_todo(
            Todo(
                id="task2",
                content="Child",
                status="pending",
                active_form="Working",
                parent_id="task1",
            )
        )

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=True)  # type: ignore[call-arg]

        assert "hierarchical view" in result.lower()
        assert "Parent" in result
        assert "Child" in result

    async def test_read_todos_flat_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test flat view with async storage shows subtask info."""
        await storage.add_todo(
            Todo(id="task1", content="Parent", status="pending", active_form="Working")
        )
        await storage.add_todo(
            Todo(
                id="task2",
                content="Child",
                status="pending",
                active_form="Working",
                parent_id="task1",
                depends_on=["task1"],
            )
        )

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=False)  # type: ignore[call-arg]

        assert "subtask of: task1" in result
        assert "depends on: task1" in result

    async def test_read_todos_empty_async(self, toolset: FunctionToolset[Any]) -> None:
        """Test reading empty todo list with async storage."""
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "No todos" in result

    async def test_read_todos_with_blocked_shows_in_summary_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test that blocked status shows in summary with async storage."""
        await storage.add_todo(
            Todo(id="task1", content="Blocked Task", status="blocked", active_form="Working")
        )
        await storage.add_todo(
            Todo(id="task2", content="Pending Task", status="pending", active_form="Working")
        )

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]

        assert "1 blocked" in result
        assert "[!]" in result  # blocked icon

    async def test_read_todos_hierarchical_with_deps_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test hierarchical view shows dependencies in async storage."""
        await storage.add_todo(
            Todo(id="task1", content="Parent", status="pending", active_form="Working")
        )
        await storage.add_todo(
            Todo(
                id="task2",
                content="Child with dep",
                status="pending",
                active_form="Working",
                parent_id="task1",
                depends_on=["task3"],
            )
        )
        await storage.add_todo(
            Todo(id="task3", content="Dependency", status="pending", active_form="Working")
        )

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(), hierarchical=True)  # type: ignore[call-arg]

        assert "depends on: task3" in result

    async def test_write_todos_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test write_todos with async storage and subtasks."""
        write_todos = toolset.tools["write_todos"]
        items = [
            TodoItem(
                id="task1",
                content="Parent",
                status="pending",
                active_form="Working",
            ),
            TodoItem(
                id="task2",
                content="Child",
                status="blocked",
                active_form="Working",
                parent_id="task1",
                depends_on=["task1"],
            ),
        ]
        result = await write_todos.function(_ctx(), todos=items)  # type: ignore[call-arg]

        assert "1 blocked" in result
        todos = await storage.get_todos()
        assert len(todos) == 2
        assert todos[1].parent_id == "task1"
        assert todos[1].depends_on == ["task1"]

    async def test_update_status_blocked_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test update_todo_status to blocked with async storage."""
        todo = Todo(id="task1", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task1", status="blocked")  # type: ignore[call-arg]

        assert "blocked" in result
        updated = await storage.get_todo("task1")
        assert updated is not None
        assert updated.status == "blocked"

    async def test_cannot_start_blocked_task_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test cannot start task with incomplete deps in async storage."""
        todo1 = Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task1"],
        )
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task2", status="in_progress")  # type: ignore[call-arg]

        assert "Cannot start" in result
        updated = await storage.get_todo("task2")
        assert updated is not None
        assert updated.status == "pending"

    async def test_can_start_task_with_completed_deps_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test can start task when all dependencies are completed.

        This covers the branch where _is_blocked returns False because deps are done.
        """
        todo1 = Todo(id="task1", content="Task 1", status="completed", active_form="Working")
        todo2 = Todo(
            id="task2",
            content="Task 2",
            status="pending",
            active_form="Working",
            depends_on=["task1"],
        )
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task2", status="in_progress")  # type: ignore[call-arg]

        # Should succeed
        assert "in_progress" in result
        updated = await storage.get_todo("task2")
        assert updated is not None
        assert updated.status == "in_progress"

    async def test_update_status_invalid_async(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Test invalid status with async storage."""
        todo = Todo(id="task1", content="Task", status="pending", active_form="Working")
        await storage.add_todo(todo)

        update_status = toolset.tools["update_todo_status"]
        result = await update_status.function(_ctx(), todo_id="task1", status="invalid")  # type: ignore[call-arg]

        assert "Invalid status" in result


class TestReadTodosAllCompletedHint:
    """Tests for the 'all completed' hint in read_todos output."""

    async def test_sync_all_completed_shows_hint(self) -> None:
        """Sync read_todos shows 'Do NOT call' hint when all tasks completed."""
        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)

        storage.todos = [
            Todo(id="1", content="Done", status="completed", active_form="Done"),
        ]
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "Do NOT call read_todos again" in result

    async def test_sync_not_all_completed_no_hint(self) -> None:
        """Sync read_todos does NOT show hint when tasks are pending."""
        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)

        storage.todos = [
            Todo(id="1", content="Done", status="completed", active_form="Done"),
            Todo(id="2", content="Todo", status="pending", active_form="Doing"),
        ]
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "Do NOT call read_todos again" not in result

    async def test_sync_subtasks_all_completed_shows_hint(self) -> None:
        """Sync subtask-enabled read_todos shows hint when all completed."""
        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage, enable_subtasks=True)

        storage.todos = [
            Todo(id="1", content="Done", status="completed", active_form="Done"),
        ]
        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "Do NOT call read_todos again" in result

    async def test_async_all_completed_shows_hint(self) -> None:
        """Async read_todos shows hint when all completed."""
        storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(async_storage=storage)

        todo = Todo(id="1", content="Done", status="completed", active_form="Done")
        await storage.add_todo(todo)

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "Do NOT call read_todos again" in result

    async def test_async_subtasks_all_completed_shows_hint(self) -> None:
        """Async subtask-enabled read_todos shows hint when all completed."""
        storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)

        todo = Todo(id="1", content="Done", status="completed", active_form="Done")
        await storage.add_todo(todo)

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx())  # type: ignore[call-arg]
        assert "Do NOT call read_todos again" in result


class TestUpdateTodoStatuses:
    """Tests for the update_todo_statuses batch tool (sync storage)."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with the storage."""
        return create_todo_toolset(storage=storage)

    def test_toolset_has_update_todo_statuses_tool(self, toolset: FunctionToolset[Any]) -> None:
        """The batch tool is registered."""
        assert "update_todo_statuses" in toolset.tools

    async def test_batch_complete_and_start(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """One logical transition: complete the current task and start the next."""
        storage.todos = [
            Todo(id="todo-a", content="Task A", status="in_progress", active_form="Doing A"),
            Todo(id="todo-b", content="Task B", status="pending", active_form="Doing B"),
        ]
        updates = [
            TodoStatusUpdate(todo_id="todo-a", status="completed"),
            TodoStatusUpdate(todo_id="todo-b", status="in_progress"),
        ]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert storage.todos[0].status == "completed"
        assert storage.todos[1].status == "in_progress"
        assert "Updated 2 todos" in result
        assert "[todo-a] Task A → completed" in result
        assert "[todo-b] Task B → in_progress" in result

    async def test_empty_updates(self, toolset: FunctionToolset[Any]) -> None:
        """An empty batch is a no-op with a clear message."""
        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=[])  # type: ignore[call-arg]
        assert "No updates provided" in result

    async def test_unknown_id_applies_nothing(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """A single bad ID aborts the whole batch (all-or-nothing)."""
        storage.todos = [
            Todo(id="todo-a", content="Task A", status="pending", active_form="Doing A"),
        ]
        updates = [
            TodoStatusUpdate(todo_id="todo-a", status="completed"),
            TodoStatusUpdate(todo_id="missing", status="in_progress"),
        ]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert "No changes applied" in result
        assert "Todo with ID 'missing' not found" in result
        # The valid entry must NOT have been applied.
        assert storage.todos[0].status == "pending"

    async def test_invalid_status_applies_nothing(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """'blocked' is invalid without subtasks, so the batch is rejected."""
        storage.todos = [
            Todo(id="todo-a", content="Task A", status="pending", active_form="Doing A"),
        ]
        updates = [TodoStatusUpdate(todo_id="todo-a", status="blocked")]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert "No changes applied" in result
        assert "Invalid status 'blocked'" in result
        assert storage.todos[0].status == "pending"


class TestUpdateTodoStatusesWithSubtasks:
    """Tests for update_todo_statuses with subtasks enabled (sync)."""

    @pytest.fixture
    def storage(self) -> TodoStorage:
        """Create a storage instance."""
        return TodoStorage()

    @pytest.fixture
    def toolset(self, storage: TodoStorage) -> FunctionToolset[Any]:
        """Create a toolset with subtasks enabled."""
        return create_todo_toolset(storage=storage, enable_subtasks=True)

    async def test_blocked_status_allowed(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """'blocked' is a valid target status when subtasks are enabled."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="pending", active_form="Working"),
        ]
        updates = [TodoStatusUpdate(todo_id="task1", status="blocked")]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert storage.todos[0].status == "blocked"
        assert "task1] Task 1 → blocked" in result

    async def test_cannot_start_blocked_dependency(
        self, storage: TodoStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Starting a task with incomplete dependencies aborts the batch."""
        storage.todos = [
            Todo(id="task1", content="Task 1", status="pending", active_form="Working"),
            Todo(
                id="task2",
                content="Task 2",
                status="pending",
                active_form="Working",
                depends_on=["task1"],
            ),
        ]
        updates = [
            TodoStatusUpdate(todo_id="task1", status="in_progress"),
            TodoStatusUpdate(todo_id="task2", status="in_progress"),
        ]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert "No changes applied" in result
        assert "Cannot start 'Task 2'" in result
        # Nothing applied, including the otherwise-valid task1 transition.
        assert storage.todos[0].status == "pending"
        assert storage.todos[1].status == "pending"


class TestUpdateTodoStatusesAsync:
    """Tests for update_todo_statuses with async storage."""

    @pytest.fixture
    def storage(self) -> AsyncMemoryStorage:
        """Create an async storage instance."""
        return AsyncMemoryStorage()

    @pytest.fixture
    def toolset(self, storage: AsyncMemoryStorage) -> FunctionToolset[Any]:
        """Create a toolset with async storage."""
        return create_todo_toolset(async_storage=storage)

    def test_toolset_has_update_todo_statuses_tool(self, toolset: FunctionToolset[Any]) -> None:
        """The batch tool is registered on the async toolset."""
        assert "update_todo_statuses" in toolset.tools

    async def test_batch_complete_and_start(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Complete the current task and start the next in one async call."""
        await storage.add_todo(
            Todo(id="todo-a", content="Task A", status="in_progress", active_form="Doing A")
        )
        await storage.add_todo(
            Todo(id="todo-b", content="Task B", status="pending", active_form="Doing B")
        )
        updates = [
            TodoStatusUpdate(todo_id="todo-a", status="completed"),
            TodoStatusUpdate(todo_id="todo-b", status="in_progress"),
        ]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        todo_a = await storage.get_todo("todo-a")
        todo_b = await storage.get_todo("todo-b")
        assert todo_a is not None and todo_a.status == "completed"
        assert todo_b is not None and todo_b.status == "in_progress"
        assert "Updated 2 todos" in result

    async def test_empty_updates(self, toolset: FunctionToolset[Any]) -> None:
        """An empty async batch is a no-op."""
        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=[])  # type: ignore[call-arg]
        assert "No updates provided" in result

    async def test_unknown_id_applies_nothing(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """A bad ID aborts the whole async batch without partial writes."""
        await storage.add_todo(
            Todo(id="todo-a", content="Task A", status="pending", active_form="Doing A")
        )
        updates = [
            TodoStatusUpdate(todo_id="todo-a", status="completed"),
            TodoStatusUpdate(todo_id="missing", status="in_progress"),
        ]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert "No changes applied" in result
        assert "Todo with ID 'missing' not found" in result
        todo_a = await storage.get_todo("todo-a")
        assert todo_a is not None and todo_a.status == "pending"

    async def test_invalid_status_applies_nothing(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """'blocked' without subtasks rejects the async batch."""
        await storage.add_todo(
            Todo(id="todo-a", content="Task A", status="pending", active_form="Doing A")
        )
        updates = [TodoStatusUpdate(todo_id="todo-a", status="blocked")]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert "Invalid status 'blocked'" in result
        todo_a = await storage.get_todo("todo-a")
        assert todo_a is not None and todo_a.status == "pending"


class TestUpdateTodoStatusesAsyncSubtasks:
    """Tests for update_todo_statuses with async storage and subtasks enabled."""

    @pytest.fixture
    def storage(self) -> AsyncMemoryStorage:
        """Create an async storage instance."""
        return AsyncMemoryStorage()

    @pytest.fixture
    def toolset(self, storage: AsyncMemoryStorage) -> FunctionToolset[Any]:
        """Create an async toolset with subtasks enabled."""
        return create_todo_toolset(async_storage=storage, enable_subtasks=True)

    async def test_cannot_start_blocked_dependency(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """Async batch refuses to start a task with incomplete dependencies."""
        await storage.add_todo(
            Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        )
        await storage.add_todo(
            Todo(
                id="task2",
                content="Task 2",
                status="pending",
                active_form="Working",
                depends_on=["task1"],
            )
        )
        updates = [TodoStatusUpdate(todo_id="task2", status="in_progress")]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        assert "No changes applied" in result
        assert "Cannot start 'Task 2'" in result
        task2 = await storage.get_todo("task2")
        assert task2 is not None and task2.status == "pending"

    async def test_blocked_status_allowed(
        self, storage: AsyncMemoryStorage, toolset: FunctionToolset[Any]
    ) -> None:
        """'blocked' is a valid async target status when subtasks are enabled."""
        await storage.add_todo(
            Todo(id="task1", content="Task 1", status="pending", active_form="Working")
        )
        updates = [TodoStatusUpdate(todo_id="task1", status="blocked")]

        batch = toolset.tools["update_todo_statuses"]
        result = await batch.function(_ctx(), updates=updates)  # type: ignore[call-arg]

        task1 = await storage.get_todo("task1")
        assert task1 is not None and task1.status == "blocked"
        assert "task1] Task 1 → blocked" in result


class TestStorageResolver:
    """Per-run storage resolution via storage_resolver / async_storage_resolver."""

    async def test_sync_resolver_reads_and_writes_per_run_storage(self) -> None:
        """A sync resolver resolves storage from RunContext deps for each call."""
        run_storage = TodoStorage()
        # Closure storage is a distinct object that must NOT be used.
        closure_storage = TodoStorage()
        toolset = create_todo_toolset(
            storage=closure_storage,
            storage_resolver=lambda ctx: ctx.deps,
        )

        write_todos = toolset.tools["write_todos"]
        await write_todos.function(  # type: ignore[call-arg]
            _ctx(deps=run_storage),
            todos=[TodoItem(content="Resolved task", active_form="Working", status="pending")],
        )

        # Written through the resolved storage, not the closure default.
        assert len(run_storage.todos) == 1
        assert run_storage.todos[0].content == "Resolved task"
        assert closure_storage.todos == []

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(deps=run_storage))  # type: ignore[call-arg]
        assert "Resolved task" in result

    async def test_async_resolver_reads_and_writes_per_run_storage(self) -> None:
        """An async resolver resolves storage from RunContext deps for each call."""
        run_storage = AsyncMemoryStorage()
        closure_storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(
            async_storage=closure_storage,
            async_storage_resolver=lambda ctx: ctx.deps,
        )

        add_todo = toolset.tools["add_todo"]
        await add_todo.function(  # type: ignore[call-arg]
            _ctx(deps=run_storage), content="Resolved async task", active_form="Working"
        )

        assert len(await run_storage.get_todos()) == 1
        assert (await run_storage.get_todos())[0].content == "Resolved async task"
        assert await closure_storage.get_todos() == []

        read_todos = toolset.tools["read_todos"]
        result = await read_todos.function(_ctx(deps=run_storage))  # type: ignore[call-arg]
        assert "Resolved async task" in result
