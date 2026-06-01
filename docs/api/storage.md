# Storage API

## TodoStorage

::: pydantic_ai_todo.TodoStorage
    options:
      show_root_heading: true
      show_source: true

---

## AsyncMemoryStorage

::: pydantic_ai_todo.AsyncMemoryStorage
    options:
      show_root_heading: true
      show_source: true

---

## AsyncPostgresStorage

::: pydantic_ai_todo.AsyncPostgresStorage
    options:
      show_root_heading: true
      show_source: true

---

## AsyncRedisStorage

::: pydantic_ai_todo.AsyncRedisStorage
    options:
      show_root_heading: true
      show_source: true

---

## TodoStorageProtocol

::: pydantic_ai_todo.TodoStorageProtocol
    options:
      show_root_heading: true
      show_source: true

---

## AsyncTodoStorageProtocol

::: pydantic_ai_todo.AsyncTodoStorageProtocol
    options:
      show_root_heading: true
      show_source: true

---

## create_storage

::: pydantic_ai_todo.create_storage
    options:
      show_root_heading: true
      show_source: true

---

## Usage Examples

### Sync Storage

```python
from pydantic_ai_todo import TodoStorage, create_todo_toolset

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# Direct access
todos = storage.todos
storage.todos = []  # Clear
```

### Async Memory Storage

```python
from pydantic_ai_todo import AsyncMemoryStorage, Todo

storage = AsyncMemoryStorage()

# CRUD operations
todo = await storage.add_todo(
    Todo(content="Task", status="pending", active_form="Working")
)
todos = await storage.get_todos()
todo = await storage.get_todo("abc12345")
await storage.update_todo("abc12345", status="completed")
await storage.remove_todo("abc12345")
```

### PostgreSQL Storage

```python
from pydantic_ai_todo import create_storage

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123",
)
await storage.initialize()

# Use with toolset
toolset = create_todo_toolset(async_storage=storage)

# Clean up
await storage.close()
```

### With Events

```python
from pydantic_ai_todo import AsyncMemoryStorage, TodoEventEmitter

emitter = TodoEventEmitter()

@emitter.on_completed
async def on_complete(event):
    print(f"Done: {event.todo.content}")

storage = AsyncMemoryStorage(event_emitter=emitter)
```
