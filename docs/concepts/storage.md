# Storage Backends

pydantic-ai-todo supports multiple storage backends for different use cases.

## Overview

| Backend | Class | Persistence | Multi-Tenancy | Use Case |
|---------|-------|-------------|---------------|----------|
| Sync Memory | [`TodoStorage`][pydantic_ai_todo.TodoStorage] | No | No | Testing, simple agents |
| Async Memory | [`AsyncMemoryStorage`][pydantic_ai_todo.AsyncMemoryStorage] | No | No | Async agents |
| PostgreSQL | [`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage] | Yes | Yes | Production apps |
| Redis | [`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage] | Yes | Yes | Production apps, fast session-scoped storage |

## Sync In-Memory Storage

The simplest option. Data is lost when the process ends.

```python
from pydantic_ai_todo import TodoStorage, create_todo_toolset

storage = TodoStorage()
toolset = create_todo_toolset(storage=storage)

# After agent runs
for todo in storage.todos:
    print(f"[{todo.status}] {todo.content}")

# Direct manipulation
storage.todos = []  # Clear all
```

### When to Use

- Testing
- Single-session agents
- Prototyping

## Async In-Memory Storage

For async operations with full CRUD support.

```python
from pydantic_ai_todo import AsyncMemoryStorage, create_todo_toolset

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

# CRUD operations
todos = await storage.get_todos()
todo = await storage.get_todo("abc12345")
await storage.add_todo(Todo(content="Task", status="pending", active_form="Working"))
await storage.update_todo("abc12345", status="completed")
await storage.remove_todo("abc12345")
await storage.set_todos([])  # Replace all
```

### When to Use

- Async agents
- When you need CRUD operations
- Testing async code

## PostgreSQL Storage

Persistent storage with multi-tenancy support.

```python
from pydantic_ai_todo import create_storage, create_todo_toolset

storage = create_storage(
    "postgres",
    connection_string="postgresql://user:pass@localhost/db",
    session_id="user-123",
)
await storage.initialize()  # Creates table

toolset = create_todo_toolset(async_storage=storage)

# When done
await storage.close()
```

### Session-Based Multi-Tenancy

Each `session_id` isolates todos:

```python
# User A's todos
storage_a = create_storage("postgres", ..., session_id="user-a")

# User B's todos (completely separate)
storage_b = create_storage("postgres", ..., session_id="user-b")
```

### Database Schema

Auto-created table:

```sql
CREATE TABLE IF NOT EXISTS todos (
    id VARCHAR(8) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    active_form TEXT NOT NULL,
    parent_id VARCHAR(8),
    depends_on TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_todos_session_id ON todos(session_id);
```

### When to Use

- Production applications
- Multi-user apps
- Persistent task storage

## Redis Storage

Persistent, session-scoped storage backed by Redis. Todos are stored in a Redis
Hash (one field per todo, JSON-serialized) with a companion List that preserves
insertion order. The `session_id` is hash-tagged so both keys co-locate on the
same Redis Cluster slot.

```python
from pydantic_ai_todo import create_storage, create_todo_toolset

storage = create_storage(
    "redis",
    url="redis://localhost:6379",
    session_id="user-123",
)
await storage.initialize()  # Verifies connectivity

toolset = create_todo_toolset(async_storage=storage)

# When done
await storage.close()
```

You can also pass an existing `redis.asyncio.Redis` client via `client=` instead
of `url=`. Each `session_id` isolates todos, just like PostgreSQL.

### When to Use

- Production applications needing fast, session-scoped storage
- Multi-user apps
- Sharing todo state across processes

## Storage Lifecycle

The async database backends ([`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage]
and [`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage]) require an explicit
lifecycle:

- **`initialize()` must be called before use.** Postgres creates its connection
  pool and ensures the table exists; Redis creates its client and verifies
  connectivity with a `PING`. Every storage operation calls an internal
  `_ensure_initialized()` check that raises `RuntimeError("Storage not
  initialized. Call initialize() first.")` if you skip it. `AsyncRedisStorage.initialize()`
  is idempotent — calling it again after a successful init is a no-op.
- **`close()` only closes resources this storage owns.** If the pool/client was
  created internally from `connection_string`/`url`, `close()` shuts it down. If
  you passed an existing `pool=` or `client=`, it is left open for you to manage.

[`AsyncMemoryStorage`][pydantic_ai_todo.AsyncMemoryStorage] has no
`initialize()`/`close()` requirements.

## Factory Function

Use `create_storage()` for consistent backend creation:

```python
from pydantic_ai_todo import create_storage

# Memory (default)
storage = create_storage("memory")

# PostgreSQL
storage = create_storage(
    "postgres",
    connection_string="postgresql://...",
    session_id="user-123",
    table_name="todos",  # optional
    event_emitter=emitter,  # optional
)

# Redis
storage = create_storage(
    "redis",
    url="redis://localhost:6379",
    session_id="user-123",
    key_prefix="todos",  # optional
    event_emitter=emitter,  # optional
)
```

## Protocols

### TodoStorageProtocol

The interface for sync storage — any object exposing a read/write `todos`
property satisfies it. See the full signature in the API reference:
[`TodoStorageProtocol`][pydantic_ai_todo.TodoStorageProtocol].

### AsyncTodoStorageProtocol

The interface for async storage. Note that `update_todo` takes explicit keyword
parameters (`content`, `status`, `active_form`, `parent_id`, `depends_on`), not
arbitrary `**fields`. See the full signature in the API reference:
[`AsyncTodoStorageProtocol`][pydantic_ai_todo.AsyncTodoStorageProtocol].

## Custom Storage

!!! tip "Use the built-in backend for production"

    The example below shows how to implement
    [`AsyncTodoStorageProtocol`][pydantic_ai_todo.AsyncTodoStorageProtocol] for a
    custom backend. For real Redis usage, prefer the built-in
    [`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage] (atomic pipelines,
    insertion ordering, multi-tenancy, events) rather than hand-rolling one.

Implement the protocol for custom backends:

```python
from pydantic_ai_todo import AsyncTodoStorageProtocol, Todo

class MyCustomStorage:
    """Example custom backend (illustrative — not production-ready)."""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def get_todos(self) -> list[Todo]:
        data = await self._redis.get("todos")
        return [Todo(**t) for t in json.loads(data)] if data else []

    async def set_todos(self, todos: list[Todo]) -> None:
        await self._redis.set("todos", json.dumps([t.model_dump() for t in todos]))

    # ... implement get_todo, add_todo, update_todo, remove_todo
```
