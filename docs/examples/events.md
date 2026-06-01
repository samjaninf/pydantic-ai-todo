# Events Example

Reacting to task changes with callbacks.

!!! warning "Events require an async storage backend"

    Events fire only from the async storage backends
    ([`AsyncMemoryStorage`][pydantic_ai_todo.AsyncMemoryStorage],
    [`AsyncPostgresStorage`][pydantic_ai_todo.AsyncPostgresStorage],
    [`AsyncRedisStorage`][pydantic_ai_todo.AsyncRedisStorage]) when constructed
    with an `event_emitter`. The sync [`TodoStorage`][pydantic_ai_todo.TodoStorage]
    and the sync toolset path emit nothing. The examples below all use
    `async_storage=`.

## Basic Event Handling

```python
import asyncio
from pydantic_ai import Agent
from pydantic_ai_todo import (
    create_todo_toolset,
    AsyncMemoryStorage,
    TodoEventEmitter,
)

async def main():
    emitter = TodoEventEmitter()
    
    @emitter.on_created
    async def on_created(event):
        print(f"📝 Created: {event.todo.content}")
    
    @emitter.on_completed
    async def on_completed(event):
        print(f"✅ Completed: {event.todo.content}")
    
    @emitter.on_deleted
    async def on_deleted(event):
        print(f"🗑️ Deleted: {event.todo.content}")
    
    storage = AsyncMemoryStorage(event_emitter=emitter)
    toolset = create_todo_toolset(async_storage=storage)
    
    agent = Agent("openai:gpt-4o", toolsets=[toolset])
    
    await agent.run("Create 3 tasks, complete 2, and delete 1")

asyncio.run(main())
```

## Output

```
📝 Created: Set up project structure
📝 Created: Write documentation
📝 Created: Deploy application
✅ Completed: Set up project structure
✅ Completed: Write documentation
🗑️ Deleted: Deploy application
```

## Webhook Integration

```python
import httpx
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()

@emitter.on_completed
async def send_webhook(event):
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://hooks.slack.com/services/...",
            json={
                "text": f"Task completed: {event.todo.content}",
                "channel": "#tasks",
            },
        )

storage = AsyncMemoryStorage(event_emitter=emitter)
```

## Audit Logging

```python
from datetime import datetime
from pydantic_ai_todo import TodoEventEmitter, TodoEventType

emitter = TodoEventEmitter()
audit_log = []

@emitter.on_created
@emitter.on_updated
@emitter.on_deleted
async def log_event(event):
    audit_log.append({
        "timestamp": event.timestamp.isoformat(),
        "type": event.event_type.value,
        "todo_id": event.todo.id,
        "content": event.todo.content,
        "status": event.todo.status,
        "previous": event.previous_state.model_dump() if event.previous_state else None,
    })

# Later
for entry in audit_log:
    print(f"[{entry['timestamp']}] {entry['type']}: {entry['content']}")
```

## Real-time Updates (WebSocket)

```python
from fastapi import FastAPI, WebSocket
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage

app = FastAPI()
connections: list[WebSocket] = []

emitter = TodoEventEmitter()

@emitter.on_created
@emitter.on_updated
@emitter.on_completed
@emitter.on_deleted
async def broadcast(event):
    message = {
        "type": event.event_type.value,
        "todo": event.todo.model_dump(),
    }
    for ws in connections:
        await ws.send_json(message)

storage = AsyncMemoryStorage(event_emitter=emitter)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    finally:
        connections.remove(websocket)
```

## Progress Tracking

```python
from pydantic_ai_todo import TodoEventEmitter, AsyncMemoryStorage

emitter = TodoEventEmitter()
stats = {"created": 0, "completed": 0}

@emitter.on_created
async def track_created(event):
    stats["created"] += 1
    print(f"Progress: {stats['completed']}/{stats['created']} tasks")

@emitter.on_completed
async def track_completed(event):
    stats["completed"] += 1
    pct = (stats["completed"] / stats["created"]) * 100 if stats["created"] else 0
    print(f"Progress: {stats['completed']}/{stats['created']} ({pct:.0f}%)")

storage = AsyncMemoryStorage(event_emitter=emitter)
```

## All Event Types

```python
from pydantic_ai_todo import TodoEventEmitter, TodoEventType

emitter = TodoEventEmitter()

@emitter.on_created
async def on_created(event):
    """New task was created."""
    pass

@emitter.on_updated
async def on_updated(event):
    """Task was modified (any field)."""
    pass

@emitter.on_status_changed
async def on_status_changed(event):
    """Task status changed."""
    old = event.previous_state.status if event.previous_state else None
    new = event.todo.status
    print(f"Status: {old} → {new}")

@emitter.on_completed
async def on_completed(event):
    """Task was marked completed."""
    pass

@emitter.on_deleted
async def on_deleted(event):
    """Task was removed."""
    pass
```

## Event Order

When completing a task, events fire in order:

1. `UPDATED` — The task was modified
2. `STATUS_CHANGED` — Status specifically changed
3. `COMPLETED` — Task reached completed status
