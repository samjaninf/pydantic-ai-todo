# TodoCapability

`TodoCapability` is the recommended way to add todo support to a Pydantic AI agent.
It's a [pydantic-ai capability](https://ai.pydantic.dev/capabilities/) that bundles
tools and instructions into a single plug-and-play unit.

## Why Capability over Toolset?

| Feature | TodoCapability | create_todo_toolset |
|---------|:-:|:-:|
| Tools registered automatically | Yes | Yes |
| Dynamic system prompt (shows current todos) | Yes | Manual wiring |
| AgentSpec YAML support | Yes | No |
| Single import | Yes | Need toolset + prompt function |

## Basic Usage

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability

agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
```

## Configuration

```python
TodoCapability(
    storage=TodoStorage(),              # Sync storage backend
    async_storage=AsyncMemoryStorage(), # Async storage backend
    enable_subtasks=True,               # Enable subtask tools
    descriptions={                      # Override tool descriptions
        "read_todos": "Check progress",
    },
)
```

Only one of `storage` or `async_storage` should be provided.
If neither is given, an in-memory `TodoStorage` is created automatically.

## How It Works

When you pass `TodoCapability` to an agent, pydantic-ai calls two methods
at construction time:

1. **`get_toolset()`** — returns the `FunctionToolset` containing all todo tools
   (`read_todos`, `write_todos`, `add_todo`, `update_todo_status`, `remove_todo`,
   and optionally `add_subtask`, `set_dependency`, `get_available_tasks`)

2. **`get_instructions()`** — returns the system prompt. The exact behavior
   depends on which storage you configured:

    - **With sync `storage`:** returns a callable invoked per-run that builds the
      prompt from the *current* todo list via
      [`get_todo_system_prompt`][pydantic_ai_todo.get_todo_system_prompt], so the
      model always sees the latest tasks.
    - **With only `async_storage` (no sync `storage`):** returns the **static**
      `TODO_SYSTEM_PROMPT` constant — the live todo
      list is **not** injected into the system prompt (the capability does not
      `await` async storage from the sync `get_instructions()` hook). The model
      still sees current todos by calling `read_todos`.

    !!! note "Dynamic injection needs sync storage"

        If you want the current task list embedded in the system prompt on every
        run, use sync `storage`. With async-only storage, rely on the `read_todos`
        tool (or build the prompt yourself with
        [`get_todo_system_prompt_async`][pydantic_ai_todo.get_todo_system_prompt_async]).

## Composing with Other Capabilities

`TodoCapability` composes naturally with other capabilities:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import TodoCapability
from pydantic_ai_summarization.capability import ContextManagerCapability

agent = Agent(
    "openai:gpt-4.1",
    capabilities=[
        TodoCapability(enable_subtasks=True),
        ContextManagerCapability(max_tokens=100_000),
    ],
)
```

## AgentSpec (YAML)

`TodoCapability` supports serialization via `Agent.from_file()`:

```yaml
model: openai:gpt-4.1
capabilities:
  - TodoCapability:
      enable_subtasks: true
```

The serialization name is `"TodoCapability"`. All constructor parameters
are serializable (primitives and dicts).
