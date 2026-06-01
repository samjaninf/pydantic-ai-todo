# Migration Guide: Memory to PostgreSQL

How to move from in-memory storage to persistent PostgreSQL storage.

## Why Migrate?

| | InMemoryStorage | PostgreSQL |
|---|---|---|
| Persistence | Data lost on restart | Data survives restarts |
| Multi-tenancy | No | Yes (`session_id`) |
| Scalability | Single process | Multiple processes / servers |
| Use case | Prototyping, testing | Production |

## Step 1: Provision PostgreSQL

No extra install is needed — `asyncpg` is a core dependency of
`pydantic-ai-todo`. Just make sure you have a PostgreSQL server available and a
connection string to point at it.

## Step 2: Set Up PostgreSQL

You need a running PostgreSQL instance. The connection string format:

```
postgresql://username:password@host:port/database
```

Example with Docker:

```bash
docker run -d \
  --name todo-postgres \
  -e POSTGRES_USER=todouser \
  -e POSTGRES_PASSWORD=todopass \
  -e POSTGRES_DB=tododb \
  -p 5432:5432 \
  postgres:16
```

Connection string: `postgresql://todouser:todopass@localhost:5432/tododb`

## Step 3: Update Your Code

### Before (In-Memory)

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4o", toolsets=[toolset])
result = await agent.run("Plan the project")

todos = await storage.get_todos()
```

### After (PostgreSQL)

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, create_storage

storage = create_storage(
    "postgres",
    connection_string="postgresql://todouser:todopass@localhost:5432/tododb",
    session_id="default",  # Required for PostgreSQL
)
await storage.initialize()  # Creates table if needed

toolset = create_todo_toolset(async_storage=storage)

agent = Agent("openai:gpt-4o", toolsets=[toolset])
result = await agent.run("Plan the project")

todos = await storage.get_todos()

# Clean up when done
await storage.close()
```

### Key Differences

| Change | Details |
|--------|---------|
| `AsyncMemoryStorage()` | Replace with `create_storage("postgres", ...)` |
| No initialization needed | Add `await storage.initialize()` after creation |
| No session_id | Add `session_id` parameter (required) |
| No cleanup needed | Add `await storage.close()` when done |

## Step 4: Migrate Existing Data (Optional)

If you have in-memory data that needs to be transferred to PostgreSQL,
use the shared `AsyncTodoStorageProtocol` interface:

```python
from pydantic_ai_todo import AsyncMemoryStorage, create_storage

# Source: your existing in-memory storage with data
memory_storage = AsyncMemoryStorage()
# ... assume memory_storage has todos from a previous run

# Destination: new PostgreSQL storage
pg_storage = create_storage(
    "postgres",
    connection_string="postgresql://todouser:todopass@localhost:5432/tododb",
    session_id="migrated-data",
)
await pg_storage.initialize()

# Transfer all todos
todos = await memory_storage.get_todos()
for todo in todos:
    await pg_storage.add_todo(todo)

print(f"Migrated {len(todos)} todos to PostgreSQL")

await pg_storage.close()
```

## Step 5: Add Proper Lifecycle Management

In a real application, manage the database connection lifecycle properly.

### Standalone Script

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_storage, create_todo_toolset

async def main():
    storage = create_storage(
        "postgres",
        connection_string="postgresql://todouser:todopass@localhost:5432/tododb",
        session_id="session-1",
    )
    await storage.initialize()

    try:
        toolset = create_todo_toolset(async_storage=storage)
        agent = Agent("openai:gpt-4o", toolsets=[toolset])
        result = await agent.run("Create tasks for the sprint")
        print(result.output)
    finally:
        await storage.close()

asyncio.run(main())
```

### FastAPI Application

```python
import asyncpg
from fastapi import FastAPI
from pydantic_ai import Agent
from pydantic_ai_todo import AsyncPostgresStorage, create_todo_toolset

app = FastAPI()
pool: asyncpg.Pool | None = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(
        "postgresql://todouser:todopass@localhost:5432/tododb",
        min_size=5,
        max_size=20,
    )
    # Ensure table exists
    storage = AsyncPostgresStorage(pool=pool, session_id="__setup__")
    await storage.initialize()

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

@app.post("/plan")
async def create_plan(user_id: str, prompt: str):
    assert pool is not None
    storage = AsyncPostgresStorage(pool=pool, session_id=user_id)
    await storage.initialize()

    toolset = create_todo_toolset(async_storage=storage)
    agent = Agent("openai:gpt-4o", toolsets=[toolset])

    result = await agent.run(prompt)
    todos = await storage.get_todos()

    return {
        "response": result.output,
        "tasks": [t.model_dump() for t in todos],
    }
```

## Step 6: Environment Variables

Keep connection strings out of source code:

```python
import os
from pydantic_ai_todo import create_storage

storage = create_storage(
    "postgres",
    connection_string=os.environ["DATABASE_URL"],
    session_id="default",
)
```

```bash
export DATABASE_URL="postgresql://todouser:todopass@localhost:5432/tododb"
```

## Database Schema Reference

The table is auto-created by `initialize()`:

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

!!! tip
    The table name defaults to `"todos"` but can be customized:
    ```python
    storage = create_storage(
        "postgres",
        connection_string="postgresql://...",
        session_id="default",
        table_name="my_custom_tasks",
    )
    ```

## Checklist

- [ ] Install `asyncpg`
- [ ] Set up PostgreSQL instance
- [ ] Replace `AsyncMemoryStorage()` with `create_storage("postgres", ...)`
- [ ] Add `await storage.initialize()` call
- [ ] Add `session_id` parameter
- [ ] Add `await storage.close()` in cleanup
- [ ] Move connection string to environment variable
- [ ] Migrate existing data if needed
