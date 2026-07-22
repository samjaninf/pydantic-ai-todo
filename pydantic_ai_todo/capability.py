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
    """Capability that provides todo/task planning tools and instructions.

    Combines the todo toolset (read_todos, write_todos, add_todo, etc.) with
    a system prompt section describing the workflow. By default the prompt is
    static so todo mutations never invalidate the provider's prompt cache;
    set `include_current_todos=True` to also inject the live task list.

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
        include_current_todos: Inject the live todo list into the system prompt.
            Off by default: the system prompt is the start of the provider's
            prompt-cache prefix, so rewriting it on every status change
            invalidates the whole cached prefix — including mid-run, after
            every mutating tool call. The mutating tools already return the
            updated state into the (append-only, cache-friendly) message
            history, and `read_todos` is available for explicit checks.
            Enable only if you need the todo list in the system prompt and
            accept the cache cost.
    """

    storage: TodoStorageProtocol | None = None
    async_storage: AsyncTodoStorageProtocol | None = None
    enable_subtasks: bool = False
    descriptions: dict[str, str] | None = None
    include_current_todos: bool = False
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
        """Return the todo instructions for the system prompt.

        By default this is the static `TODO_SYSTEM_PROMPT`, which keeps the
        system prompt stable across todo mutations and preserves the
        provider's prompt cache. With `include_current_todos=True` (and sync
        storage) it returns a per-request function that appends the live todo
        list to the prompt.
        """
        storage = self.storage

        if self.include_current_todos and storage is not None:

            def _sync_instructions(ctx: RunContext[Any]) -> str:
                return get_todo_system_prompt(storage)

            return _sync_instructions

        # Static prompt: cache-friendly default, and the only option
        # when no sync storage is configured.
        return TODO_SYSTEM_PROMPT
