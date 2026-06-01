"""Todo capability for pydantic-ai agents.

Provides a `TodoCapability` that integrates todo toolset + dynamic instructions
via the pydantic-ai capabilities API.

Example:
    ```python
    from pydantic_ai import Agent
    from pydantic_ai_todo import TodoCapability

    agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AbstractToolset

from pydantic_ai_todo.storage import (
    AsyncTodoStorageProtocol,
    TodoStorage,
    TodoStorageProtocol,
)
from pydantic_ai_todo.toolset import (
    TODO_SYSTEM_PROMPT,
    create_todo_toolset,
    get_todo_system_prompt,
)


@dataclass
class TodoCapability(AbstractCapability[Any]):
    """Capability that provides todo/task planning tools and dynamic instructions.

    Combines the todo toolset (read_todos, write_todos, add_todo, etc.) with
    dynamic system prompt injection that shows the current task list.

    This is the recommended way to add todo support to a pydantic-ai agent
    when using the capabilities API.

    Example:
        ```python
        from pydantic_ai import Agent
        from pydantic_ai_todo import TodoCapability, TodoStorage

        # Simple usage
        agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])

        # With storage access
        storage = TodoStorage()
        agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(storage=storage)])
        result = await agent.run("Create 3 tasks for building a REST API")
        print(storage.todos)

        # With subtasks enabled
        agent = Agent(
            "openai:gpt-4.1",
            capabilities=[TodoCapability(enable_subtasks=True)],
        )
        ```

    Attributes:
        storage: Sync storage backend for todos.
        async_storage: Async storage backend for todos.
        enable_subtasks: Enable subtask and dependency features.
        descriptions: Custom tool descriptions override.
    """

    storage: TodoStorageProtocol | None = None
    async_storage: AsyncTodoStorageProtocol | None = None
    enable_subtasks: bool = False
    descriptions: dict[str, str] | None = None
    _toolset: AbstractToolset[Any] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Create the underlying toolset and set default storage."""
        if self.storage is None and self.async_storage is None:
            self.storage = TodoStorage()

        self._toolset = create_todo_toolset(
            storage=self.storage,
            async_storage=self.async_storage,
            id="todo",
            enable_subtasks=self.enable_subtasks,
            descriptions=self.descriptions,
        )

    @classmethod
    def get_serialization_name(cls) -> str:
        """Return name for AgentSpec YAML/JSON serialization."""
        return "TodoCapability"

    def get_toolset(self) -> AbstractToolset[Any] | None:
        """Return the todo toolset with all registered tools."""
        return self._toolset

    def get_instructions(self) -> Any:
        """Return a dynamic instruction function that includes current todos.

        The function is called per-run, so the system prompt always reflects
        the latest todo state.
        """
        storage = self.storage

        if storage is not None:

            def _sync_instructions(ctx: RunContext[Any]) -> str:
                return get_todo_system_prompt(storage)

            return _sync_instructions

        # No sync storage — return static prompt
        return TODO_SYSTEM_PROMPT
