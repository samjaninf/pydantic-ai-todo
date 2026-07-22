# TodoCapability

`TodoCapability` is the recommended way to add todo support to a Pydantic AI agent.
It's a [pydantic-ai capability](https://ai.pydantic.dev/capabilities/) that bundles
tools and instructions into a single plug-and-play unit.

## Why Capability over Toolset?

| Feature | TodoCapability | create_todo_toolset |
|---------|:-:|:-:|
| Tools registered automatically | Yes | Yes |
| System prompt section | Yes | Manual wiring |
| Live todo list in prompt (opt-in) | `include_current_todos=True` | Manual wiring |
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
    include_current_todos=True,         # Inject live todo list into the prompt
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

2. **`get_instructions()`** — returns the system prompt. By default this is the
   **static** `TODO_SYSTEM_PROMPT` constant, which describes the tools and the
   workflow but does not embed the todo list itself. The model sees the current
   state through the mutating tools' return values and `read_todos`.

    With `include_current_todos=True` and sync `storage`, it instead returns a
    callable invoked per model request that appends the *current* todo list via
    [`get_todo_system_prompt`][pydantic_ai_todo.get_todo_system_prompt].

    !!! warning "Prompt caching"

        The system prompt is the very start of the provider's prompt-cache
        prefix. With `include_current_todos=True`, every status change rewrites
        it — invalidating the entire cached prefix, including mid-run after each
        mutating tool call. On cached workloads this can raise input-token cost
        several-fold ([#41](https://github.com/vstorm-co/pydantic-ai-todo/issues/41)).
        The live list is largely redundant anyway: every mutating tool already
        returns the updated state into the append-only (cache-friendly) message
        history. Prefer the default unless you have a specific reason.

    !!! note "Dynamic injection needs sync storage"

        `include_current_todos=True` requires sync `storage` — the capability
        cannot `await` async storage from the sync `get_instructions()` hook.
        With async-only storage the prompt stays static; rely on the
        `read_todos` tool (or build the prompt yourself with
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
