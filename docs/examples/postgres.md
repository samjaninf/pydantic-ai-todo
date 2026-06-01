# PostgreSQL Storage

Persistent storage with PostgreSQL and multi-tenancy support.

## Prerequisites

`asyncpg` ships as a core dependency of `pydantic-ai-todo`, so no extra install
is required — you only need a running PostgreSQL server to connect to.

## Basic Usage

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_storage, create_todo_toolset

async def main():
    # Create PostgreSQL storage
    storage = create_storage(
        "postgres",
        connection_string="postgresql://user:pass@localhost/mydb",
        session_id="user-123",
    )
    
    # Initialize (creates table if needed)
    await storage.initialize()
    
    try:
        toolset = create_todo_toolset(async_storage=storage)
        agent = Agent("openai:gpt-4o", toolsets=[toolset])
        
        result = await agent.run("Plan the Q1 roadmap")
        print(result.output)
        
        # Todos are persisted!
        todos = await storage.get_todos()
        print(f"\n{len(todos)} tasks saved to PostgreSQL")
    
    finally:
        await storage.close()

asyncio.run(main())
```

## Multi-Tenancy

Each `session_id` gets isolated todos:

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import create_storage, create_todo_toolset

async def main():
    connection_string = "postgresql://user:pass@localhost/mydb"
    
    # User A's session
    storage_a = create_storage(
        "postgres",
        connection_string=connection_string,
        session_id="user-alice",
    )
    await storage_a.initialize()
    
    # User B's session
    storage_b = create_storage(
        "postgres",
        connection_string=connection_string,
        session_id="user-bob",
    )
    await storage_b.initialize()
    
    # Create toolsets
    toolset_a = create_todo_toolset(async_storage=storage_a)
    toolset_b = create_todo_toolset(async_storage=storage_b)
    
    # Each user has separate todos
    agent_a = Agent("openai:gpt-4o", toolsets=[toolset_a])
    agent_b = Agent("openai:gpt-4o", toolsets=[toolset_b])
    
    await agent_a.run("Create tasks for Alice's project")
    await agent_b.run("Create tasks for Bob's project")
    
    # They don't see each other's tasks
    alice_todos = await storage_a.get_todos()
    bob_todos = await storage_b.get_todos()
    
    print(f"Alice has {len(alice_todos)} tasks")
    print(f"Bob has {len(bob_todos)} tasks")
    
    await storage_a.close()
    await storage_b.close()

asyncio.run(main())
```

## With Connection Pool

For production apps, use a shared connection pool:

```python
import asyncio
import asyncpg
from pydantic_ai import Agent
from pydantic_ai_todo import AsyncPostgresStorage, create_todo_toolset

async def main():
    # Create shared pool
    pool = await asyncpg.create_pool(
        "postgresql://user:pass@localhost/mydb",
        min_size=5,
        max_size=20,
    )
    
    try:
        # Create storage with pool
        storage = AsyncPostgresStorage(
            pool=pool,
            session_id="user-123",
        )
        await storage.initialize()
        
        toolset = create_todo_toolset(async_storage=storage)
        agent = Agent("openai:gpt-4o", toolsets=[toolset])
        
        await agent.run("Plan the sprint")
        
    finally:
        # Pool is NOT closed by storage.close()
        # You manage pool lifecycle
        await pool.close()

asyncio.run(main())
```

## With Events

```python
from pydantic_ai_todo import create_storage, TodoEventEmitter

emitter = TodoEventEmitter()

@emitter.on_completed
async def notify_completion(event):
    # Send notification, update dashboard, etc.
    print(f"Task completed: {event.todo.content}")

storage = create_storage(
    "postgres",
    connection_string="postgresql://...",
    session_id="user-123",
    event_emitter=emitter,
)
```

## Custom Table Name

```python
storage = create_storage(
    "postgres",
    connection_string="postgresql://...",
    session_id="user-123",
    table_name="project_tasks",  # Default: "todos"
)
```

## Database Schema

The table is auto-created:

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

## FastAPI Integration

```python
from fastapi import FastAPI, Depends
from pydantic_ai import Agent
from pydantic_ai_todo import create_storage, create_todo_toolset
import asyncpg

app = FastAPI()
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool("postgresql://...")

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

async def get_storage(user_id: str):
    from pydantic_ai_todo import AsyncPostgresStorage
    storage = AsyncPostgresStorage(pool=pool, session_id=user_id)
    await storage.initialize()
    return storage

@app.post("/plan")
async def create_plan(user_id: str, prompt: str):
    storage = await get_storage(user_id)
    toolset = create_todo_toolset(async_storage=storage)
    agent = Agent("openai:gpt-4o", toolsets=[toolset])
    
    result = await agent.run(prompt)
    todos = await storage.get_todos()
    
    return {
        "response": result.output,
        "tasks": [t.model_dump() for t in todos],
    }
```
