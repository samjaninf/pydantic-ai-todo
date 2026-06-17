<h1 align="center">Todo Toolset for Pydantic AI</h1>

<p align="center">
  <em>Task Planning and Tracking for AI Agents</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/pydantic-ai-todo/"><img src="https://img.shields.io/pypi/v/pydantic-ai-todo.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/pydantic/pydantic-ai"><img src="https://img.shields.io/badge/Powered%20by-Pydantic%20AI-E92063?logo=pydantic&logoColor=white" alt="Pydantic AI"></a>
</p>

<p align="center">
  <b>Capabilities API</b> — plug-and-play with one line
  &nbsp;&bull;&nbsp;
  <b>Subtasks & Dependencies</b> — hierarchical task management
  &nbsp;&bull;&nbsp;
  <b>PostgreSQL Storage</b> — persistent multi-tenant tasks
  &nbsp;&bull;&nbsp;
  <b>Event System</b> — webhooks and callbacks
</p>

---

**Todo Toolset for Pydantic AI** adds task planning capabilities to any [Pydantic AI](https://ai.pydantic.dev/) agent. Your agent can create, track, and complete tasks with full support for subtasks, dependencies, and persistent storage.

> **Full framework?** Check out [Pydantic Deep Agents](https://github.com/vstorm-co/pydantic-deepagents) — complete agent framework with planning, filesystem, subagents, and skills.

## Quick Start

The recommended way to add todo support is via the **Capabilities API** — one import, one line:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability

agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
result = await agent.run("Create a todo list for building a REST API")
```

`TodoCapability` automatically:
- Registers all todo tools (`add_todo`, `read_todos`, `write_todos`, `update_todo_status`, `remove_todo`)
- Injects dynamic system prompt showing current task state
- Creates in-memory storage (or use your own)

### With Storage Access

```python
from pydantic_ai_todo import TodoCapability, TodoStorage

storage = TodoStorage()
agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(storage=storage)])

result = await agent.run("Plan a blog application")

# Access todos directly
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")
```

### With Subtasks and Dependencies

```python
agent = Agent(
    "openai:gpt-4.1",
    capabilities=[TodoCapability(enable_subtasks=True)],
)
```

Enables `add_subtask`, `set_dependency`, and `get_available_tasks` tools with automatic cycle detection.

### YAML Agent Definition

```yaml
model: openai:gpt-4.1
instructions: "You are a project planner."
capabilities:
  - TodoCapability:
      enable_subtasks: true
```

```python
agent = Agent.from_file("agent.yaml")
```

## Installation

```bash
pip install pydantic-ai-todo
```

Or with uv:

```bash
uv add pydantic-ai-todo
```

## Alternative: Toolset API

If you prefer the lower-level toolset approach (without capabilities):

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

> **Note:** With the toolset API, you need to wire `get_todo_system_prompt()` manually. `TodoCapability` handles this automatically.

## Available Tools

| Tool | Description |
|------|-------------|
| `read_todos` | List all tasks (supports hierarchical view) |
| `write_todos` | Bulk write/update tasks |
| `add_todo` | Add a single task |
| `update_todo_status` | Update task status by ID |
| `remove_todo` | Delete task by ID |
| `add_subtask`* | Create child task |
| `set_dependency`* | Link tasks with dependency |
| `get_available_tasks`* | List tasks ready to work on |

*Available when `enable_subtasks=True`

## Storage Backends

### In-Memory (Default)

```python
from pydantic_ai_todo import TodoCapability, TodoStorage

storage = TodoStorage()
agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(storage=storage)])
```

### Async Memory

```python
from pydantic_ai_todo import TodoCapability, AsyncMemoryStorage

storage = AsyncMemoryStorage()
agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(async_storage=storage)])
```

### PostgreSQL

> Requires the `postgres` extra: `pip install 'pydantic-ai-todo[postgres]'`

```python
from pydantic_ai_todo import TodoCapability, create_storage

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123",  # Multi-tenancy
)
await storage.initialize()

agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(async_storage=storage)])
```

## Event System

React to task changes:

```python
from pydantic_ai_todo import TodoCapability, TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()

@emitter.on_completed
async def notify_completed(event):
    print(f"Task done: {event.todo.content}")

@emitter.on_created
async def notify_created(event):
    print(f"New task: {event.todo.content}")

storage = AsyncMemoryStorage(event_emitter=emitter)
agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability(async_storage=storage)])
```

## API Reference

### Capability

| Class | Description |
|-------|-------------|
| `TodoCapability` | Pydantic AI capability — recommended way to add todo support |

### Factory Functions

| Function | Description |
|----------|-------------|
| `create_todo_toolset()` | Create standalone toolset (lower-level API) |
| `create_storage(backend, **options)` | Factory for storage backends |
| `get_todo_system_prompt()` | Generate system prompt with current todos |

### Models

| Model | Description |
|-------|-------------|
| `Todo` | Task with id, content, status, parent_id, depends_on |
| `TodoItem` | Input model for write_todos |
| `TodoEvent` | Event data with type, todo, timestamp |
| `TodoEventType` | CREATED, UPDATED, STATUS_CHANGED, DELETED, COMPLETED |

### Storage Classes

| Class | Description |
|-------|-------------|
| `TodoStorage` | Sync in-memory storage |
| `AsyncMemoryStorage` | Async in-memory with CRUD |
| `AsyncPostgresStorage` | PostgreSQL with multi-tenancy |
| `TodoEventEmitter` | Event emitter for callbacks |

## Related Projects

| Package | Description |
|---------|-------------|
| [Pydantic Deep Agents](https://github.com/vstorm-co/pydantic-deepagents) | Full agent framework (uses this library) |
| [pydantic-ai-backend](https://github.com/vstorm-co/pydantic-ai-backend) | File storage and Docker sandbox |
| [subagents-pydantic-ai](https://github.com/vstorm-co/subagents-pydantic-ai) | Multi-agent orchestration |
| [summarization-pydantic-ai](https://github.com/vstorm-co/summarization-pydantic-ai) | Context management |
| [pydantic-ai](https://github.com/pydantic/pydantic-ai) | The foundation — agent framework by Pydantic |

## Contributing

```bash
git clone https://github.com/vstorm-co/pydantic-ai-todo.git
cd pydantic-ai-todo
make install
make test  # 100% coverage required
```

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

### Need help implementing this in your company?

<p>We're <a href="https://vstorm.co"><b>Vstorm</b></a> — an Applied Agentic AI Engineering Consultancy<br>with 30+ production AI agent implementations.</p>

<a href="https://vstorm.co/contact-us/">
  <img src="https://img.shields.io/badge/Talk%20to%20us%20%E2%86%92-0066FF?style=for-the-badge&logoColor=white" alt="Talk to us">
</a>

<br><br>

Made with ❤️ by <a href="https://vstorm.co"><b>Vstorm</b></a>

</div>
