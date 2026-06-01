"""Storage abstraction for todo items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol, overload, runtime_checkable

import asyncpg
import redis.asyncio as redis_async

from pydantic_ai_todo.types import Todo

if TYPE_CHECKING:
    from pydantic_ai_todo.events import TodoEventEmitter


@runtime_checkable
class TodoStorageProtocol(Protocol):
    """Protocol for todo storage implementations.

    Any class that has a `todos` property (read/write) implementing
    `list[Todo]` can be used as storage for the todo toolset.

    Example:
        ```python
        class MyCustomStorage:
            def __init__(self):
                self._todos: list[Todo] = []

            @property
            def todos(self) -> list[Todo]:
                return self._todos

            @todos.setter
            def todos(self, value: list[Todo]) -> None:
                self._todos = value
        ```
    """

    @property
    def todos(self) -> list[Todo]:
        """Get the current list of todos."""
        ...

    @todos.setter
    def todos(self, value: list[Todo]) -> None:
        """Set the list of todos."""
        ...


@dataclass
class TodoStorage:
    """Default in-memory todo storage.

    Simple implementation that stores todos in memory.
    Use this for standalone agents or testing.

    Example:
        ```python
        from pydantic_ai_todo import create_todo_toolset, TodoStorage

        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)

        # After agent runs, access todos directly
        print(storage.todos)
        ```
    """

    _todos: list[Todo] = field(default_factory=lambda: [])

    @property
    def todos(self) -> list[Todo]:
        """Get the current list of todos."""
        return self._todos

    @todos.setter
    def todos(self, value: list[Todo]) -> None:
        """Set the list of todos."""
        self._todos = value


class AsyncTodoStorageProtocol(Protocol):
    """Protocol for async todo storage implementations.

    This protocol defines the interface for async storage backends
    that support true persistence (database, file, etc.).

    Example:
        ```python
        class MyAsyncStorage:
            async def get_todos(self) -> list[Todo]:
                return await db.fetch_todos()

            async def set_todos(self, todos: list[Todo]) -> None:
                await db.save_todos(todos)

            async def get_todo(self, id: str) -> Todo | None:
                return await db.get_todo(id)

            async def add_todo(self, todo: Todo) -> Todo:
                return await db.insert_todo(todo)

            async def update_todo(self, id: str, **fields) -> Todo | None:
                return await db.update_todo(id, fields)

            async def remove_todo(self, id: str) -> bool:
                return await db.delete_todo(id)
        ```
    """

    async def get_todos(self) -> list[Todo]:
        """Get all todos."""
        ...

    async def set_todos(self, todos: list[Todo]) -> None:
        """Replace all todos with the provided list."""
        ...

    async def get_todo(self, id: str) -> Todo | None:
        """Get a single todo by ID."""
        ...

    async def add_todo(self, todo: Todo) -> Todo:
        """Add a new todo and return it."""
        ...

    async def update_todo(
        self,
        id: str,
        *,
        content: str | None = None,
        status: Literal["pending", "in_progress", "completed", "blocked"] | None = None,
        active_form: str | None = None,
        parent_id: str | None = None,
        depends_on: list[str] | None = None,
    ) -> Todo | None:
        """Update a todo's fields by ID. Returns None if not found."""
        ...

    async def remove_todo(self, id: str) -> bool:
        """Remove a todo by ID. Returns True if removed, False if not found."""
        ...


class AsyncMemoryStorage:
    """Async in-memory todo storage.

    Implements AsyncTodoStorageProtocol for testing and simple use cases.
    Data is stored in memory and lost when the process ends.

    Example:
        ```python
        from pydantic_ai_todo import AsyncMemoryStorage, create_todo_toolset

        storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(async_storage=storage)

        # After agent runs, access todos
        todos = await storage.get_todos()
        ```

    With event emitter:
        ```python
        from pydantic_ai_todo import AsyncMemoryStorage, TodoEventEmitter

        emitter = TodoEventEmitter()

        @emitter.on_created
        async def notify(event):
            print(f"Created: {event.todo.content}")

        storage = AsyncMemoryStorage(event_emitter=emitter)
        ```
    """

    def __init__(self, event_emitter: TodoEventEmitter | None = None) -> None:
        self._todos: list[Todo] = []
        self._event_emitter = event_emitter

    async def get_todos(self) -> list[Todo]:
        """Get all todos."""
        return list(self._todos)

    async def set_todos(self, todos: list[Todo]) -> None:
        """Replace all todos with the provided list."""
        self._todos = list(todos)

    async def get_todo(self, id: str) -> Todo | None:
        """Get a single todo by ID."""
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    async def add_todo(self, todo: Todo) -> Todo:
        """Add a new todo and return it."""
        self._todos.append(todo)
        if self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(TodoEvent(event_type=TodoEventType.CREATED, todo=todo))
        return todo

    async def update_todo(
        self,
        id: str,
        *,
        content: str | None = None,
        status: Literal["pending", "in_progress", "completed", "blocked"] | None = None,
        active_form: str | None = None,
        parent_id: str | None = None,
        depends_on: list[str] | None = None,
    ) -> Todo | None:
        """Update a todo's fields by ID. Returns None if not found."""
        for todo in self._todos:
            if todo.id == id:
                # Capture previous state for events
                previous_state = todo.model_copy() if self._event_emitter else None
                old_status = todo.status

                if content is not None:
                    todo.content = content
                if status is not None:
                    todo.status = status
                if active_form is not None:
                    todo.active_form = active_form
                if parent_id is not None:
                    todo.parent_id = parent_id
                if depends_on is not None:
                    todo.depends_on = depends_on

                # Emit events
                if self._event_emitter:
                    from pydantic_ai_todo.events import TodoEvent, TodoEventType

                    # Always emit UPDATED
                    await self._event_emitter.emit(
                        TodoEvent(
                            event_type=TodoEventType.UPDATED,
                            todo=todo,
                            previous_state=previous_state,
                        )
                    )

                    # Emit STATUS_CHANGED if status changed
                    if status is not None and status != old_status:
                        await self._event_emitter.emit(
                            TodoEvent(
                                event_type=TodoEventType.STATUS_CHANGED,
                                todo=todo,
                                previous_state=previous_state,
                            )
                        )

                        # Emit COMPLETED if newly completed
                        if status == "completed":
                            await self._event_emitter.emit(
                                TodoEvent(
                                    event_type=TodoEventType.COMPLETED,
                                    todo=todo,
                                    previous_state=previous_state,
                                )
                            )

                return todo
        return None

    async def remove_todo(self, id: str) -> bool:
        """Remove a todo by ID. Returns True if removed, False if not found."""
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                removed_todo = self._todos.pop(i)
                if self._event_emitter:
                    from pydantic_ai_todo.events import TodoEvent, TodoEventType

                    await self._event_emitter.emit(
                        TodoEvent(event_type=TodoEventType.DELETED, todo=removed_todo)
                    )
                return True
        return False


class AsyncPostgresStorage:
    """Async PostgreSQL todo storage.

    Implements AsyncTodoStorageProtocol with PostgreSQL backend.
    Supports session-based multi-tenancy via session_id.

    Example with connection string:
        ```python
        from pydantic_ai_todo import AsyncPostgresStorage

        storage = AsyncPostgresStorage(
            connection_string="postgresql://user:pass@localhost/db",
            session_id="user-123"
        )
        await storage.initialize()  # Creates table if not exists

        # Use with toolset
        toolset = create_todo_toolset(async_storage=storage)
        ```

    Example with existing pool:
        ```python
        import asyncpg
        from pydantic_ai_todo import AsyncPostgresStorage

        pool = await asyncpg.create_pool("postgresql://...")
        storage = AsyncPostgresStorage(pool=pool, session_id="user-123")
        await storage.initialize()
        ```
    """

    _CREATE_TABLE_SQL = """
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
    """

    def __init__(
        self,
        *,
        connection_string: str | None = None,
        pool: asyncpg.Pool | None = None,
        session_id: str,
        table_name: str = "todos",
        event_emitter: TodoEventEmitter | None = None,
    ) -> None:
        """Initialize PostgreSQL storage.

        Args:
            connection_string: PostgreSQL connection string. Either this or pool required.
            pool: Existing asyncpg connection pool. Either this or connection_string required.
            session_id: Unique identifier for this session/user. All operations are scoped to this.
            table_name: Name of the todos table (default: "todos").
            event_emitter: Optional event emitter to receive CRUD events.

        Raises:
            ValueError: If neither connection_string nor pool is provided.
        """
        if connection_string is None and pool is None:
            raise ValueError("Either connection_string or pool must be provided")

        self._connection_string = connection_string
        self._external_pool = pool
        self._pool: asyncpg.Pool | None = pool
        self._session_id = session_id
        self._table_name = table_name
        self._event_emitter = event_emitter
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize storage: create pool if needed and ensure table exists.

        Must be called before using the storage.
        """
        if self._pool is None and self._connection_string:
            self._pool = await asyncpg.create_pool(self._connection_string)

        if self._pool:
            async with self._pool.acquire() as conn:
                await conn.execute(self._CREATE_TABLE_SQL)
            self._initialized = True

    async def close(self) -> None:
        """Close the connection pool if we created it.

        Only closes the pool if it was created from connection_string.
        External pools passed via pool parameter are not closed.
        """
        if self._pool and self._external_pool is None:
            await self._pool.close()
            self._pool = None

    def _ensure_initialized(self) -> asyncpg.Pool:
        """Ensure storage is initialized and return pool."""
        if not self._initialized or self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return self._pool

    def _record_to_todo(self, record: asyncpg.Record) -> Todo:
        """Convert database record to Todo model."""
        return Todo(
            id=record["id"],
            content=record["content"],
            status=record["status"],
            active_form=record["active_form"],
            parent_id=record["parent_id"],
            depends_on=list(record["depends_on"]) if record["depends_on"] else [],
        )

    async def get_todos(self) -> list[Todo]:
        """Get all todos for current session."""
        pool = self._ensure_initialized()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM {self._table_name} WHERE session_id = $1 ORDER BY created_at",
                self._session_id,
            )
            return [self._record_to_todo(row) for row in rows]

    async def set_todos(self, todos: list[Todo]) -> None:
        """Replace all todos for current session."""
        pool = self._ensure_initialized()
        async with pool.acquire() as conn, conn.transaction():
            # Delete existing todos for this session
            await conn.execute(
                f"DELETE FROM {self._table_name} WHERE session_id = $1",
                self._session_id,
            )
            # Insert new todos
            for todo in todos:
                await conn.execute(
                    f"""
                    INSERT INTO {self._table_name}
                    (id, session_id, content, status, active_form, parent_id, depends_on)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    todo.id,
                    self._session_id,
                    todo.content,
                    todo.status,
                    todo.active_form,
                    todo.parent_id,
                    todo.depends_on,
                )

    async def get_todo(self, id: str) -> Todo | None:
        """Get a single todo by ID for current session."""
        pool = self._ensure_initialized()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self._table_name} WHERE id = $1 AND session_id = $2",
                id,
                self._session_id,
            )
            return self._record_to_todo(row) if row else None

    async def add_todo(self, todo: Todo) -> Todo:
        """Add a new todo for current session."""
        pool = self._ensure_initialized()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self._table_name}
                (id, session_id, content, status, active_form, parent_id, depends_on)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                todo.id,
                self._session_id,
                todo.content,
                todo.status,
                todo.active_form,
                todo.parent_id,
                todo.depends_on,
            )

        if self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(TodoEvent(event_type=TodoEventType.CREATED, todo=todo))

        return todo

    async def update_todo(
        self,
        id: str,
        *,
        content: str | None = None,
        status: Literal["pending", "in_progress", "completed", "blocked"] | None = None,
        active_form: str | None = None,
        parent_id: str | None = None,
        depends_on: list[str] | None = None,
    ) -> Todo | None:
        """Update a todo's fields by ID for current session."""
        pool = self._ensure_initialized()

        # First get the current todo
        current = await self.get_todo(id)
        if current is None:
            return None

        previous_state = current.model_copy() if self._event_emitter else None
        old_status = current.status

        # Build update query dynamically
        updates: list[str] = ["updated_at = NOW()"]
        params: list[str | list[str]] = []
        param_idx = 1

        if content is not None:
            updates.append(f"content = ${param_idx}")
            params.append(content)
            param_idx += 1
        if status is not None:
            updates.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1
        if active_form is not None:
            updates.append(f"active_form = ${param_idx}")
            params.append(active_form)
            param_idx += 1
        if parent_id is not None:
            updates.append(f"parent_id = ${param_idx}")
            params.append(parent_id)
            param_idx += 1
        if depends_on is not None:
            updates.append(f"depends_on = ${param_idx}")
            params.append(depends_on)
            param_idx += 1

        # Add id and session_id to params
        params.append(id)
        params.append(self._session_id)

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE {self._table_name}
                SET {", ".join(updates)}
                WHERE id = ${param_idx} AND session_id = ${param_idx + 1}
                """,
                *params,
            )

        # Get updated todo
        updated = await self.get_todo(id)

        # Emit events
        if updated and self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(
                TodoEvent(
                    event_type=TodoEventType.UPDATED,
                    todo=updated,
                    previous_state=previous_state,
                )
            )

            if status is not None and status != old_status:
                await self._event_emitter.emit(
                    TodoEvent(
                        event_type=TodoEventType.STATUS_CHANGED,
                        todo=updated,
                        previous_state=previous_state,
                    )
                )

                if status == "completed":
                    await self._event_emitter.emit(
                        TodoEvent(
                            event_type=TodoEventType.COMPLETED,
                            todo=updated,
                            previous_state=previous_state,
                        )
                    )

        return updated

    async def remove_todo(self, id: str) -> bool:
        """Remove a todo by ID for current session."""
        pool = self._ensure_initialized()

        # Get todo before deletion for event
        todo = await self.get_todo(id) if self._event_emitter else None

        async with pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name} WHERE id = $1 AND session_id = $2",
                id,
                self._session_id,
            )

        deleted = result == "DELETE 1"

        if deleted and todo and self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(TodoEvent(event_type=TodoEventType.DELETED, todo=todo))

        return deleted


class AsyncRedisStorage:
    """Async Redis todo storage.

    Implements AsyncTodoStorageProtocol with Redis backend.
    Supports session-based multi-tenancy via session_id.

    Todos are stored in a Redis Hash (one field per todo, JSON-serialized)
    with a companion List to maintain insertion order.

    Example with URL:
        ```python
        from pydantic_ai_todo import AsyncRedisStorage

        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="user-123"
        )
        await storage.initialize()

        # Use with toolset
        toolset = create_todo_toolset(async_storage=storage)
        ```

    Example with existing client:
        ```python
        import redis.asyncio as redis_async
        from pydantic_ai_todo import AsyncRedisStorage

        client = redis_async.from_url("redis://localhost:6379")
        storage = AsyncRedisStorage(client=client, session_id="user-123")
        await storage.initialize()
        ```
    """

    def __init__(
        self,
        *,
        url: str | None = None,
        client: redis_async.Redis | None = None,  # type: ignore[type-arg]
        session_id: str,
        key_prefix: str = "todos",
        event_emitter: TodoEventEmitter | None = None,
    ) -> None:
        """Initialize Redis storage.

        Args:
            url: Redis URL (e.g. `redis://localhost:6379`).
                Either this or client is required.
            client: Existing `redis.asyncio.Redis` client.
                Either this or url is required.
            session_id: Unique identifier for this session/user.
                All operations are scoped to this.
            key_prefix: Prefix for Redis keys (default: `"todos"`).
            event_emitter: Optional event emitter to receive CRUD events.

        Raises:
            ValueError: If neither url nor client is provided.
        """
        if url is None and client is None:
            raise ValueError("Either url or client must be provided")

        self._url = url
        self._external_client = client
        self._client: redis_async.Redis | None = client  # type: ignore[type-arg]
        self._session_id = session_id
        self._key_prefix = key_prefix
        self._event_emitter = event_emitter
        self._initialized = False

    @property
    def _hash_key(self) -> str:
        """Redis Hash key storing todo data keyed by todo ID.

        The session id is wrapped in `{...}` so Redis Cluster hashes
        it as a single hash-tag, keeping :attr:`_hash_key` and
        :attr:`_order_key` co-located on the same slot. Without that
        guarantee the multi-key pipelines in :meth:`set_todos`,
        :meth:`add_todo` and :meth:`remove_todo` would fail with
        `CROSSSLOT` under clustered deployments. On single-node Redis
        the hash-tag is a no-op.
        """
        return f"{self._key_prefix}:{{{self._session_id}}}"

    @property
    def _order_key(self) -> str:
        """Redis List key maintaining insertion order of todo IDs.

        Shares the `{session_id}` hash-tag with :attr:`_hash_key` so
        both keys route to the same Redis Cluster slot.
        """
        return f"{self._key_prefix}:{{{self._session_id}}}:order"

    async def initialize(self) -> None:
        """Initialize storage: create client if needed and verify connectivity.

        Idempotent — calling more than once is a no-op after the first
        successful initialization.
        """
        if self._initialized:
            return

        if self._client is None and self._url:
            self._client = redis_async.from_url(self._url)

        if self._client:
            await self._client.ping()  # type: ignore[misc]
            self._initialized = True

    async def close(self) -> None:
        """Close the Redis client if we created it.

        Only closes the client if it was created from url.
        External clients passed via client parameter are not closed.
        """
        if self._client and self._external_client is None:
            await self._client.aclose()
            self._client = None

    def _ensure_initialized(self) -> redis_async.Redis:  # type: ignore[type-arg]
        """Ensure storage is initialized and return client."""
        if not self._initialized or self._client is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return self._client

    async def get_todos(self) -> list[Todo]:
        """Get all todos for current session, in insertion order."""
        client = self._ensure_initialized()
        order_raw: list[bytes] = await client.lrange(self._order_key, 0, -1)  # type: ignore[misc]
        if not order_raw:
            return []

        pipe = client.pipeline()
        for todo_id_bytes in order_raw:
            pipe.hget(self._hash_key, todo_id_bytes.decode())
        results: list[bytes | None] = await pipe.execute()

        todos: list[Todo] = []
        for data in results:
            if data is not None:
                todos.append(Todo.model_validate_json(data))
        return todos

    async def set_todos(self, todos: list[Todo]) -> None:
        """Replace all todos for current session atomically."""
        client = self._ensure_initialized()
        pipe = client.pipeline()
        pipe.delete(self._hash_key)
        pipe.delete(self._order_key)
        for todo in todos:
            pipe.hset(self._hash_key, todo.id, todo.model_dump_json())
            pipe.rpush(self._order_key, todo.id)
        await pipe.execute()

    async def get_todo(self, id: str) -> Todo | None:
        """Get a single todo by ID for current session."""
        client = self._ensure_initialized()
        data: bytes | None = await client.hget(self._hash_key, id)  # type: ignore[misc]
        if data is not None:
            return Todo.model_validate_json(data)
        return None

    async def add_todo(self, todo: Todo) -> Todo:
        """Add a new todo for current session."""
        client = self._ensure_initialized()
        pipe = client.pipeline()
        pipe.hset(self._hash_key, todo.id, todo.model_dump_json())
        pipe.rpush(self._order_key, todo.id)
        await pipe.execute()

        if self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(TodoEvent(event_type=TodoEventType.CREATED, todo=todo))

        return todo

    async def update_todo(
        self,
        id: str,
        *,
        content: str | None = None,
        status: Literal["pending", "in_progress", "completed", "blocked"] | None = None,
        active_form: str | None = None,
        parent_id: str | None = None,
        depends_on: list[str] | None = None,
    ) -> Todo | None:
        """Update a todo's fields by ID for current session."""
        current = await self.get_todo(id)
        if current is None:
            return None

        previous_state = current.model_copy() if self._event_emitter else None
        old_status = current.status

        if content is not None:
            current.content = content
        if status is not None:
            current.status = status
        if active_form is not None:
            current.active_form = active_form
        if parent_id is not None:
            current.parent_id = parent_id
        if depends_on is not None:
            current.depends_on = depends_on

        client = self._ensure_initialized()
        await client.hset(self._hash_key, id, current.model_dump_json())  # type: ignore[misc]

        if self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(
                TodoEvent(
                    event_type=TodoEventType.UPDATED,
                    todo=current,
                    previous_state=previous_state,
                )
            )

            if status is not None and status != old_status:
                await self._event_emitter.emit(
                    TodoEvent(
                        event_type=TodoEventType.STATUS_CHANGED,
                        todo=current,
                        previous_state=previous_state,
                    )
                )

                if status == "completed":
                    await self._event_emitter.emit(
                        TodoEvent(
                            event_type=TodoEventType.COMPLETED,
                            todo=current,
                            previous_state=previous_state,
                        )
                    )

        return current

    async def remove_todo(self, id: str) -> bool:
        """Remove a todo by ID for current session.

        Hash and order-list deletion happen atomically inside a single
        pipeline so a connection drop between the two cannot leave the
        order list pointing at a deleted hash entry.
        """
        client = self._ensure_initialized()

        todo = await self.get_todo(id) if self._event_emitter else None

        # Pipeline both ops so we never end up with an orphaned id in the
        # order list. `lrem` on a missing id is a no-op, so it is safe
        # to send unconditionally.
        pipe = client.pipeline()
        pipe.hdel(self._hash_key, id)
        pipe.lrem(self._order_key, 1, id)
        results: list[int] = await pipe.execute()

        deleted = int(results[0]) > 0

        if deleted and todo and self._event_emitter:
            from pydantic_ai_todo.events import TodoEvent, TodoEventType

            await self._event_emitter.emit(TodoEvent(event_type=TodoEventType.DELETED, todo=todo))

        return deleted


@overload
def create_storage(
    backend: Literal["memory"] = "memory",
    *,
    event_emitter: TodoEventEmitter | None = None,
) -> AsyncMemoryStorage: ...


@overload
def create_storage(
    backend: Literal["postgres"],
    *,
    connection_string: str | None = None,
    pool: asyncpg.Pool | None = None,
    session_id: str,
    table_name: str = "todos",
    event_emitter: TodoEventEmitter | None = None,
) -> AsyncPostgresStorage: ...


@overload
def create_storage(
    backend: Literal["redis"],
    *,
    url: str | None = None,
    client: redis_async.Redis | None = None,  # type: ignore[type-arg]
    session_id: str,
    key_prefix: str = "todos",
    event_emitter: TodoEventEmitter | None = None,
) -> AsyncRedisStorage: ...


def create_storage(
    backend: Literal["memory", "postgres", "redis"] = "memory",
    *,
    connection_string: str | None = None,
    pool: asyncpg.Pool | None = None,
    url: str | None = None,
    client: redis_async.Redis | None = None,  # type: ignore[type-arg]
    session_id: str | None = None,
    table_name: str = "todos",
    key_prefix: str = "todos",
    event_emitter: TodoEventEmitter | None = None,
) -> AsyncMemoryStorage | AsyncPostgresStorage | AsyncRedisStorage:
    """Factory function to create storage backends.

    Args:
        backend: The storage backend to use (`"memory"`, `"postgres"`, or `"redis"`).
        connection_string: PostgreSQL connection string (postgres backend only).
        pool: Existing asyncpg pool (postgres backend only).
        url: Redis URL, e.g. `"redis://localhost:6379"` (redis backend only).
        client: Existing `redis.asyncio.Redis` client (redis backend only).
        session_id: Session identifier for multi-tenancy (postgres/redis, required).
        table_name: Database table name (postgres backend only, default: `"todos"`).
        key_prefix: Redis key prefix (redis backend only, default: `"todos"`).
        event_emitter: Optional event emitter to receive CRUD events.

    Returns:
        An async storage instance.

    Example (memory):
        ```python
        from pydantic_ai_todo import create_storage

        storage = create_storage("memory")
        toolset = create_todo_toolset(async_storage=storage)
        ```

    Example (postgres):
        ```python
        from pydantic_ai_todo import create_storage

        storage = create_storage(
            "postgres",
            connection_string="postgresql://user:pass@localhost/db",
            session_id="user-123"
        )
        await storage.initialize()  # Required for postgres
        ```

    Example (redis):
        ```python
        from pydantic_ai_todo import create_storage

        storage = create_storage(
            "redis",
            url="redis://localhost:6379",
            session_id="user-123"
        )
        await storage.initialize()  # Required for redis
        ```

    With events:
        ```python
        from pydantic_ai_todo import create_storage, TodoEventEmitter

        emitter = TodoEventEmitter()
        storage = create_storage("memory", event_emitter=emitter)
        ```
    """
    if backend == "memory":
        return AsyncMemoryStorage(event_emitter=event_emitter)

    if backend == "postgres":
        if session_id is None:
            raise ValueError("session_id is required for postgres backend")
        return AsyncPostgresStorage(
            connection_string=connection_string,
            pool=pool,
            session_id=session_id,
            table_name=table_name,
            event_emitter=event_emitter,
        )

    if backend == "redis":
        if session_id is None:
            raise ValueError("session_id is required for redis backend")
        return AsyncRedisStorage(
            url=url,
            client=client,
            session_id=session_id,
            key_prefix=key_prefix,
            event_emitter=event_emitter,
        )

    # This line is unreachable due to Literal type, but keeps future extensibility clear
    raise ValueError(f"Unknown storage backend: {backend}")  # pragma: no cover
