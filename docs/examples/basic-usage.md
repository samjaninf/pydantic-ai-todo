# Basic Usage

## Using TodoCapability (Recommended)

The simplest way to add todo support to your agent:

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability

async def main():
    agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
    result = await agent.run(
        "Create a todo list for building a REST API with user authentication"
    )
    print(result.output)

asyncio.run(main())
```

## Accessing Tasks After Run

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability, TodoStorage

async def main():
    storage = TodoStorage()
    agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(storage=storage)])

    result = await agent.run("Plan the implementation of a blog application")

    print("Agent's response:")
    print(result.output)
    print()

    # Access tasks directly from storage
    print("Tasks created:")
    for todo in storage.todos:
        status_icon = "✓" if todo.status == "completed" else "○"
        print(f"  {status_icon} [{todo.id}] {todo.content}")

asyncio.run(main())
```

## With Subtasks

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability

async def main():
    agent = Agent(
        "openai:gpt-4.1",
        capabilities=[TodoCapability(enable_subtasks=True)],
    )

    result = await agent.run(
        "Break down 'Build authentication system' into subtasks"
    )
    print(result.output)

asyncio.run(main())
```

## Task Progress Tracking

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability, TodoStorage

async def main():
    storage = TodoStorage()
    agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(storage=storage)])

    # First run: create tasks
    result1 = await agent.run("Create 3 simple coding tasks")
    print("Created tasks:")
    for todo in storage.todos:
        print(f"  [{todo.status}] {todo.content}")

    # Second run: complete tasks
    result2 = await agent.run(
        "Complete all the tasks you created",
        message_history=result1.all_messages(),
    )
    print("\nAfter completion:")
    for todo in storage.todos:
        print(f"  [{todo.status}] {todo.content}")

asyncio.run(main())
```

## YAML Agent Definition

Define your agent in YAML and load it:

```yaml
# agent.yaml
model: openai:gpt-4.1
instructions: "You are a project planner. Break down tasks and track progress."
capabilities:
  - TodoCapability:
      enable_subtasks: true
```

```python
from pydantic_ai import Agent

agent = Agent.from_file("agent.yaml")
result = await agent.run("Plan a mobile app project")
```

## Using the Toolset API (Alternative)

If you need lower-level control:

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
```

!!! note
    With `TodoCapability`, the system prompt section is injected automatically
    (static by default; pass `include_current_todos=True` to embed the live
    todo state). With the toolset API, you need to wire this manually.

## Next Steps

- [Async Storage](async-storage.md) — Use async storage backends
- [PostgreSQL](postgres.md) — Persistent storage
- [Subtasks](subtasks.md) — Hierarchical tasks
