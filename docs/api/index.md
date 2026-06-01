# API Reference

Complete API documentation for Todo Toolset for Pydantic AI.

## Modules

### Toolset

The main entry point for creating todo tools.

- [`create_todo_toolset()`](toolset.md#create_todo_toolset) — Create a todo toolset
- [`get_todo_system_prompt()`](toolset.md#get_todo_system_prompt) — Generate system prompt
- [`get_todo_system_prompt_async()`](toolset.md#get_todo_system_prompt_async) — Async system prompt

### Storage

Storage backends for task persistence.

- [`TodoStorage`](storage.md#todostorage) — Sync in-memory storage
- [`AsyncMemoryStorage`](storage.md#asyncmemorystorage) — Async in-memory storage
- [`AsyncPostgresStorage`](storage.md#asyncpostgresstorage) — PostgreSQL storage
- [`AsyncRedisStorage`](storage.md#asyncredisstorage) — Redis storage
- [`TodoStorageProtocol`](storage.md#todostorageprotocol) — Sync storage interface
- [`AsyncTodoStorageProtocol`](storage.md#asynctodostorageprotocol) — Async storage interface
- [`create_storage()`](storage.md#create_storage) — Storage factory function

### Types

Data structures used throughout the library.

- [`Todo`](types.md#todo) — Task model
- [`TodoItem`](types.md#todoitem) — Input model for LLM
- [`TodoEvent`](types.md#todoevent) — Event data model
- [`TodoEventType`](types.md#todoeventtype) — Event type enum
- [`TodoEventEmitter`](types.md#todoeventemitter) — Event emitter

## Quick Reference

### Creating a Toolset

```python
from pydantic_ai_todo import create_todo_toolset

# Basic (in-memory)
toolset = create_todo_toolset()

# With storage access
from pydantic_ai_todo import TodoStorage
storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# With async storage
from pydantic_ai_todo import AsyncMemoryStorage
storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

# With subtasks
toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)
```

### All Exports

```python
from pydantic_ai_todo import (
    # Toolset
    create_todo_toolset,
    get_todo_system_prompt,
    get_todo_system_prompt_async,
    
    # Storage
    TodoStorage,
    AsyncMemoryStorage,
    AsyncPostgresStorage,
    create_storage,
    
    # Types
    Todo,
    TodoItem,
    TodoEvent,
    TodoEventType,
    TodoEventEmitter,
    
    # Protocols
    TodoStorageProtocol,
    AsyncTodoStorageProtocol,
)
```
