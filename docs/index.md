<h1 align="center">Todo Toolset for Pydantic AI</h1>
<p align="center">
  <em>Task Planning and Tracking for AI Agents</em>
</p>
<p align="center">
  <a href="https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/pydantic-ai-todo/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://coveralls.io/github/vstorm-co/pydantic-ai-todo?branch=main"><img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage"></a>
  <a href="https://pypi.org/project/pydantic-ai-todo/"><img src="https://img.shields.io/pypi/v/pydantic-ai-todo.svg" alt="PyPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue" alt="Python"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

**Todo Toolset for Pydantic AI** adds task planning capabilities to any [Pydantic AI](https://ai.pydantic.dev/) agent. Your agent can create, track, and complete tasks with full support for subtasks, dependencies, and persistent storage.

Think of it as giving your AI agent a todo list — so it can break down complex work, track progress, and remember what needs to be done.

## Why use Todo Toolset?

1. **Task Decomposition**: Agents break complex problems into manageable tasks. A "build REST API" request becomes a tracked list of specific steps.

2. **Progress Tracking**: See what your agent is working on, what's done, and what's blocked.

3. **Hierarchical Tasks**: Subtasks and dependencies with automatic cycle detection. Perfect for complex workflows.

4. **Persistent Storage**: PostgreSQL backend with session-based multi-tenancy. Production-ready.

## Quick Start (Capability API)

The recommended way to add todo support — one import, one line:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability

agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
result = await agent.run("Create a todo list for building a REST API")
```

`TodoCapability` automatically registers all tools and injects a system prompt
section describing the todo workflow. No manual wiring needed. The prompt is
static by default so todo updates never break the provider's prompt cache —
pass `include_current_todos=True` to embed the live task list instead.

### Alternative: Toolset API

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset

agent = Agent("openai:gpt-4.1", toolsets=[create_todo_toolset()])
result = await agent.run("Create a todo list for building a REST API")
```

!!! note
    With the toolset API you need to wire `get_todo_system_prompt()` into the
    agent's instructions manually. `TodoCapability` handles this automatically.

## Core Features

| Feature | Description |
|---------|-------------|
| **Task Management** | Create, update, complete, and delete tasks |
| **Subtasks** | Hierarchical task structure with parent-child relationships |
| **Dependencies** | Link tasks with automatic cycle detection |
| **Multiple Backends** | In-memory, async, and PostgreSQL storage |
| **Event System** | React to task changes with callbacks and webhooks |
| **Multi-Tenancy** | Session-based isolation in PostgreSQL |

## Available Tools

When you add the todo toolset, your agent gets these tools:

| Tool | Description |
|------|-------------|
| `read_todos` | List all tasks (hierarchical view available) |
| `write_todos` | Bulk write/update tasks |
| `add_todo` | Add a single task |
| `update_todo_status` | Update task status by ID |
| `remove_todo` | Delete task by ID |
| `add_subtask`* | Create child task |
| `set_dependency`* | Link tasks with dependency |
| `get_available_tasks`* | List tasks ready to work on |

*Available when `enable_subtasks=True`

## Part of the Pydantic AI Ecosystem

Todo Toolset is part of a modular ecosystem:

| Package | Description |
|---------|-------------|
| [Pydantic Deep Agents](https://github.com/vstorm-co/pydantic-deepagents) | Full agent framework (uses this library) |
| [pydantic-ai-backend](https://github.com/vstorm-co/pydantic-ai-backend) | File storage and Docker sandbox |
| [subagents-pydantic-ai](https://github.com/vstorm-co/subagents-pydantic-ai) | Multi-agent orchestration |
| [summarization-pydantic-ai](https://github.com/vstorm-co/summarization-pydantic-ai) | Context management |

## Installation

```bash
pip install pydantic-ai-todo
```

## Next Steps

- [Installation](installation.md) - Get started in minutes
- [Core Concepts](concepts/index.md) - Learn about toolset, storage, and types
- [Examples](examples/index.md) - See the toolset in action
- [API Reference](api/index.md) - Complete API documentation

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/vstorm-co">vstorm-co</a></sub>
</p>
