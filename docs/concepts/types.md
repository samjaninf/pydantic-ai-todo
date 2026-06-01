# Types

Pydantic models used throughout the library.

## Todo

The main task model.

```python
from pydantic_ai_todo import Todo

todo = Todo(
    id="abc12345",  # Auto-generated if not provided
    content="Implement user authentication",
    status="pending",  # "pending" | "in_progress" | "completed" | "blocked"
    active_form="Implementing user authentication",
    parent_id=None,  # For subtasks
    depends_on=[],  # Task IDs this depends on
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | 8-character hex ID (auto-generated) |
| `content` | `str` | Task description |
| `status` | `str` | `"pending"`, `"in_progress"`, `"completed"`, or `"blocked"` |
| `active_form` | `str` | Present tense description (for display) |
| `parent_id` | `str \| None` | Parent task ID (for subtasks) |
| `depends_on` | `list[str]` | IDs of blocking tasks |

### Status Values

- **pending** — Not started
- **in_progress** — Currently being worked on
- **completed** — Finished
- **blocked** — Cannot proceed (dependencies not met, used with subtasks)

## TodoItem

Input model for the `write_todos` tool. Optimized for LLM output.

```python
from pydantic_ai_todo import TodoItem

item = TodoItem(
    content="Set up database",
    status="pending",
    active_form="Setting up database",
)
```

### Why TodoItem?

`TodoItem` has `Field` descriptions that help the LLM understand what to provide.
It carries the same fields as [`Todo`][pydantic_ai_todo.Todo] — including the
optional `id`, `parent_id`, and `depends_on` for subtask hierarchies, and the
full `status` literal (`pending`, `in_progress`, `completed`, `blocked`). See the
full field reference: [`TodoItem`][pydantic_ai_todo.TodoItem].

## TodoEvent

Event data emitted when tasks change.

```python
from pydantic_ai_todo import TodoEvent, TodoEventType

# Event structure
event = TodoEvent(
    event_type=TodoEventType.COMPLETED,
    todo=todo,
    timestamp=datetime.now(timezone.utc),
    previous_state=old_todo,  # Previous Todo object or None
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `TodoEventType` | Type of change |
| `todo` | `Todo` | The affected task |
| `timestamp` | `datetime` | When the event occurred |
| `previous_state` | `Todo \| None` | Previous todo state (for changes) |

## TodoEventType

Enum of event types.

```python
from pydantic_ai_todo import TodoEventType

TodoEventType.CREATED        # Task was created
TodoEventType.UPDATED        # Task was modified
TodoEventType.STATUS_CHANGED # Status specifically changed
TodoEventType.DELETED        # Task was removed
TodoEventType.COMPLETED      # Task was marked completed
```

## Type Aliases

```python
from pydantic_ai_todo import (
    TodoStorageProtocol,      # Sync storage protocol
    AsyncTodoStorageProtocol, # Async storage protocol
)
```

## Example: Working with Types

```python
from pydantic_ai_todo import (
    Todo,
    TodoItem,
    TodoEvent,
    TodoEventType,
    TodoStorage,
)

# Create storage with initial todos
storage = TodoStorage()
storage.todos = [
    Todo(content="Task 1", status="pending", active_form="Working on task 1"),
    Todo(content="Task 2", status="completed", active_form="Working on task 2"),
]

# Filter by status
pending = [t for t in storage.todos if t.status == "pending"]
completed = [t for t in storage.todos if t.status == "completed"]

# Convert to dict
todo_dict = storage.todos[0].model_dump()

# Create from dict
todo = Todo(**todo_dict)
```
