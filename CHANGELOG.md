# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.5] - unreleased

### Added

- **Batch status updates (`update_todo_statuses`).** New tool that applies several `{todo_id, status}` transitions in a single call, so an agent can express one logical workflow step — e.g. mark the current task `completed` and the next task `in_progress` — without chaining separate `update_todo_status` calls (and the extra `read_todos` round-trips they encourage). The batch is **all-or-nothing**: it is fully validated first (unknown IDs, invalid statuses, and starting a task with incomplete dependencies all abort the batch with no changes applied), then applied, returning a compact summary of the transitions. Available on both sync and async storage and honours `enable_subtasks` (the `blocked` status and dependency checks). Adds the `TodoStatusUpdate` input model and the `UPDATE_TODO_STATUSES_DESCRIPTION` constant to the public API. Resolves [#32](https://github.com/vstorm-co/pydantic-ai-todo/issues/32).

### Changed

- **`TodoItem.status` now defaults to `"pending"`.** Creating a plan with `write_todos` no longer requires a `status` on every item — a new task is `pending` by definition, so the field can be omitted. This removes the extra validation round-trip that agents previously paid when they left `status` out and had to retry. The field description nudges agents to set `status` explicitly when *restructuring* an existing list (so in-progress/completed tasks are preserved). Resolves [#30](https://github.com/vstorm-co/pydantic-ai-todo/issues/30).

## [0.2.4] - 2026-06-01

### Changed

- **Docstring hygiene (internal; no behavior change).** Converted reStructuredText-style double-backtick inline code in docstrings and comments to single-backtick Markdown (25 occurrences), so it renders correctly under the mkdocstrings Markdown handler. No function-local imports needed hoisting (the package already keeps its imports at module top).

### Documentation

- **Documentation accuracy pass.** Corrected the installation guide (PostgreSQL `asyncpg` and Redis `redis` are core dependencies, not optional extras), documented the previously-undocumented `AsyncRedisStorage` backend (API reference, storage overview, and connection-lifecycle notes), and fixed the misleading "tasks automatically unblock" claim — a `blocked` status is never auto-cleared; `get_available_tasks` computes availability live and excludes blocked tasks. Added an explicit note that task events fire only from async storage backends (the sync `TodoStorage`/toolset path emits nothing), fixed the `read_todos` sample output to match the real numbered/icon format, replaced hand-copied (and drifted) `TodoItem`/protocol snippets with mkdocstrings renders, documented the exported `*_DESCRIPTION`/`TODO_SYSTEM_PROMPT` constants, and noted the static-prompt behavior when only `async_storage` is provided. `mkdocs build --strict` now passes with zero warnings.

## [0.2.3] - 2026-05-24

### Infrastructure

Pure CI / dependency-bot housekeeping — no source-code changes, no behaviour change since 0.2.2. Consolidates the open Renovate auto-PRs and the rate-limited items from the [Dependency Dashboard #24](https://github.com/vstorm-co/pydantic-ai-todo/issues/24) into a single release so downstream consumers see one bump instead of four.

- **CI: bump `actions/checkout` to `v6`** across `ci.yml` (×3), `docs.yml`, `publish.yml` ([#23](https://github.com/vstorm-co/pydantic-ai-todo/pull/23), Renovate auto-PR — folded in here).
- **CI: bump `docs.yml` Python to `3.14`** ([#22](https://github.com/vstorm-co/pydantic-ai-todo/pull/22), Renovate auto-PR — folded in here).
- **CI: bump `astral-sh/setup-uv` to `v8.1.0`** across `ci.yml` (×3) and `publish.yml` — from Dashboard #24. Pinned to the specific patch because `astral-sh/setup-uv` does not maintain a rolling `v8` tag (only `v8.0.0` / `v8.1.0`; `v7` and earlier do have rolling majors).
- **CI: bump `actions/setup-python` to `v6`** in `docs.yml` — from Dashboard #24; `v6` has a rolling tag so plain `@v6` is used.

The `ci.yml` test matrix (`["3.10", "3.13"]` and `["3.10", "3.11", "3.12", "3.13"]`) is unchanged in this release.

## [0.2.2] - 2026-05-24

### Added

- **`AsyncRedisStorage` — third storage backend, Redis-based** ([#18](https://github.com/vstorm-co/pydantic-ai-todo/pull/18) by [@shamalgithub](https://github.com/shamalgithub)). Stores each session's todos in a Redis Hash (one field per todo, JSON-serialized) with a companion List for insertion order. Supports either URL-based construction (`AsyncRedisStorage(url="redis://...", session_id=...)`) or injection of an existing `redis.asyncio.Redis` client (`AsyncRedisStorage(client=..., session_id=...)`). Session-scoped keys give multi-tenancy out of the box, the event emitter integration mirrors the other backends (CREATED, UPDATED, STATUS_CHANGED, COMPLETED, DELETED), and `create_storage("redis", ...)` plus a new overload land the factory shape. Adds `redis>=7.4.0` as a dependency and exports `AsyncRedisStorage` from the package root.

### Fixed

- **`AsyncRedisStorage.remove_todo` is now atomic.** The previous two-round-trip implementation (`hdel` then `lrem`) could leave the order list pointing at a deleted hash entry if the connection dropped between the two; both ops now go through a single pipeline so they cannot diverge.
- **`AsyncRedisStorage` is Redis Cluster-safe.** `_hash_key` and `_order_key` now share a `{session_id}` hash-tag (`todos:{user-123}` / `todos:{user-123}:order`) so both keys route to the same Cluster slot. Without it the multi-key pipelines in `set_todos` / `add_todo` / `remove_todo` would fail with `CROSSSLOT` under clustered deployments. No-op on single-node Redis.
- **`AsyncRedisStorage.initialize()` is now idempotent.** A second call is a no-op instead of issuing another `PING`.
- **`.gitignore` cleanup** — fixed an "Ingore" typo, trimmed trailing whitespace, and added the missing final newline introduced in #18.

## [0.2.1] - 2026-03-31

### Changed

- Bump minimum `pydantic-ai-slim` to `>=1.74.0` for compatibility with async `get_instructions` on toolsets

## [0.2.0] - 2026-03-26

### Added

- **`TodoCapability`** — new pydantic-ai [capability](https://ai.pydantic.dev/capabilities/) that bundles todo tools + dynamic system prompt into a single plug-and-play unit. This is now the recommended way to add todo support:
  ```python
  from pydantic_ai import Agent
  from pydantic_ai_todo import TodoCapability

  agent = Agent("openai:gpt-4.1", capabilities=[TodoCapability()])
  ```
  - Registers all tools automatically (`read_todos`, `write_todos`, `add_todo`, `update_todo_status`, `remove_todo`, and subtask tools when enabled)
  - Injects dynamic system prompt showing current todo state — no manual `get_todo_system_prompt()` wiring needed
  - Supports AgentSpec YAML serialization (`Agent.from_file("agent.yaml")`)
  - Accepts all `create_todo_toolset()` params: `storage`, `async_storage`, `enable_subtasks`, `descriptions`

### Fixed

- **`read_todos` loop when all tasks completed** — when all tasks are done, `read_todos` now returns an explicit "All tasks are completed. Do NOT call read_todos again" message. Previously the model would keep calling `read_todos` in a loop because the response didn't signal that no further action was needed. ([#14](https://github.com/vstorm-co/pydantic-ai-todo/issues/14), reported by [@ilayu-blip](https://github.com/ilayu-blip))

### Changed

- **Documentation rewritten for capabilities-first approach** — README, quick start, examples, and concept pages now lead with `TodoCapability`. The toolset API (`create_todo_toolset()`) is documented as a lower-level alternative for users who need more control.

## [0.1.10] - 2026-02-26

### Added

- **Custom tool descriptions** — `create_todo_toolset()` now accepts `descriptions: dict[str, str] | None` parameter to override any tool's built-in description. Enables customizing agent behavior without forking the library ([#11](https://github.com/vstorm-co/pydantic-ai-todo/issues/11))

## [0.1.9] - 2026-02-24

### Changed

- **Enriched all tool description constants** — All 9 description constants (`TODO_TOOL_DESCRIPTION`, `TODO_SYSTEM_PROMPT`, `READ_TODO_DESCRIPTION`, `ADD_TODO_DESCRIPTION`, `UPDATE_TODO_STATUS_DESCRIPTION`, `REMOVE_TODO_DESCRIPTION`, `ADD_SUBTASK_DESCRIPTION`, `SET_DEPENDENCY_DESCRIPTION`, `GET_AVAILABLE_TASKS_DESCRIPTION`) rewritten with detailed "When to Use" / "When NOT to Use" sections, status workflow documentation, parameter explanations, and practical tips. Follows the Claude Code / deepagents pattern of putting comprehensive guidance directly in tool descriptions.
- **Expanded `TODO_SYSTEM_PROMPT`** — Tool listing now includes brief usage guidance for each tool. Added "Task Workflow" section with numbered steps.

## [0.1.8] - 2026-02-16

### Fixed

- **System prompt now includes todo IDs**: `get_todo_system_prompt()` and `get_todo_system_prompt_async()` now render todos as `- [x] [abc123ef] Task content` instead of `- [x] Task content`. Previously, agents could see their todos in the system prompt but had no way to know the IDs needed by `update_todo_status` and `remove_todo` without first calling `read_todos`. ([#9](https://github.com/vstorm-co/pydantic-ai-todo/pull/9) by [@pedro-at-noxus](https://github.com/pedro-at-noxus))

- **Improved `active_form` parameter descriptions**: Added concrete transformation examples (e.g., "Fix the login bug" → "Fixing the login bug") to `add_todo` and `add_subtask` tool descriptions and docstrings. Some models previously asked the user for this value instead of generating it from the task content. ([#9](https://github.com/vstorm-co/pydantic-ai-todo/pull/9) by [@pedro-at-noxus](https://github.com/pedro-at-noxus))

## [0.1.7] - 2026-02-15

### Added

- **Event Subscription Patterns**: New documentation section covering:
  - Single event, multiple subscribers
  - Single subscriber, multiple events via stacked decorators
  - Conditional event handling
  - Dynamic registration/unregistration at runtime
  - Class-based event handlers for organizing related logic
- **Cycle Detection Deep Dive**: Expanded documentation explaining:
  - DFS algorithm for cycle detection
  - Self-dependency, direct cycle, and transitive cycle cases
  - Diamond dependencies (allowed)
  - Practical examples for each case
- **Multi-Tenancy Example**: New guide for per-user task isolation in web applications
- **Migration Guide**: New guide for transitioning from memory to PostgreSQL storage

### Changed

- **Navigation**: Updated docs nav to include multi-tenancy and migration guide

## [0.1.6] - 2026-02-03

### Changed

- **Lightweight dependency**: Replaced `pydantic-ai` with `pydantic-ai-slim` to reduce install footprint — pulls in only the core modules needed by the toolset
- **Removed CLI**: Dropped the CLI entry point to keep the package focused as a library-only toolset

## [0.1.5] - 2025-01-23

### Added

- **Missing Exports**: Added `UPDATE_TODO_STATUS_DESCRIPTION` and `REMOVE_TODO_DESCRIPTION` constants to public API

### Fixed

- **Documentation**: Fixed `create_todo_toolset` signature - added missing `id` parameter and corrected return type to `FunctionToolset[Any]`

## [0.1.4] - 2025-01-22

### Added

- **Full Documentation Site**: MkDocs Material documentation matching pydantic-deep style
  - Concepts: Toolset, Storage, Types
  - Advanced: Subtasks & Dependencies, Event System
  - Examples: Basic Usage, Async Storage, PostgreSQL, Subtasks, Events
  - API Reference: Auto-generated from docstrings
- **GitHub Actions Workflow**: Auto-deploy docs to GitHub Pages on push to main
- **Custom Styling**: Pink theme with Inter/JetBrains Mono fonts

### Changed

- **README**: Complete rewrite with centered header, badges, Use Cases table, and vstorm-co branding

### Fixed

- Documentation accuracy: Added missing "blocked" status to all status lists
- Documentation accuracy: Fixed `previous_state` type from `str | None` to `Todo | None`

## [0.1.3] - 2025-01-18

### Added

- **Todo IDs**: Auto-generated 8-char hex IDs for todos (`uuid4().hex[:8]`)
- **Atomic CRUD Operations**:
  - `add_todo(content, active_form)` - Add single task
  - `update_todo_status(todo_id, status)` - Update task status by ID
  - `remove_todo(todo_id)` - Delete task by ID
- **Async Storage Protocol**:
  - `AsyncTodoStorageProtocol` - Interface for async storage backends
  - `AsyncMemoryStorage` - In-memory async implementation
  - `create_storage(backend)` - Factory function for storage backends
  - `get_todo_system_prompt_async()` - Async version of system prompt generator
- **Task Hierarchy** (opt-in via `enable_subtasks=True`):
  - `parent_id` and `depends_on` fields on Todo model
  - `add_subtask(parent_id, content, active_form)` - Create child tasks
  - `set_dependency(todo_id, depends_on_id)` - Link tasks with cycle detection
  - `get_available_tasks()` - List tasks ready to work on
  - `blocked` status for tasks with incomplete dependencies
  - Hierarchical tree view in `read_todos`
- **Event System**:
  - `TodoEventType` enum: CREATED, UPDATED, STATUS_CHANGED, DELETED, COMPLETED
  - `TodoEvent` model with event_type, todo, timestamp, previous_state
  - `TodoEventEmitter` class with `on/off/emit` methods
  - Convenience decorators: `on_created`, `on_completed`, `on_status_changed`, `on_updated`, `on_deleted`
  - Event integration with `AsyncMemoryStorage` and `AsyncPostgresStorage`
- **PostgreSQL Storage Backend**:
  - `AsyncPostgresStorage` - Full PostgreSQL implementation
  - Session-based multi-tenancy via `session_id` parameter
  - Support for connection string or existing `asyncpg.Pool`
  - Auto table creation on `initialize()`
  - `asyncpg>=0.29.0` as required dependency

### Changed

- `read_todos` output now includes todo IDs: `"1. [ ] [id] content"`
- `TODO_SYSTEM_PROMPT` updated to document all available tools
- `create_storage()` now supports `"postgres"` backend

## [0.1.2] - 2025-01-17

### Changed

- `__version__` now dynamically reads from package metadata (pyproject.toml) via `importlib.metadata`
