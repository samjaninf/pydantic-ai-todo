"""Tests for optional dependency handling.

Verifies that `asyncpg` is truly optional: the package imports cleanly
without it, and `AsyncPostgresStorage.initialize()` raises a helpful
`ImportError` pointing to the `postgres` extra.
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from unittest.mock import patch

import pytest

from pydantic_ai_todo import AsyncPostgresStorage


@pytest.fixture
def _blocking_import() -> Iterator[None]:
    """Block `import asyncpg` for the duration of the test.

    Monkeypatches `builtins.__import__` so any attempt to import the
    top-level `asyncpg` module raises `ModuleNotFoundError`. Other imports
    are unaffected. Cleanup restores the real importer.
    """
    import builtins

    real_import = builtins.__import__

    def blocking_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "asyncpg":
            raise ModuleNotFoundError("No module named 'asyncpg'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with patch.object(builtins, "__import__", blocking_import):
        yield


class TestAsyncpgOptional:
    """Tests verifying asyncpg is an optional dependency."""

    def test_package_imports_without_asyncpg(self) -> None:
        """`pydantic_ai_todo` imports cleanly when asyncpg is unavailable.

        Uses a subprocess to guarantee a fresh interpreter where asyncpg
        is blocked via `sys.modules['asyncpg'] = None`. An in-process
        reload would leak state across tests that already imported asyncpg.
        """
        code = (
            "import sys\n"
            "sys.modules['asyncpg'] = None\n"
            "import pydantic_ai_todo\n"
            "from pydantic_ai_todo import AsyncPostgresStorage\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Expected clean import without asyncpg, got:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert result.stdout.strip() == "ok"

    async def test_initialize_raises_install_hint_without_asyncpg(self) -> None:
        """`initialize()` raises `ImportError` with the postgres-extra hint."""
        storage = AsyncPostgresStorage(
            connection_string="postgresql://localhost/test",
            session_id="test-session",
        )

        with (
            patch.dict(sys.modules, {"asyncpg": None}),
            pytest.raises(ImportError) as exc_info,
        ):
            await storage.initialize()

        assert "postgres" in str(exc_info.value)
        assert "pydantic-ai-todo[postgres]" in str(exc_info.value)

    async def test_initialize_with_pool_skips_asyncpg_import(self, _blocking_import: None) -> None:
        """A pre-supplied pool does not require asyncpg to be importable.

        `initialize()` only imports asyncpg when it needs to create a pool
        itself. If the caller passes `pool=...`, the import is never reached.
        """
        from unittest.mock import AsyncMock, MagicMock

        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        storage = AsyncPostgresStorage(pool=mock_pool, session_id="test-session")
        await storage.initialize()
        assert storage._initialized
