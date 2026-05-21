"""Todo toolset for pydantic-ai agents.

Provides task planning and tracking capabilities for AI agents.
Compatible with any pydantic-ai agent - no specific deps required.

Example:
    ```python
    from pydantic_ai import Agent
    from pydantic_ai_todo import create_todo_toolset, TodoStorage

    # Simple usage
    agent = Agent("openai:gpt-4.1", toolsets=[create_todo_toolset()])

    # With storage access
    storage = TodoStorage()
    agent = Agent("openai:gpt-4.1", toolsets=[create_todo_toolset(storage)])
    result = await agent.run("Create 3 tasks")
    print(storage.todos)  # Access todos directly
    ```
"""

from importlib.metadata import version

from pydantic_ai_todo.capability import TodoCapability
from pydantic_ai_todo.events import TodoEvent, TodoEventEmitter, TodoEventType
from pydantic_ai_todo.storage import (
    AsyncMemoryStorage,
    AsyncPostgresStorage,
    AsyncRedisStorage,
    AsyncTodoStorageProtocol,
    TodoStorage,
    TodoStorageProtocol,
    create_storage,
)
from pydantic_ai_todo.toolset import (
    ADD_SUBTASK_DESCRIPTION,
    ADD_TODO_DESCRIPTION,
    GET_AVAILABLE_TASKS_DESCRIPTION,
    READ_TODO_DESCRIPTION,
    REMOVE_TODO_DESCRIPTION,
    SET_DEPENDENCY_DESCRIPTION,
    TODO_SYSTEM_PROMPT,
    TODO_TOOL_DESCRIPTION,
    UPDATE_TODO_STATUS_DESCRIPTION,
    create_todo_toolset,
    get_todo_system_prompt,
    get_todo_system_prompt_async,
)
from pydantic_ai_todo.types import Todo, TodoItem

__all__ = [
    # Capability (recommended)
    "TodoCapability",
    # Main factory
    "create_todo_toolset",
    "get_todo_system_prompt",
    "get_todo_system_prompt_async",
    # Types
    "Todo",
    "TodoItem",
    # Sync storage
    "TodoStorage",
    "TodoStorageProtocol",
    # Async storage
    "AsyncMemoryStorage",
    "AsyncPostgresStorage",
    "AsyncRedisStorage",
    "AsyncTodoStorageProtocol",
    "create_storage",
    # Events
    "TodoEvent",
    "TodoEventType",
    "TodoEventEmitter",
    # Constants (for customization)
    "TODO_TOOL_DESCRIPTION",
    "TODO_SYSTEM_PROMPT",
    "READ_TODO_DESCRIPTION",
    "ADD_TODO_DESCRIPTION",
    "UPDATE_TODO_STATUS_DESCRIPTION",
    "REMOVE_TODO_DESCRIPTION",
    "ADD_SUBTASK_DESCRIPTION",
    "SET_DEPENDENCY_DESCRIPTION",
    "GET_AVAILABLE_TASKS_DESCRIPTION",
]

__version__ = version("pydantic-ai-todo")
