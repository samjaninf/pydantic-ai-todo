# Task Hierarchy (Subtasks & Dependencies)

Enable complex task management with parent-child relationships and dependencies.

## Enabling Subtasks

Subtask tools are opt-in:

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()

# Without subtasks (default)
toolset = create_todo_toolset(async_storage=storage)

# With subtasks enabled
toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])
result = await agent.run("Break down the API implementation into subtasks")
```

## Additional Tools

When `enable_subtasks=True`, these tools are added:

| Tool | Description |
|------|-------------|
| `add_subtask` | Create a child task under a parent |
| `set_dependency` | Link tasks with dependency relationship |
| `get_available_tasks` | List tasks ready to work on |

## Todo Model Extensions

With subtasks enabled, todos have additional fields:

```python
class Todo(BaseModel):
    id: str                    # Auto-generated 8-char hex
    content: str               # Task description
    status: Literal["pending", "in_progress", "completed", "blocked"]
    active_form: str           # Present continuous form
    parent_id: str | None      # Parent task ID (for subtasks)
    depends_on: list[str]      # List of dependency task IDs
```

## Creating Subtasks

### Via Tool (Agent)

The agent can use `add_subtask`:

```
Agent: I'll break this down into subtasks.
[calls add_subtask(parent_id="abc12345", content="Design database schema", active_form="Designing schema")]
```

### Via Storage (Programmatic)

```python
from pydantic_ai_todo import Todo, AsyncMemoryStorage

storage = AsyncMemoryStorage()

parent = Todo(content="Build API", status="pending", active_form="Building API")
await storage.add_todo(parent)

child = Todo(
    content="Design schema",
    status="pending",
    active_form="Designing schema",
    parent_id=parent.id
)
await storage.add_todo(child)
```

## Dependencies

### Setting Dependencies

```python
# Via tool (agent)
# set_dependency(todo_id="task2", depends_on_id="task1")

# Task 2 now depends on Task 1
# Task 2 is automatically blocked if Task 1 is not completed
```

### Automatic Blocking

When you set a dependency on an incomplete task:
- The dependent task's status becomes `"blocked"`
- The task shows as blocked in `read_todos`

```python
# Task 1: pending
# Task 2: depends on Task 1 -> automatically blocked
```

### Cycle Detection

Circular dependencies are prevented. The library uses a **depth-first search (DFS)** algorithm
to detect cycles before adding any new dependency.

#### How It Works

When you call `set_dependency(todo_id="X", depends_on_id="Y")`, the library checks whether
adding this edge would create a cycle in the dependency graph. It does so by starting at
node `Y` and walking the existing `depends_on` edges. If it ever reaches `X`, a cycle would
be formed and the dependency is rejected.

The algorithm in pseudocode:

```
function has_cycle(todo_id, depends_on_id):
    visited = {}
    function visit(current_id):
        if current_id == todo_id:
            return True          # Found a path back to the origin -> cycle
        if current_id in visited:
            return False          # Already explored, no cycle here
        visited.add(current_id)
        for each dep_id in current_id.depends_on:
            if visit(dep_id):
                return True
        return False
    return visit(depends_on_id)
```

The actual implementation lives in the `_has_cycle` function inside
[`pydantic_ai_todo/toolset.py`](https://github.com/vstorm-co/pydantic-ai-todo):

```python
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
```

#### What Happens When a Cycle Is Detected

The `set_dependency` tool returns an error message and the dependency is **not** added:

```
"Cannot add dependency: would create a cycle"
```

The task graph remains unchanged. Three specific cases are checked:

| Case | Result |
|------|--------|
| Self-dependency (`A -> A`) | `"A todo cannot depend on itself"` |
| Direct cycle (`A -> B -> A`) | `"Cannot add dependency: would create a cycle"` |
| Transitive cycle (`A -> B -> C -> A`) | `"Cannot add dependency: would create a cycle"` |

#### Examples

**Self-dependency** -- rejected immediately:

```
set_dependency(todo_id="A", depends_on_id="A")
# Result: "A todo cannot depend on itself"
```

**Direct cycle** -- two tasks depending on each other:

```
set_dependency(todo_id="A", depends_on_id="B")  # OK: A depends on B
set_dependency(todo_id="B", depends_on_id="A")  # ERROR: Would create B -> A -> B cycle
```

**Transitive cycle** -- longer chain:

```
set_dependency(todo_id="B", depends_on_id="A")  # OK: B depends on A
set_dependency(todo_id="C", depends_on_id="B")  # OK: C depends on B
set_dependency(todo_id="A", depends_on_id="C")  # ERROR: A -> C -> B -> A cycle
```

**Diamond dependencies** -- allowed (no cycle):

```
     Task A
    /      \
Task B    Task C
    \      /
     Task D
```

```python
# D depends on both B and C -- this is fine
set_dependency(todo_id="D", depends_on_id="B")  # OK
set_dependency(todo_id="D", depends_on_id="C")  # OK

# B and C both depend on A -- also fine
set_dependency(todo_id="B", depends_on_id="A")  # OK
set_dependency(todo_id="C", depends_on_id="A")  # OK
```

!!! tip
    Diamond dependencies are the most common pattern for tasks that converge.
    For example, "Deploy" depends on both "Build Frontend" and "Build Backend",
    which both depend on "Design Architecture".

## Hierarchical View

`read_todos` supports hierarchical display:

```python
# Flat view (default)
todos = await read_todos()
# 1. [ ] [abc123] Build API
# 2. [ ] [def456] Design schema
# 3. [ ] [ghi789] Implement endpoints

# Hierarchical view
todos = await read_todos(hierarchical=True)
# 1. [ ] [abc123] Build API
#    1.1. [ ] [def456] Design schema
#    1.2. [ ] [ghi789] Implement endpoints
```

## Available Tasks

Get tasks that can be worked on immediately:

```python
# get_available_tasks returns a task only when BOTH hold:
# - its stored status is NOT "completed" and NOT "blocked"
# - none of its `depends_on` tasks are still incomplete
#   (checked live by _is_blocked at call time, not from stored status)
available = await get_available_tasks()
```

Availability is computed **live** on each call. A task is included only if its
stored status is neither `completed` nor `blocked`, *and* a fresh dependency
check (`_is_blocked`) confirms all of its `depends_on` prerequisites are
`completed`. Note that the stored `blocked` status is never recomputed by this
tool — a task left with status `blocked` is always excluded, even if its
dependencies have since completed.

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task not started |
| `in_progress` | Task being worked on |
| `completed` | Task finished |
| `blocked` | Task has incomplete dependencies |

## Practical Example

```python
from pydantic_ai import Agent
from pydantic_ai_todo import create_todo_toolset, AsyncMemoryStorage

storage = AsyncMemoryStorage()
toolset = create_todo_toolset(async_storage=storage, enable_subtasks=True)

agent = Agent("openai:gpt-4.1", toolsets=[toolset])

# Agent creates tasks with hierarchy
result = await agent.run("Build a REST API with user authentication. Break it down into subtasks with proper dependencies.")

# Agent might create:
# 1. [ ] Build REST API
#    1.1. [ ] Design database schema
#    1.2. [blocked] Implement models (depends on 1.1)
#    1.3. [blocked] Create endpoints (depends on 1.2)
# 2. [ ] Add authentication
#    2.1. [ ] Choose auth method
#    2.2. [blocked] Implement auth (depends on 2.1, 1.3)

# Check what's available to work on
todos = await storage.get_todos()
available = [t for t in todos if t.status in ("pending", "in_progress")]
# - Design database schema
# - Choose auth method
```

## Best Practices

1. **Use subtasks for breakdown** - Let the agent break complex tasks into subtasks
2. **Set dependencies explicitly** - Don't assume order from list position
3. **Check available tasks** - Use `get_available_tasks` to find what can be done next
4. **Handle blocked status** - The stored `blocked` status does **not** clear itself. When a task is given a dependency via `set_dependency`, it is marked `blocked` and stays that way until something explicitly updates it (e.g. `update_todo_status`). What changes automatically is *availability*: once the prerequisite is `completed`, `get_available_tasks` will surface the task again only if its stored status was moved off `blocked` (for example back to `pending`).
