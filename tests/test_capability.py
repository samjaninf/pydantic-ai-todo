"""Tests for TodoCapability."""

from __future__ import annotations

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from pydantic_ai_todo import Todo, TodoCapability, TodoStorage
from pydantic_ai_todo.storage import AsyncMemoryStorage
from pydantic_ai_todo.toolset import TODO_SYSTEM_PROMPT


class TestTodoCapability:
    """Tests for TodoCapability construction and configuration."""

    def test_default_creates_storage(self):
        """Default capability creates in-memory TodoStorage."""
        cap = TodoCapability()
        assert cap.storage is not None
        assert isinstance(cap.storage, TodoStorage)
        assert cap.async_storage is None

    def test_custom_sync_storage(self):
        """Custom sync storage is used."""
        storage = TodoStorage()
        cap = TodoCapability(storage=storage)
        assert cap.storage is storage

    def test_serialization_name(self):
        """Serialization name for AgentSpec."""
        assert TodoCapability.get_serialization_name() == "TodoCapability"

    def test_async_storage(self):
        """Async storage is accepted."""
        async_storage = AsyncMemoryStorage()
        cap = TodoCapability(async_storage=async_storage)
        assert cap.async_storage is async_storage
        assert cap.storage is None

    def test_enable_subtasks(self):
        """enable_subtasks flag is forwarded to toolset."""
        cap = TodoCapability(enable_subtasks=True)
        assert cap.enable_subtasks is True
        assert cap.get_toolset() is not None

    def test_custom_descriptions(self):
        """Custom descriptions are forwarded."""
        cap = TodoCapability(descriptions={"read_todos": "Custom desc"})
        assert cap.descriptions == {"read_todos": "Custom desc"}

    def test_get_toolset_returns_toolset(self):
        """get_toolset returns the FunctionToolset."""
        cap = TodoCapability()
        toolset = cap.get_toolset()
        assert toolset is not None

    def test_get_instructions_static_by_default(self):
        """Default instructions are the static prompt, even with sync storage."""
        storage = TodoStorage()
        cap = TodoCapability(storage=storage)
        instructions = cap.get_instructions()
        assert instructions == TODO_SYSTEM_PROMPT

    def test_static_instructions_stable_across_mutations(self):
        """The static prompt does not change when todos are mutated (cache-safe)."""
        storage = TodoStorage()
        cap = TodoCapability(storage=storage)
        before = cap.get_instructions()
        storage.todos = [
            Todo(
                id="1",
                content="Write tests",
                status="in_progress",
                active_form="Writing tests",
            )
        ]
        assert cap.get_instructions() == before
        assert "Write tests" not in before

    def test_get_instructions_dynamic_with_opt_in(self):
        """include_current_todos=True returns a per-request callable."""
        storage = TodoStorage()
        cap = TodoCapability(storage=storage, include_current_todos=True)
        instructions = cap.get_instructions()
        assert callable(instructions)

    def test_get_instructions_without_sync_storage(self):
        """get_instructions returns static string without sync storage."""
        cap = TodoCapability(async_storage=AsyncMemoryStorage(), include_current_todos=True)
        instructions = cap.get_instructions()
        assert instructions == TODO_SYSTEM_PROMPT

    def test_instructions_reflect_current_todos(self):
        """Opted-in dynamic instructions show current todo state."""

        storage = TodoStorage()
        cap = TodoCapability(storage=storage, include_current_todos=True)
        instructions_fn = cap.get_instructions()

        ctx = type("FakeCtx", (), {"deps": None})()

        # Empty todos — should return base prompt
        result = instructions_fn(ctx)
        assert "## Task Management" in result

        # Add a todo — should appear in prompt
        storage.todos = [
            Todo(
                id="1",
                content="Write tests",
                status="in_progress",
                active_form="Writing tests",
            )
        ]
        result = instructions_fn(ctx)
        assert "Write tests" in result
        assert "[*]" in result  # in_progress icon


class TestTodoCapabilityIntegration:
    """Integration tests with real Agent."""

    @pytest.mark.anyio
    async def test_agent_with_capability(self):
        """Agent with TodoCapability can run successfully."""
        cap = TodoCapability()
        agent = Agent(TestModel(), capabilities=[cap])
        result = await agent.run("Create a todo list")
        assert result.output is not None

    @pytest.mark.anyio
    async def test_agent_has_todo_tools(self):
        """Agent with TodoCapability registers todo tools."""
        cap = TodoCapability()
        agent = Agent(TestModel(), capabilities=[cap])

        # The toolset has the expected tools
        toolset = cap.get_toolset()
        assert toolset is not None
        tool_names = set(toolset.tools.keys())  # type: ignore[union-attr]
        assert "read_todos" in tool_names
        assert "write_todos" in tool_names
        assert "add_todo" in tool_names
        assert "update_todo_status" in tool_names
        assert "remove_todo" in tool_names

        # Agent runs without error
        result = await agent.run("List my tasks")
        assert result.output is not None

    @pytest.mark.anyio
    async def test_agent_with_subtasks(self):
        """Agent with subtasks enabled has extra tools."""
        cap = TodoCapability(enable_subtasks=True)
        agent = Agent(TestModel(), capabilities=[cap])

        toolset = cap.get_toolset()
        assert toolset is not None
        tool_names = set(toolset.tools.keys())  # type: ignore[union-attr]
        assert "add_subtask" in tool_names
        assert "set_dependency" in tool_names

        result = await agent.run("Create subtasks")
        assert result.output is not None
