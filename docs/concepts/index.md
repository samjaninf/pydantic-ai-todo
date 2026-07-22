# Core Concepts

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     Your Agent                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │           TodoCapability (recommended)             │  │
│  │  tools + prompt section — auto-configured          │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Todo Toolset                          │  │
│  │  read_todos │ write_todos │ add_todo │ ...        │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Storage Backend                       │  │
│  │  TodoStorage │ AsyncMemoryStorage │ PostgreSQL    │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Event System (optional)               │  │
│  │  on_created │ on_completed │ on_updated │ ...     │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Key Components

### [TodoCapability](capability.md) (Recommended)

The capability bundles tools + a system prompt section into a single unit:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability

agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
```

- Registers all tools automatically
- Injects a static, cache-friendly system prompt section
  (opt into the live todo list with `include_current_todos=True`)
- Supports YAML agent definitions via AgentSpec

### [Toolset](toolset.md) (Lower-level)

The standalone toolset for when you need more control:

- [`create_todo_toolset()`][pydantic_ai_todo.create_todo_toolset] — Factory function
- Tools: `read_todos`, `write_todos`, `add_todo`, etc.
- Optional subtask tools with `enable_subtasks=True`
- Requires manual system prompt wiring via [`get_todo_system_prompt()`][pydantic_ai_todo.get_todo_system_prompt]

### [Storage](storage.md)

Multiple storage backends for different needs:

- [`TodoStorage`][pydantic_ai_todo.TodoStorage] — Simple sync in-memory
- [`AsyncMemoryStorage`][pydantic_ai_todo.AsyncMemoryStorage] — Async with CRUD operations
- [`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage] — Persistent with multi-tenancy
- [`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage] — Persistent, session-scoped Redis

### [Types](types.md)

Pydantic models for type safety:

- [`Todo`][pydantic_ai_todo.Todo] — The task model
- [`TodoItem`][pydantic_ai_todo.TodoItem] — Input model for LLM
- [`TodoEvent`][pydantic_ai_todo.TodoEvent] — Event data model

## How It Works

### With Capability (Recommended)

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability, TodoStorage

storage = TodoStorage()
agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(storage=storage)])

result = await agent.run("Plan the project")

for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")
```

### With Toolset

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, get_todo_system_prompt, TodoStorage

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

agent = Agent(
    "openai:gpt-4.1",
    toolsets=[toolset],
    system_prompt=get_todo_system_prompt(storage),
)

result = await agent.run("Plan the project")
```

## Next Steps

- [Capability](capability.md) — Recommended integration
- [Toolset](toolset.md) — Lower-level API
- [Storage](storage.md) — Choose the right backend
- [Types](types.md) — Understand the data models
