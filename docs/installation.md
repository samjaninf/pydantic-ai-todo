# Installation

## Requirements

- Python 3.10 or higher
- [pydantic-ai](https://ai.pydantic.dev/) installed

## Install from PyPI

=== "pip"

    ```bash
    pip install pydantic-ai-todo
    ```

=== "uv"

    ```bash
    uv add pydantic-ai-todo
    ```

=== "poetry"

    ```bash
    poetry add pydantic-ai-todo
    ```

## PostgreSQL and Redis Support

PostgreSQL and Redis storage ship by default. The package depends on
[`asyncpg`](https://magicstack.github.io/asyncpg/) and
[`redis`](https://redis.readthedocs.io/) as core dependencies, so
[`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage] and
[`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage] are available without
any extra installs. You only need a running PostgreSQL or Redis server to use
them.

## Verify Installation

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

# Create agent with todo capabilities
agent = Agent(
    "openai:gpt-4o",
    toolsets=[create_todo_toolset()],
)

# Test it works
result = await agent.run("Add a task: Test installation")
print(result.output)
```

## API Key Setup

You'll need an API key for your LLM provider. For OpenAI:

=== "Environment Variable"

    ```bash
    export OPENAI_API_KEY="your-api-key"
    ```

=== ".env File"

    ```bash
    # .env
    OPENAI_API_KEY=your-api-key
    ```

    ```python
    from dotenv import load_dotenv
    load_dotenv()
    ```

## What's Included

The package provides:

- [`create_todo_toolset()`][pydantic_ai_todo.create_todo_toolset] — Factory function to create the toolset
- [`TodoCapability`][pydantic_ai_todo.TodoCapability] — Capability bundling the toolset with dynamic instructions (recommended)
- [`get_todo_system_prompt()`][pydantic_ai_todo.get_todo_system_prompt] / [`get_todo_system_prompt_async()`][pydantic_ai_todo.get_todo_system_prompt_async] — Build the system prompt with the current todo list
- [`TodoStorage`][pydantic_ai_todo.TodoStorage] — Sync in-memory storage
- [`AsyncMemoryStorage`][pydantic_ai_todo.AsyncMemoryStorage] — Async in-memory storage
- [`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage] — PostgreSQL storage
- [`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage] — Redis storage
- [`create_storage()`][pydantic_ai_todo.create_storage] — Factory for async storage backends
- [`TodoStorageProtocol`][pydantic_ai_todo.TodoStorageProtocol] / [`AsyncTodoStorageProtocol`][pydantic_ai_todo.AsyncTodoStorageProtocol] — Storage interfaces for custom backends
- [`TodoEventEmitter`][pydantic_ai_todo.TodoEventEmitter] — Event system for callbacks
- [`Todo`][pydantic_ai_todo.Todo], [`TodoItem`][pydantic_ai_todo.TodoItem] — Pydantic models

## Next Steps

- [Quick Start](examples/basic-usage.md) — Build your first todo-enabled agent
- [Core Concepts](concepts/index.md) — Understand the architecture
- [Storage Backends](concepts/storage.md) — Choose the right storage
