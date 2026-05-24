"""Tests for AsyncRedisStorage."""

# pyright: reportPrivateUsage=false
# pyright: reportArgumentType=false

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pydantic_ai_todo import (
    AsyncRedisStorage,
    Todo,
    TodoEvent,
    TodoEventEmitter,
    TodoEventType,
    create_storage,
)


class TestAsyncRedisStorageInit:
    """Tests for AsyncRedisStorage initialization."""

    def test_init_with_url(self) -> None:
        """Test initialization with URL."""
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="test-session",
        )
        assert storage._session_id == "test-session"
        assert storage._url == "redis://localhost:6379"
        assert storage._external_client is None
        assert not storage._initialized

    def test_init_with_client(self) -> None:
        """Test initialization with existing client."""
        mock_client = MagicMock()
        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
        )
        assert storage._session_id == "test-session"
        assert storage._external_client is mock_client
        assert storage._client is mock_client

    def test_init_requires_url_or_client(self) -> None:
        """Test that either url or client is required."""
        with pytest.raises(ValueError, match="Either url or client"):
            AsyncRedisStorage(session_id="test-session")

    def test_init_with_custom_key_prefix(self) -> None:
        """Test initialization with custom key prefix."""
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="test-session",
            key_prefix="custom_todos",
        )
        assert storage._key_prefix == "custom_todos"

    def test_init_with_event_emitter(self) -> None:
        """Test initialization with event emitter."""
        emitter = TodoEventEmitter()
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="test-session",
            event_emitter=emitter,
        )
        assert storage._event_emitter is emitter

    def test_hash_key_property(self) -> None:
        """_hash_key wraps the session id in a Redis Cluster hash-tag."""
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="user-123",
            key_prefix="mytodos",
        )
        assert storage._hash_key == "mytodos:{user-123}"

    def test_order_key_property(self) -> None:
        """_order_key shares the same hash-tag as _hash_key."""
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="user-123",
            key_prefix="mytodos",
        )
        assert storage._order_key == "mytodos:{user-123}:order"

    def test_keys_share_hash_tag_for_cluster_safety(self) -> None:
        """_hash_key and _order_key MUST land in the same Cluster slot.

        Redis Cluster routes by the substring between ``{`` and ``}``; if
        the two keys had different hash tags, the multi-key pipelines in
        set_todos/add_todo/remove_todo would fail with CROSSSLOT under a
        clustered deployment.
        """
        storage = AsyncRedisStorage(url="redis://localhost:6379", session_id="abc-xyz")
        hash_tag_h = storage._hash_key.split("{", 1)[1].split("}", 1)[0]
        hash_tag_o = storage._order_key.split("{", 1)[1].split("}", 1)[0]
        assert hash_tag_h == hash_tag_o == "abc-xyz"


class TestAsyncRedisStorageNotInitialized:
    """Tests for operations before initialization."""

    def test_ensure_initialized_raises_without_init(self) -> None:
        """Test that operations fail before initialize() is called."""
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="test-session",
        )
        with pytest.raises(RuntimeError, match="not initialized"):
            storage._ensure_initialized()


class TestAsyncRedisStorageMocked:
    """Tests for AsyncRedisStorage with mocked redis client."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.hget = AsyncMock(return_value=None)
        client.hset = AsyncMock(return_value=1)
        client.hdel = AsyncMock(return_value=1)
        client.lrange = AsyncMock(return_value=[])
        client.lrem = AsyncMock(return_value=1)
        client.delete = AsyncMock(return_value=1)
        client.aclose = AsyncMock()

        pipe = AsyncMock()
        pipe.hset = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.delete = MagicMock(return_value=pipe)
        pipe.hget = MagicMock(return_value=pipe)
        pipe.hdel = MagicMock(return_value=pipe)
        pipe.lrem = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[])
        client.pipeline = MagicMock(return_value=pipe)

        return client

    @pytest.fixture
    def storage(self, mock_client: MagicMock) -> AsyncRedisStorage:
        """Create storage with mocked client."""
        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
        )
        storage._initialized = True
        return storage

    async def test_initialize_pings_server(self, mock_client: MagicMock) -> None:
        """Test that initialize pings the Redis server."""
        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
        )
        await storage.initialize()

        mock_client.ping.assert_called_once()
        assert storage._initialized

    async def test_initialize_is_idempotent(self, mock_client: MagicMock) -> None:
        """Calling initialize() more than once is a no-op after the first."""
        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
        )
        await storage.initialize()
        await storage.initialize()
        await storage.initialize()

        # Only the first call should reach the server.
        mock_client.ping.assert_called_once()
        assert storage._initialized

    async def test_initialize_with_url(self) -> None:
        """Test that initialize creates client from URL."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)

        with patch("redis.asyncio.from_url", return_value=mock_client) as mock_from_url:
            storage = AsyncRedisStorage(
                url="redis://localhost:6379",
                session_id="test-session",
            )
            await storage.initialize()

            mock_from_url.assert_called_once_with("redis://localhost:6379")
            assert storage._client is mock_client
            assert storage._initialized

    async def test_close_closes_own_client(self) -> None:
        """Test that close() closes client created from URL."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="test-session",
        )
        storage._client = mock_client
        storage._external_client = None

        await storage.close()

        mock_client.aclose.assert_called_once()
        assert storage._client is None

    async def test_close_does_not_close_external_client(self, mock_client: MagicMock) -> None:
        """Test that close() doesn't close externally provided client."""
        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
        )
        storage._initialized = True

        await storage.close()

        mock_client.aclose.assert_not_called()

    async def test_get_todos_empty(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test getting todos when none exist."""
        mock_client.lrange = AsyncMock(return_value=[])

        todos = await storage.get_todos()

        assert todos == []

    async def test_get_todos(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """Test getting all todos."""
        todo = Todo(id="abc12345", content="Test task", status="pending", active_form="Testing")
        mock_client.lrange = AsyncMock(return_value=[b"abc12345"])

        pipe = AsyncMock()
        pipe.hget = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[todo.model_dump_json().encode()])
        mock_client.pipeline = MagicMock(return_value=pipe)

        todos = await storage.get_todos()

        assert len(todos) == 1
        assert todos[0].id == "abc12345"
        assert todos[0].content == "Test task"

    async def test_get_todos_skips_missing(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test that get_todos skips IDs in order list but missing from hash."""
        todo = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.lrange = AsyncMock(return_value=[b"abc12345", b"missing1"])

        pipe = AsyncMock()
        pipe.hget = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[todo.model_dump_json().encode(), None])
        mock_client.pipeline = MagicMock(return_value=pipe)

        todos = await storage.get_todos()

        assert len(todos) == 1
        assert todos[0].id == "abc12345"

    async def test_get_todo(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """Test getting a single todo."""
        todo = Todo(id="abc12345", content="Test task", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=todo.model_dump_json().encode())

        result = await storage.get_todo("abc12345")

        assert result is not None
        assert result.id == "abc12345"

    async def test_get_todo_not_found(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test getting a non-existent todo."""
        mock_client.hget = AsyncMock(return_value=None)

        result = await storage.get_todo("nonexistent")

        assert result is None

    async def test_add_todo(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """Test adding a todo."""
        pipe = AsyncMock()
        pipe.hset = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[1, 1])
        mock_client.pipeline = MagicMock(return_value=pipe)

        todo = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        result = await storage.add_todo(todo)

        assert result == todo
        pipe.hset.assert_called_once()
        pipe.rpush.assert_called_once()

    async def test_add_todo_emits_event(self, mock_client: MagicMock) -> None:
        """Test that add_todo emits CREATED event."""
        emitter = TodoEventEmitter()
        events: list[tuple[TodoEventType, Todo]] = []

        @emitter.on_created
        def callback(event: TodoEvent) -> None:
            events.append((event.event_type, event.todo))

        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        pipe = AsyncMock()
        pipe.hset = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[1, 1])
        mock_client.pipeline = MagicMock(return_value=pipe)

        todo = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        await storage.add_todo(todo)

        assert len(events) == 1
        assert events[0][0] == TodoEventType.CREATED
        assert events[0][1] == todo

    async def test_set_todos(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """Test setting all todos."""
        pipe = AsyncMock()
        pipe.delete = MagicMock(return_value=pipe)
        pipe.hset = MagicMock(return_value=pipe)
        pipe.rpush = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[1, 1, 1, 1, 1, 1])
        mock_client.pipeline = MagicMock(return_value=pipe)

        todos = [
            Todo(id="id1", content="Task 1", status="pending", active_form="T1"),
            Todo(id="id2", content="Task 2", status="pending", active_form="T2"),
        ]

        await storage.set_todos(todos)

        # 2 deletes + 2 hset + 2 rpush = 6 pipeline calls
        assert pipe.delete.call_count == 2
        assert pipe.hset.call_count == 2
        assert pipe.rpush.call_count == 2

    async def test_update_todo(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """Test updating a todo."""
        original = Todo(id="abc12345", content="Original", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())
        mock_client.hset = AsyncMock(return_value=1)

        result = await storage.update_todo("abc12345", content="Updated")

        assert result is not None
        assert result.content == "Updated"
        mock_client.hset.assert_called_once()

    async def test_update_todo_not_found(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test updating a non-existent todo."""
        mock_client.hget = AsyncMock(return_value=None)

        result = await storage.update_todo("nonexistent", content="Updated")

        assert result is None

    async def test_remove_todo(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """remove_todo pipelines hdel + lrem so they cannot diverge."""
        pipe = mock_client.pipeline.return_value
        pipe.execute = AsyncMock(return_value=[1, 1])  # hdel removed 1, lrem removed 1

        result = await storage.remove_todo("abc12345")

        assert result is True
        # Both ops go through the same pipeline — never a separate round-trip.
        pipe.hdel.assert_called_once()
        pipe.lrem.assert_called_once()
        pipe.execute.assert_awaited_once()
        # And nothing is sent directly on the client.
        mock_client.hdel.assert_not_called()
        mock_client.lrem.assert_not_called()

    async def test_remove_todo_not_found(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """remove_todo returns False when the hash field did not exist."""
        pipe = mock_client.pipeline.return_value
        pipe.execute = AsyncMock(return_value=[0, 0])

        result = await storage.remove_todo("nonexistent")

        assert result is False

    async def test_remove_todo_emits_event(self, mock_client: MagicMock) -> None:
        """remove_todo emits DELETED event when the todo existed."""
        emitter = TodoEventEmitter()
        events: list[tuple[TodoEventType, Todo]] = []

        @emitter.on_deleted
        def callback(event: TodoEvent) -> None:
            events.append((event.event_type, event.todo))

        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        todo = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=todo.model_dump_json().encode())
        pipe = mock_client.pipeline.return_value
        pipe.execute = AsyncMock(return_value=[1, 1])

        await storage.remove_todo("abc12345")

        assert len(events) == 1
        assert events[0][0] == TodoEventType.DELETED


class TestAsyncRedisStorageUpdateFields:
    """Tests for update_todo with different field combinations."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Redis client."""
        client = AsyncMock()
        client.hget = AsyncMock(return_value=None)
        client.hset = AsyncMock(return_value=1)
        return client

    @pytest.fixture
    def storage(self, mock_client: MagicMock) -> AsyncRedisStorage:
        """Create storage with mocked client."""
        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
        )
        storage._initialized = True
        return storage

    async def test_update_status(self, storage: AsyncRedisStorage, mock_client: MagicMock) -> None:
        """Test updating status field."""
        original = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        result = await storage.update_todo("abc12345", status="in_progress")

        assert result is not None
        assert result.status == "in_progress"

    async def test_update_active_form(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test updating active_form field."""
        original = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        result = await storage.update_todo("abc12345", active_form="New form")

        assert result is not None
        assert result.active_form == "New form"

    async def test_update_parent_id(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test updating parent_id field."""
        original = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        result = await storage.update_todo("abc12345", parent_id="parent1")

        assert result is not None
        assert result.parent_id == "parent1"

    async def test_update_depends_on(
        self, storage: AsyncRedisStorage, mock_client: MagicMock
    ) -> None:
        """Test updating depends_on field."""
        original = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        result = await storage.update_todo("abc12345", depends_on=["dep1", "dep2"])

        assert result is not None
        assert result.depends_on == ["dep1", "dep2"]

    async def test_update_emits_status_changed_event(self, mock_client: MagicMock) -> None:
        """Test that updating status emits STATUS_CHANGED event."""
        emitter = TodoEventEmitter()
        status_events: list[TodoEventType] = []

        @emitter.on_status_changed
        def callback(event: TodoEvent) -> None:
            status_events.append(event.event_type)

        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        original = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        await storage.update_todo("abc12345", status="in_progress")

        assert TodoEventType.STATUS_CHANGED in status_events

    async def test_update_emits_completed_event(self, mock_client: MagicMock) -> None:
        """Test that completing a todo emits COMPLETED event."""
        emitter = TodoEventEmitter()
        completed_events: list[TodoEventType] = []

        @emitter.on_completed
        def callback(event: TodoEvent) -> None:
            completed_events.append(event.event_type)

        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        original = Todo(id="abc12345", content="Test", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        await storage.update_todo("abc12345", status="completed")

        assert TodoEventType.COMPLETED in completed_events


class TestAsyncRedisStorageEventEdgeCases:
    """Tests for event emission edge cases."""

    async def test_update_without_status_change_no_status_event(self) -> None:
        """Test that updating without status change doesn't emit STATUS_CHANGED."""
        mock_client = AsyncMock()
        mock_client.hget = AsyncMock()
        mock_client.hset = AsyncMock(return_value=1)

        emitter = TodoEventEmitter()
        status_events: list[TodoEventType] = []
        updated_events: list[TodoEventType] = []

        @emitter.on_status_changed
        def on_status(event: TodoEvent) -> None:
            status_events.append(event.event_type)

        @emitter.on_updated
        def on_updated(event: TodoEvent) -> None:
            updated_events.append(event.event_type)

        storage = AsyncRedisStorage(
            client=mock_client,
            session_id="test-session",
            event_emitter=emitter,
        )
        storage._initialized = True

        original = Todo(id="abc12345", content="Original", status="pending", active_form="Testing")
        mock_client.hget = AsyncMock(return_value=original.model_dump_json().encode())

        await storage.update_todo("abc12345", content="Updated")

        assert TodoEventType.UPDATED in updated_events
        assert len(status_events) == 0


class TestAsyncRedisStorageInitializeEdgeCases:
    """Tests for initialize edge cases."""

    async def test_initialize_when_from_url_returns_none(self) -> None:
        """Test initialize behavior when from_url returns None (edge case)."""
        with patch("redis.asyncio.from_url", return_value=None):
            storage = AsyncRedisStorage(
                url="redis://localhost:6379",
                session_id="test-session",
            )
            await storage.initialize()

            assert not storage._initialized


class TestAsyncRedisStorageClose:
    """Tests for close method edge cases."""

    async def test_close_when_client_is_none(self) -> None:
        """Test close when client was never created."""
        storage = AsyncRedisStorage(
            url="redis://localhost:6379",
            session_id="test-session",
        )
        await storage.close()  # Should not raise


class TestCreateStorageRedis:
    """Tests for create_storage with redis backend."""

    def test_create_redis_storage(self) -> None:
        """Test creating redis storage via factory."""
        storage = create_storage(
            "redis",
            url="redis://localhost:6379",
            session_id="test-session",
        )

        assert isinstance(storage, AsyncRedisStorage)
        assert storage._session_id == "test-session"

    def test_create_redis_requires_session_id(self) -> None:
        """Test that redis backend requires session_id."""
        with pytest.raises(ValueError, match="session_id is required"):
            create_storage(  # pyright: ignore[reportCallIssue]
                "redis",
                url="redis://localhost:6379",
            )

    def test_create_redis_with_event_emitter(self) -> None:
        """Test creating redis storage with event emitter."""
        emitter = TodoEventEmitter()
        storage = create_storage(
            "redis",
            url="redis://localhost:6379",
            session_id="test-session",
            event_emitter=emitter,
        )

        assert storage._event_emitter is emitter

    def test_create_redis_with_custom_key_prefix(self) -> None:
        """Test creating redis storage with custom key prefix."""
        storage = create_storage(
            "redis",
            url="redis://localhost:6379",
            session_id="test-session",
            key_prefix="custom",
        )

        assert storage._key_prefix == "custom"


# Integration tests — only run if REDIS_URL is set
REDIS_URL = os.environ.get("REDIS_TEST_URL", os.environ.get("REDIS_URL"))


@pytest.mark.skipif(REDIS_URL is None, reason="REDIS_TEST_URL/REDIS_URL not set")
class TestAsyncRedisStorageIntegration:
    """Integration tests for AsyncRedisStorage with real Redis."""

    @pytest.fixture
    async def storage(self) -> AsyncGenerator[AsyncRedisStorage, None]:
        """Create and initialize storage for integration tests."""
        assert REDIS_URL is not None
        storage = AsyncRedisStorage(
            url=REDIS_URL,
            session_id=f"test-{os.urandom(4).hex()}",
            key_prefix="todos_test",
        )
        await storage.initialize()
        yield storage
        # Cleanup
        client = storage._ensure_initialized()
        await client.delete(storage._hash_key, storage._order_key)
        await storage.close()

    async def test_full_crud_cycle(self, storage: AsyncRedisStorage) -> None:
        """Test complete CRUD cycle with real Redis."""
        # Create
        todo = Todo(content="Integration test", status="pending", active_form="Testing")
        created = await storage.add_todo(todo)
        assert created.id == todo.id

        # Read
        fetched = await storage.get_todo(todo.id)
        assert fetched is not None
        assert fetched.content == "Integration test"

        # Read all
        all_todos = await storage.get_todos()
        assert len(all_todos) == 1
        assert all_todos[0].id == todo.id

        # Update
        updated = await storage.update_todo(todo.id, status="completed")
        assert updated is not None
        assert updated.status == "completed"

        # Delete
        deleted = await storage.remove_todo(todo.id)
        assert deleted is True

        # Verify deleted
        gone = await storage.get_todo(todo.id)
        assert gone is None

    async def test_set_todos_replaces_all(self, storage: AsyncRedisStorage) -> None:
        """Test that set_todos replaces existing todos."""
        # Add initial todos
        todo1 = Todo(content="Task 1", status="pending", active_form="T1")
        todo2 = Todo(content="Task 2", status="pending", active_form="T2")
        await storage.add_todo(todo1)
        await storage.add_todo(todo2)

        # Replace with new set
        todo3 = Todo(content="Task 3", status="in_progress", active_form="T3")
        await storage.set_todos([todo3])

        all_todos = await storage.get_todos()
        assert len(all_todos) == 1
        assert all_todos[0].content == "Task 3"

    async def test_ordering_preserved(self, storage: AsyncRedisStorage) -> None:
        """Test that insertion order is preserved."""
        todos = [Todo(content=f"Task {i}", status="pending", active_form=f"T{i}") for i in range(5)]
        for todo in todos:
            await storage.add_todo(todo)

        fetched = await storage.get_todos()
        assert len(fetched) == 5
        for i, todo in enumerate(fetched):
            assert todo.content == f"Task {i}"

    async def test_remove_nonexistent(self, storage: AsyncRedisStorage) -> None:
        """Test removing a todo that doesn't exist."""
        result = await storage.remove_todo("nonexistent")
        assert result is False

    async def test_update_nonexistent(self, storage: AsyncRedisStorage) -> None:
        """Test updating a todo that doesn't exist."""
        result = await storage.update_todo("nonexistent", content="Updated")
        assert result is None
