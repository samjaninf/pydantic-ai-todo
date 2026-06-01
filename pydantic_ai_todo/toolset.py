"""Todo toolset for pydantic-ai agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic_ai.toolsets import FunctionToolset

from pydantic_ai_todo.storage import (
    AsyncTodoStorageProtocol,
    TodoStorage,
    TodoStorageProtocol,
)
from pydantic_ai_todo.types import Todo, TodoItem

TODO_TOOL_DESCRIPTION = """\
Use this tool to create and manage a structured task list for your current session. \
This helps you track progress, organize complex tasks, and demonstrate thoroughness \
to the user. It also helps the user understand your progress on their requests.

## When to Use This Tool

Use this tool proactively in these scenarios:

- **Complex multi-step tasks** — When a task requires 3 or more distinct steps or actions
- **Non-trivial tasks** — Tasks that require careful planning or multiple operations
- **User provides multiple tasks** — When users provide a list of things to be done \
(numbered or comma-separated)
- **After receiving new instructions** — Immediately capture user requirements as tasks
- **When you start working on a task** — Mark it as in_progress BEFORE beginning work
- **After completing a task** — Mark it as completed and add any new follow-up tasks \
discovered during implementation

## When NOT to Use This Tool

Skip using this tool when:
- There is only a single, straightforward task
- The task is trivial and tracking it provides no organizational benefit
- The task can be completed in less than 3 trivial steps
- The task is purely conversational or informational

NOTE: Do not use this tool if there is only one trivial task to do. \
Just do the task directly.

## Task Fields

- **content**: A brief, actionable title in imperative form \
(e.g., "Fix authentication bug in login flow")
- **active_form**: Present continuous form shown as a status label when the task \
is in_progress (e.g., "Fixing authentication bug"). Always provide this when \
creating tasks. The content should be imperative ("Run tests") while active_form \
should be present continuous ("Running tests").
- **status**: pending (not started), in_progress (working now), completed (done)

## Status Workflow

Status progresses: `pending` → `in_progress` → `completed`

- Exactly ONE task should be `in_progress` at any time
- Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
- ONLY mark a task as completed when you have FULLY accomplished it
- If you encounter errors, blockers, or cannot finish, keep the task as in_progress
- When blocked, create a new task describing what needs to be resolved
- Never mark a task as completed if:
  - Tests are failing
  - Implementation is partial
  - You encountered unresolved errors

## Tips

- Create tasks with clear, specific content that describes the outcome
- After completing a task, check for newly unblocked work or start the next available task
- Prefer working on tasks in creation order when multiple tasks are available, \
as earlier tasks often set up context for later ones
"""

TODO_SYSTEM_PROMPT = """\
## Task Management

You have access to todo tools to track your tasks:
- `read_todos` — View current tasks with their IDs and statuses. \
Use this to check what's available before deciding what to work on next.
- `write_todos` — Replace the entire todo list. Use this to initialize or \
restructure the full task list.
- `add_todo` — Add a single new task without replacing existing todos. \
Preferred over write_todos when adding one task.
- `update_todo_status` — Change a task's status by ID. \
Use when starting (→ in_progress) or finishing (→ completed) a task.
- `remove_todo` — Delete a task by ID. Use for tasks that are no longer \
needed or were created in error.

### Task Workflow
1. Break down complex tasks into smaller, actionable steps
2. Mark exactly one task as `in_progress` at a time
3. Mark tasks as `completed` immediately after finishing — don't batch completions
4. After completing a task, call `read_todos` to find the next task to work on
5. Prefer working on tasks in order — earlier tasks often set up context for later ones
6. If a task turns out to be impossible or irrelevant, remove it and explain why
"""

READ_TODO_DESCRIPTION = """\
Read the current todo list state.

## When to Use This Tool

- To see what tasks are available to work on (status: pending, not blocked)
- To check overall progress on the project
- After completing a task, to find the next task to work on
- Before reporting progress to the user

## Output

Returns a summary of each task:
- **id**: Task identifier (use with update_todo_status, remove_todo)
- **content**: Brief description of the task
- **status**: pending, in_progress, or completed

Use read_todos before starting any task to ensure you're working on \
the right thing and to avoid duplicating work.
"""

ADD_TODO_DESCRIPTION = """\
Add a single new todo item to the list without replacing existing todos.

Preferred over write_todos when you only need to add one task.

## Parameters
- **content**: A brief, actionable title in imperative form \
(e.g., "Fix authentication bug in login flow"). Should describe the outcome.
- **active_form**: Present continuous form shown as a status label when \
the task is in_progress (e.g., "Fixing authentication bug"). \
Generate it from the content — "Fix X" → "Fixing X", "Add Y" → "Adding Y".

## Tips
- Always provide active_form — it's displayed to the user while you work on the task
- Content should be imperative ("Run tests") while active_form should be present \
continuous ("Running tests")
- All tasks are created with status `pending`
"""

UPDATE_TODO_STATUS_DESCRIPTION = """\
Update the status of an existing todo by its ID.

## When to Use This Tool

- **Mark tasks as in_progress** when you START working on them (before writing code)
- **Mark tasks as completed** when you have FULLY accomplished the task
- **Reset to pending** if you need to defer a task

## Status Workflow

Status progresses: `pending` → `in_progress` → `completed`

## Important

- ONLY mark a task as completed when you have FULLY accomplished it
- If you encounter errors, blockers, or cannot finish, keep the task as in_progress
- Never mark a task as completed if tests are failing or implementation is partial
- After marking a task as completed, call read_todos to find the next task

## Staleness

Make sure to read the current todo list (read_todos) before updating \
to ensure you're updating the correct task.
"""

REMOVE_TODO_DESCRIPTION = """\
Remove a todo from the list by its ID.

## When to Use This Tool

- When a task is no longer relevant or was created in error
- When a task has been superseded by another approach
- When you determine a task is unnecessary after investigation

Do NOT use this to mark completed tasks — use update_todo_status instead. \
Removing permanently deletes the task.
"""

ADD_SUBTASK_DESCRIPTION = """\
Add a subtask to an existing todo, creating a parent-child relationship.

Use this tool to break down a complex task into smaller, actionable steps. \
The subtask will be linked to its parent via parent_id and displayed in \
hierarchical views.

## Parameters
- **parent_id**: The ID of the parent todo (must exist)
- **content**: Actionable title in imperative form (e.g., "Create login endpoint")
- **active_form**: Present continuous form for status display \
(e.g., "Creating login endpoint")

## Tips
- Break large tasks into 3-7 subtasks for best results
- Subtasks should be independently completable
- Complete subtasks before marking the parent as completed
"""

SET_DEPENDENCY_DESCRIPTION = """\
Set a dependency between two todos.

Use this tool to specify that one task must wait for another to complete \
before it can be started. The dependent task will be automatically marked \
as 'blocked' until its dependency is completed.

## Parameters
- **todo_id**: The task that DEPENDS on another (will be blocked)
- **depends_on_id**: The task that must complete FIRST (the prerequisite)

## Validation
- Cannot create self-dependencies (A depends on A)
- Cannot create circular dependencies (A→B→A)
- Duplicate dependencies are rejected
"""

GET_AVAILABLE_TASKS_DESCRIPTION = """\
Get all tasks that can be worked on now (no blocking dependencies).

Returns only tasks whose dependencies are all completed. \
Blocked and completed tasks are excluded from the list.

Use this to decide what to work on next, especially when tasks have \
complex dependency chains. Prefer working on tasks in order — earlier \
tasks often set up context for later ones.
"""


def create_todo_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    async_storage: AsyncTodoStorageProtocol | None = None,
    id: str | None = None,
    enable_subtasks: bool = False,
    descriptions: dict[str, str] | None = None,
) -> FunctionToolset[Any]:
    """Create a todo toolset for task management.

    This toolset provides read_todos and write_todos tools for AI agents
    to track and manage tasks during a session.

    Args:
        storage: Optional sync storage backend. Defaults to in-memory TodoStorage.
            You can provide a custom storage implementing TodoStorageProtocol.
            Ignored if async_storage is provided.
        async_storage: Optional async storage backend implementing AsyncTodoStorageProtocol.
            When provided, all operations use async methods for true persistence.
        id: Optional unique ID for the toolset.
        enable_subtasks: Enable subtask and dependency features. When True, adds:
            - add_subtask: Create subtasks linked to parent todos
            - set_dependency: Create dependencies between todos
            - get_available_tasks: Get tasks without blocking dependencies
            - Hierarchical view in read_todos
            - 'blocked' status for tasks with incomplete dependencies
        descriptions: Optional dict mapping tool names to custom descriptions.
            Override any tool's description by providing its name as key.
            Tool names: `read_todos`, `write_todos`, `add_todo`,
            `update_todo_status`, `remove_todo`, `add_subtask`,
            `set_dependency`, `get_available_tasks`.

    Returns:
        FunctionToolset compatible with any pydantic-ai agent.

    Example (standalone):
        ```python
        from pydantic_ai import Agent
        from pydantic_ai_todo import create_todo_toolset

        agent = Agent("openai:gpt-4.1", toolsets=[create_todo_toolset()])
        result = await agent.run("Create a todo list for my project")
        ```

    Example (with sync storage):
        ```python
        from pydantic_ai_todo import create_todo_toolset, TodoStorage

        storage = TodoStorage()
        toolset = create_todo_toolset(storage=storage)

        # After agent runs, access todos directly
        print(storage.todos)
        ```

    Example (with async storage):
        ```python
        from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

        storage = AsyncMemoryStorage()
        toolset = create_todo_toolset(async_storage=storage)

        # After agent runs, access todos
        todos = await storage.get_todos()
        ```

    Example (with custom descriptions):
        ```python
        from pydantic_ai_todo import create_todo_toolset

        toolset = create_todo_toolset(
            descriptions={
                "write_todos": "Only use for tasks with 5+ steps.",
            }
        )
        ```
    """
    _descs = descriptions or {}
    # Use async storage if provided, otherwise fall back to sync storage
    if async_storage is not None:
        return _create_async_toolset(
            async_storage,
            id=id,
            enable_subtasks=enable_subtasks,
            descriptions=_descs,
        )
    else:
        return _create_sync_toolset(
            storage,
            id=id,
            enable_subtasks=enable_subtasks,
            descriptions=_descs,
        )


def _create_sync_toolset(
    storage: TodoStorageProtocol | None = None,
    *,
    id: str | None = None,
    enable_subtasks: bool = False,
    descriptions: dict[str, str] | None = None,
) -> FunctionToolset[Any]:
    """Create toolset with sync storage (backwards compatible)."""
    _storage = storage if storage is not None else TodoStorage()
    _descs = descriptions or {}

    toolset: FunctionToolset[Any] = FunctionToolset(id=id)

    def _get_status_icon(status: str, enable_subtasks: bool = False) -> str:
        """Get the icon for a todo status."""
        icons = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }
        if enable_subtasks:
            icons["blocked"] = "[!]"
        return icons.get(status, "[ ]")

    def _get_todo_by_id(todo_id: str) -> Todo | None:
        """Find a todo by its ID."""
        for todo in _storage.todos:
            if todo.id == todo_id:
                return todo
        return None

    def _has_cycle(todo_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        visited: set[str] = set()

        def visit(current_id: str) -> bool:
            if current_id == todo_id:
                return True
            if current_id in visited:
                return False
            visited.add(current_id)
            todo = _get_todo_by_id(current_id)
            if todo:
                for dep_id in todo.depends_on:
                    if visit(dep_id):
                        return True
            return False

        return visit(depends_on_id)

    def _is_blocked(todo: Todo) -> bool:
        """Check if a todo is blocked by incomplete dependencies."""
        for dep_id in todo.depends_on:
            dep = _get_todo_by_id(dep_id)
            if dep and dep.status != "completed":
                return True
        return False

    def _format_hierarchical(todos: list[Todo]) -> str:
        """Format todos as a hierarchical tree."""
        # Build parent->children map
        children_map: dict[str | None, list[Todo]] = {None: []}
        for todo in todos:
            parent = todo.parent_id
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(todo)

        lines = ["Current todos (hierarchical view):"]

        def render_tree(parent_id: str | None, depth: int, counter: list[int]) -> None:
            for todo in children_map.get(parent_id, []):
                counter[0] += 1
                indent = "  " * depth
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{indent}{counter[0]}. {status_icon} [{todo.id}] {todo.content}")
                if todo.depends_on:
                    lines.append(f"{indent}   depends on: {', '.join(todo.depends_on)}")
                if todo.id in children_map:
                    render_tree(todo.id, depth + 1, counter)

        counter = [0]
        render_tree(None, 0, counter)

        return "\n".join(lines)

    if enable_subtasks:
        _default_read = READ_TODO_DESCRIPTION + "\nSet hierarchical=True to view as tree."
        read_description = _descs.get("read_todos", _default_read)

        @toolset.tool_plain(description=read_description)
        async def read_todos(hierarchical: bool = False) -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list.

            Args:
                hierarchical: If True, display todos as a tree with subtasks indented.
            """
            if not _storage.todos:
                return "No todos in the list. Use write_todos to create tasks."

            if hierarchical:
                result = _format_hierarchical(_storage.todos)
            else:
                lines = ["Current todos:"]
                for i, todo in enumerate(_storage.todos, 1):
                    status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                    lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")
                    if todo.parent_id:
                        lines.append(f"   (subtask of: {todo.parent_id})")
                    if todo.depends_on:
                        lines.append(f"   (depends on: {', '.join(todo.depends_on)})")
                result = "\n".join(lines)

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
            for todo in _storage.todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

            summary_parts = [f"{counts['completed']} completed"]
            if counts["blocked"] > 0:
                summary_parts.append(f"{counts['blocked']} blocked")
            summary_parts.append(f"{counts['in_progress']} in progress")
            summary_parts.append(f"{counts['pending']} pending")

            summary = f"\n\nSummary: {', '.join(summary_parts)}"

            if counts["pending"] == 0 and counts["in_progress"] == 0 and counts["completed"] > 0:
                summary += (
                    "\n\nAll tasks are completed. "
                    "Do NOT call read_todos again — respond to the user with a summary instead."
                )

            return result + summary
    else:

        @toolset.tool_plain(description=_descs.get("read_todos", READ_TODO_DESCRIPTION))
        async def read_todos() -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list."""
            if not _storage.todos:
                return "No todos in the list. Use write_todos to create tasks."

            lines = ["Current todos:"]
            for i, todo in enumerate(_storage.todos, 1):
                status_icon = _get_status_icon(todo.status)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
            for todo in _storage.todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

            lines.append("")
            lines.append(
                f"Summary: {counts['completed']} completed, "
                f"{counts['in_progress']} in progress, "
                f"{counts['pending']} pending"
            )

            if counts["pending"] == 0 and counts["in_progress"] == 0 and counts["completed"] > 0:
                lines.append("")
                lines.append(
                    "All tasks are completed. "
                    "Do NOT call read_todos again — respond to the user with a summary instead."
                )

            return "\n".join(lines)

    @toolset.tool_plain(description=_descs.get("write_todos", TODO_TOOL_DESCRIPTION))
    async def write_todos(todos: list[TodoItem]) -> str:
        """Update the todo list with new items.

        Args:
            todos: List of todo items with content, status, and active_form.
        """
        new_todos: list[Todo] = []
        for t in todos:
            todo_kwargs: dict[str, Any] = {
                "content": t.content,
                "status": t.status,
                "active_form": t.active_form,
            }
            if t.id is not None:
                todo_kwargs["id"] = t.id
            if enable_subtasks:
                todo_kwargs["parent_id"] = t.parent_id
                todo_kwargs["depends_on"] = t.depends_on
            new_todos.append(Todo(**todo_kwargs))
        _storage.todos = new_todos

        # Count by status
        counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
        if enable_subtasks:
            counts["blocked"] = 0
        for todo in _storage.todos:
            counts[todo.status] = counts.get(todo.status, 0) + 1

        summary_parts = [f"{counts['completed']} completed"]
        if enable_subtasks and counts.get("blocked", 0) > 0:
            summary_parts.append(f"{counts['blocked']} blocked")
        summary_parts.append(f"{counts['in_progress']} in progress")
        summary_parts.append(f"{counts['pending']} pending")

        return f"Updated {len(todos)} todos: {', '.join(summary_parts)}"

    @toolset.tool_plain(description=_descs.get("add_todo", ADD_TODO_DESCRIPTION))
    async def add_todo(content: str, active_form: str) -> str:
        """Add a new todo item to the list.

        Args:
            content: The task description in imperative form.
            active_form: Present continuous form of the content, e.g. "Fix bug" → "Fixing bug".

        Returns:
            Confirmation message with the new todo's ID.
        """
        new_todo = Todo(content=content, status="pending", active_form=active_form)
        _storage.todos = [*_storage.todos, new_todo]
        return f"Added todo '{content}' with ID: {new_todo.id}"

    @toolset.tool_plain(
        description=_descs.get("update_todo_status", UPDATE_TODO_STATUS_DESCRIPTION),
    )
    async def update_todo_status(todo_id: str, status: str) -> str:
        """Update the status of an existing todo.

        Args:
            todo_id: The ID of the todo to update.
            status: New status (pending, in_progress, completed, or blocked if subtasks enabled).

        Returns:
            Confirmation message or error if not found.
        """
        valid_statuses = {"pending", "in_progress", "completed"}
        if enable_subtasks:
            valid_statuses.add("blocked")
        if status not in valid_statuses:
            return f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"

        for todo in _storage.todos:
            if todo.id == todo_id:
                # Check if trying to start a blocked task
                if enable_subtasks and status == "in_progress" and _is_blocked(todo):
                    return f"Cannot start '{todo.content}' - it has incomplete dependencies"
                todo.status = status  # type: ignore[assignment]
                return f"Updated todo '{todo.content}' status to '{status}'"

        return f"Todo with ID '{todo_id}' not found"

    @toolset.tool_plain(description=_descs.get("remove_todo", REMOVE_TODO_DESCRIPTION))
    async def remove_todo(todo_id: str) -> str:
        """Remove a todo from the list.

        Args:
            todo_id: The ID of the todo to remove.

        Returns:
            Confirmation message or error if not found.
        """
        for i, todo in enumerate(_storage.todos):
            if todo.id == todo_id:
                removed = _storage.todos.pop(i)
                return f"Removed todo '{removed.content}' (ID: {todo_id})"

        return f"Todo with ID '{todo_id}' not found"

    # Add subtask-related tools only when enabled
    if enable_subtasks:

        @toolset.tool_plain(description=_descs.get("add_subtask", ADD_SUBTASK_DESCRIPTION))
        async def add_subtask(parent_id: str, content: str, active_form: str) -> str:
            """Add a subtask to an existing todo.

            Args:
                parent_id: The ID of the parent todo.
                content: The task description in imperative form.
                active_form: Present continuous form of the content,
                    e.g. "Create endpoint" → "Creating endpoint".

            Returns:
                Confirmation message with the new subtask's ID or error.
            """
            parent = _get_todo_by_id(parent_id)
            if not parent:
                return f"Parent todo with ID '{parent_id}' not found"

            new_todo = Todo(
                content=content,
                status="pending",
                active_form=active_form,
                parent_id=parent_id,
            )
            _storage.todos = [*_storage.todos, new_todo]
            return f"Added subtask '{content}' with ID: {new_todo.id} (parent: {parent_id})"

        @toolset.tool_plain(description=_descs.get("set_dependency", SET_DEPENDENCY_DESCRIPTION))
        async def set_dependency(todo_id: str, depends_on_id: str) -> str:
            """Set a dependency between two todos.

            Args:
                todo_id: The ID of the todo that depends on another.
                depends_on_id: The ID of the todo that must be completed first.

            Returns:
                Confirmation message or error if validation fails.
            """
            todo = _get_todo_by_id(todo_id)
            if not todo:
                return f"Todo with ID '{todo_id}' not found"

            dependency = _get_todo_by_id(depends_on_id)
            if not dependency:
                return f"Dependency todo with ID '{depends_on_id}' not found"

            if todo_id == depends_on_id:
                return "A todo cannot depend on itself"

            if _has_cycle(todo_id, depends_on_id):
                return "Cannot add dependency: would create a cycle"

            if depends_on_id in todo.depends_on:
                return "Dependency already exists"

            todo.depends_on = [*todo.depends_on, depends_on_id]

            # Auto-block if dependency is not completed
            if dependency.status != "completed" and todo.status not in ("completed", "blocked"):
                todo.status = "blocked"
                return (
                    f"Added dependency: '{todo.content}' now depends on '{dependency.content}'. "
                    f"Task automatically blocked."
                )

            return f"Added dependency: '{todo.content}' now depends on '{dependency.content}'"

        @toolset.tool_plain(
            description=_descs.get("get_available_tasks", GET_AVAILABLE_TASKS_DESCRIPTION)
        )
        async def get_available_tasks() -> str:
            """Get all tasks that can be worked on now.

            Returns:
                List of tasks without incomplete dependencies.
            """
            available: list[Todo] = []
            for todo in _storage.todos:
                if todo.status == "completed":
                    continue
                if todo.status == "blocked":
                    continue
                if not _is_blocked(todo):
                    available.append(todo)

            if not available:
                return "No available tasks. All tasks are either completed or blocked."

            lines: list[str] = ["Available tasks (no blocking dependencies):"]
            for i, todo in enumerate(available, 1):
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            return "\n".join(lines)

    return toolset


def _create_async_toolset(
    storage: AsyncTodoStorageProtocol,
    *,
    id: str | None = None,
    enable_subtasks: bool = False,
    descriptions: dict[str, str] | None = None,
) -> FunctionToolset[Any]:
    """Create toolset with async storage for true persistence."""
    toolset: FunctionToolset[Any] = FunctionToolset(id=id)
    _descs = descriptions or {}

    def _get_status_icon(status: str, enable_subtasks: bool = False) -> str:
        """Get the icon for a todo status."""
        icons = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }
        if enable_subtasks:
            icons["blocked"] = "[!]"
        return icons.get(status, "[ ]")

    async def _get_todo_by_id(todo_id: str) -> Todo | None:
        """Find a todo by its ID."""
        return await storage.get_todo(todo_id)

    async def _has_cycle(todo_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        todos = await storage.get_todos()
        todos_map = {t.id: t for t in todos}
        visited: set[str] = set()

        def visit(current_id: str) -> bool:
            if current_id == todo_id:
                return True
            if current_id in visited:
                return False
            visited.add(current_id)
            todo = todos_map.get(current_id)
            if todo:
                for dep_id in todo.depends_on:
                    if visit(dep_id):
                        return True
            return False

        return visit(depends_on_id)

    async def _is_blocked(todo: Todo) -> bool:
        """Check if a todo is blocked by incomplete dependencies."""
        for dep_id in todo.depends_on:
            dep = await _get_todo_by_id(dep_id)
            if dep and dep.status != "completed":
                return True
        return False

    def _format_hierarchical(todos: list[Todo]) -> str:
        """Format todos as a hierarchical tree."""
        children_map: dict[str | None, list[Todo]] = {None: []}
        for todo in todos:
            parent = todo.parent_id
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(todo)

        lines = ["Current todos (hierarchical view):"]

        def render_tree(parent_id: str | None, depth: int, counter: list[int]) -> None:
            for todo in children_map.get(parent_id, []):
                counter[0] += 1
                indent = "  " * depth
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{indent}{counter[0]}. {status_icon} [{todo.id}] {todo.content}")
                if todo.depends_on:
                    lines.append(f"{indent}   depends on: {', '.join(todo.depends_on)}")
                if todo.id in children_map:
                    render_tree(todo.id, depth + 1, counter)

        counter = [0]
        render_tree(None, 0, counter)

        return "\n".join(lines)

    if enable_subtasks:
        _default_read = READ_TODO_DESCRIPTION + "\nSet hierarchical=True to view as tree."
        read_description = _descs.get("read_todos", _default_read)

        @toolset.tool_plain(description=read_description)
        async def read_todos(hierarchical: bool = False) -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list.

            Args:
                hierarchical: If True, display todos as a tree with subtasks indented.
            """
            todos = await storage.get_todos()
            if not todos:
                return "No todos in the list. Use write_todos to create tasks."

            if hierarchical:
                result = _format_hierarchical(todos)
            else:
                lines = ["Current todos:"]
                for i, todo in enumerate(todos, 1):
                    status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                    lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")
                    if todo.parent_id:
                        lines.append(f"   (subtask of: {todo.parent_id})")
                    if todo.depends_on:
                        lines.append(f"   (depends on: {', '.join(todo.depends_on)})")
                result = "\n".join(lines)

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
            for todo in todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

            summary_parts = [f"{counts['completed']} completed"]
            if counts["blocked"] > 0:
                summary_parts.append(f"{counts['blocked']} blocked")
            summary_parts.append(f"{counts['in_progress']} in progress")
            summary_parts.append(f"{counts['pending']} pending")

            summary = f"\n\nSummary: {', '.join(summary_parts)}"

            if counts["pending"] == 0 and counts["in_progress"] == 0 and counts["completed"] > 0:
                summary += (
                    "\n\nAll tasks are completed. "
                    "Do NOT call read_todos again — respond to the user with a summary instead."
                )

            return result + summary
    else:

        @toolset.tool_plain(description=_descs.get("read_todos", READ_TODO_DESCRIPTION))
        async def read_todos() -> str:  # pyright: ignore[reportRedeclaration]
            """Read the current todo list."""
            todos = await storage.get_todos()
            if not todos:
                return "No todos in the list. Use write_todos to create tasks."

            lines = ["Current todos:"]
            for i, todo in enumerate(todos, 1):
                status_icon = _get_status_icon(todo.status)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            # Add summary
            counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
            for todo in todos:
                counts[todo.status] = counts.get(todo.status, 0) + 1

            lines.append("")
            lines.append(
                f"Summary: {counts['completed']} completed, "
                f"{counts['in_progress']} in progress, "
                f"{counts['pending']} pending"
            )

            if counts["pending"] == 0 and counts["in_progress"] == 0 and counts["completed"] > 0:
                lines.append("")
                lines.append(
                    "All tasks are completed. "
                    "Do NOT call read_todos again — respond to the user with a summary instead."
                )

            return "\n".join(lines)

    @toolset.tool_plain(description=_descs.get("write_todos", TODO_TOOL_DESCRIPTION))
    async def write_todos(todos: list[TodoItem]) -> str:
        """Update the todo list with new items.

        Args:
            todos: List of todo items with content, status, and active_form.
        """
        new_todos: list[Todo] = []
        for t in todos:
            todo_kwargs: dict[str, Any] = {
                "content": t.content,
                "status": t.status,
                "active_form": t.active_form,
            }
            if t.id is not None:
                todo_kwargs["id"] = t.id
            if enable_subtasks:
                todo_kwargs["parent_id"] = t.parent_id
                todo_kwargs["depends_on"] = t.depends_on
            new_todos.append(Todo(**todo_kwargs))
        await storage.set_todos(new_todos)

        # Count by status
        counts: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0}
        if enable_subtasks:
            counts["blocked"] = 0
        for todo in new_todos:
            counts[todo.status] = counts.get(todo.status, 0) + 1

        summary_parts = [f"{counts['completed']} completed"]
        if enable_subtasks and counts.get("blocked", 0) > 0:
            summary_parts.append(f"{counts['blocked']} blocked")
        summary_parts.append(f"{counts['in_progress']} in progress")
        summary_parts.append(f"{counts['pending']} pending")

        return f"Updated {len(todos)} todos: {', '.join(summary_parts)}"

    @toolset.tool_plain(description=_descs.get("add_todo", ADD_TODO_DESCRIPTION))
    async def add_todo(content: str, active_form: str) -> str:
        """Add a new todo item to the list.

        Args:
            content: The task description in imperative form.
            active_form: Present continuous form of the content, e.g. "Fix bug" → "Fixing bug".

        Returns:
            Confirmation message with the new todo's ID.
        """
        new_todo = Todo(content=content, status="pending", active_form=active_form)
        await storage.add_todo(new_todo)
        return f"Added todo '{content}' with ID: {new_todo.id}"

    @toolset.tool_plain(
        description=_descs.get("update_todo_status", UPDATE_TODO_STATUS_DESCRIPTION),
    )
    async def update_todo_status(
        todo_id: str, status: Literal["pending", "in_progress", "completed", "blocked"]
    ) -> str:
        """Update the status of an existing todo.

        Args:
            todo_id: The ID of the todo to update.
            status: New status (pending, in_progress, completed, or blocked if subtasks enabled).

        Returns:
            Confirmation message or error if not found.
        """
        valid_statuses: set[str] = {"pending", "in_progress", "completed"}
        if enable_subtasks:
            valid_statuses.add("blocked")
        if status not in valid_statuses:
            return f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"

        # Check if trying to start a blocked task
        if enable_subtasks and status == "in_progress":
            todo = await _get_todo_by_id(todo_id)
            if todo and await _is_blocked(todo):
                return f"Cannot start '{todo.content}' - it has incomplete dependencies"

        updated = await storage.update_todo(todo_id, status=status)
        if updated:
            return f"Updated todo '{updated.content}' status to '{status}'"
        return f"Todo with ID '{todo_id}' not found"

    @toolset.tool_plain(description=_descs.get("remove_todo", REMOVE_TODO_DESCRIPTION))
    async def remove_todo(todo_id: str) -> str:
        """Remove a todo from the list.

        Args:
            todo_id: The ID of the todo to remove.

        Returns:
            Confirmation message or error if not found.
        """
        # Get todo content before removing for the message
        todo = await storage.get_todo(todo_id)
        if todo:
            await storage.remove_todo(todo_id)
            return f"Removed todo '{todo.content}' (ID: {todo_id})"
        return f"Todo with ID '{todo_id}' not found"

    # Add subtask-related tools only when enabled
    if enable_subtasks:

        @toolset.tool_plain(description=_descs.get("add_subtask", ADD_SUBTASK_DESCRIPTION))
        async def add_subtask(parent_id: str, content: str, active_form: str) -> str:
            """Add a subtask to an existing todo.

            Args:
                parent_id: The ID of the parent todo.
                content: The task description in imperative form.
                active_form: Present continuous form of the content,
                    e.g. "Create endpoint" → "Creating endpoint".

            Returns:
                Confirmation message with the new subtask's ID or error.
            """
            parent = await _get_todo_by_id(parent_id)
            if not parent:
                return f"Parent todo with ID '{parent_id}' not found"

            new_todo = Todo(
                content=content,
                status="pending",
                active_form=active_form,
                parent_id=parent_id,
            )
            await storage.add_todo(new_todo)
            return f"Added subtask '{content}' with ID: {new_todo.id} (parent: {parent_id})"

        @toolset.tool_plain(description=_descs.get("set_dependency", SET_DEPENDENCY_DESCRIPTION))
        async def set_dependency(todo_id: str, depends_on_id: str) -> str:
            """Set a dependency between two todos.

            Args:
                todo_id: The ID of the todo that depends on another.
                depends_on_id: The ID of the todo that must be completed first.

            Returns:
                Confirmation message or error if validation fails.
            """
            todo = await _get_todo_by_id(todo_id)
            if not todo:
                return f"Todo with ID '{todo_id}' not found"

            dependency = await _get_todo_by_id(depends_on_id)
            if not dependency:
                return f"Dependency todo with ID '{depends_on_id}' not found"

            if todo_id == depends_on_id:
                return "A todo cannot depend on itself"

            if await _has_cycle(todo_id, depends_on_id):
                return "Cannot add dependency: would create a cycle"

            if depends_on_id in todo.depends_on:
                return "Dependency already exists"

            new_depends_on = [*todo.depends_on, depends_on_id]

            # Auto-block if dependency is not completed
            original_status = todo.status
            new_status = todo.status
            if dependency.status != "completed" and todo.status not in ("completed", "blocked"):
                new_status = "blocked"  # type: ignore[assignment]

            await storage.update_todo(todo_id, depends_on=new_depends_on, status=new_status)

            if new_status == "blocked" and original_status != "blocked":
                return (
                    f"Added dependency: '{todo.content}' now depends on '{dependency.content}'. "
                    f"Task automatically blocked."
                )

            return f"Added dependency: '{todo.content}' now depends on '{dependency.content}'"

        @toolset.tool_plain(
            description=_descs.get("get_available_tasks", GET_AVAILABLE_TASKS_DESCRIPTION)
        )
        async def get_available_tasks() -> str:
            """Get all tasks that can be worked on now.

            Returns:
                List of tasks without incomplete dependencies.
            """
            todos = await storage.get_todos()
            available: list[Todo] = []
            for todo in todos:
                if todo.status == "completed":
                    continue
                if todo.status == "blocked":
                    continue
                if not await _is_blocked(todo):
                    available.append(todo)

            if not available:
                return "No available tasks. All tasks are either completed or blocked."

            lines: list[str] = ["Available tasks (no blocking dependencies):"]
            for i, todo in enumerate(available, 1):
                status_icon = _get_status_icon(todo.status, enable_subtasks=True)
                lines.append(f"{i}. {status_icon} [{todo.id}] {todo.content}")

            return "\n".join(lines)

    return toolset


def get_todo_system_prompt(storage: TodoStorageProtocol | None = None) -> str:
    """Generate dynamic system prompt section for todos.

    Args:
        storage: Optional sync storage to read current todos from.

    Returns:
        System prompt section with current todos, or base prompt if no todos.

    Note:
        For async storage, use get_todo_system_prompt_async instead.
    """
    if storage is None or not storage.todos:
        return TODO_SYSTEM_PROMPT

    lines = [TODO_SYSTEM_PROMPT, "", "## Current Todos"]

    for todo in storage.todos:
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
            "blocked": "[!]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} [{todo.id}] {todo.content}")

    return "\n".join(lines)


async def get_todo_system_prompt_async(
    storage: AsyncTodoStorageProtocol | None = None,
) -> str:
    """Generate dynamic system prompt section for todos (async version).

    Args:
        storage: Optional async storage to read current todos from.

    Returns:
        System prompt section with current todos, or base prompt if no todos.
    """
    if storage is None:
        return TODO_SYSTEM_PROMPT

    todos = await storage.get_todos()
    if not todos:
        return TODO_SYSTEM_PROMPT

    lines = [TODO_SYSTEM_PROMPT, "", "## Current Todos"]

    for todo in todos:
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
            "blocked": "[!]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} [{todo.id}] {todo.content}")

    return "\n".join(lines)
