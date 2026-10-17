# /project-status

Produce a fast, structured status summary of the project by scanning the frontmatter-based docs under `docs/`. Use this whenever the agent needs to load current state without reading every file.

## When to use

- At the start of any session after reading `Agent.md` and `AGENTS.md`.
- Before planning the next task.
- When the user asks "What is the status?" or "What should I work on next?"
- When returning from a break or context window reset.

## Invocation inputs (optional)

The user may pass filters after `/project-status`:

- `/project-status feature FEAT-001` — Show status scoped to one feature.
- `/project-status blocked` — Show only blocked todos.
- `/project-status active` — Show active sprint and in-progress work.
- `/project-status todo` — Show pending todos by priority.

If no filter is given, provide the full summary.

## Steps

### 1. Read the project manifest/index

Read:

- `Agent.md`
- `docs/index.md`
- `docs/progress.md`

### 2. Scan doc directories for frontmatter

For each directory, discover files and extract YAML frontmatter:

- `docs/features/*.md` → `id`, `title`, `status`, `priority`, `tags`
- `docs/stories/*.md` → `id`, `title`, `feature`, `status`, `priority`, `story_points`
- `docs/todos/*.md` → `id`, `title`, `feature`, `story`, `status`, `priority`, `dependencies`, `blocks`
- `docs/decisions/*.md` → `id`, `title`, `status`, `date`, `tags`
- `docs/sprints/*.md` → `id`, `title`, `status`, `start_date`, `end_date`, `goal`

Prefer `read` for small directories or search tools for large ones.

### 3. Build status summary

Return a concise markdown report with:

#### Header

- Project phase from `docs/progress.md`.
- Current focus from `docs/progress.md`.
- Active sprint name and goal (if any sprint has `status: active`).

#### Counters

| Type | Total | Todo | In Progress | Done | Blocked | Proposed |
| ---- | ----- | ---- | ----------- | ---- | ------- | -------- |
| Features | 0 | - | - | 0 | - | 0 |
| Stories | 0 | - | 0 | 0 | - | 0 |
| Todos | 0 | 0 | 0 | 0 | 0 | - |
| Decisions | 0 | - | - | 0 | - | 0 |

#### Active work

List todos with `status: in_progress`, ordered by priority, showing:
- ID and title
- Linked story and feature
- Dependencies / blockers

#### Next up

List top 3 pending todos by priority and dependency readiness (no unmet dependencies).

#### Blocked

List todos with `status: blocked` and their blocker reason if noted in the file body.

#### Recently completed

List todos with `status: done`, sorted by `updated` date descending, limit 5.

#### Open decisions

List decisions with `status: proposed` that need resolution.

### 4. Apply filters

If the user provided a filter, narrow the output:

- `feature FEAT-XXX` → Only todos/stories/decisions where `feature` matches.
- `blocked` → Only blocked todos and active blockers.
- `active` → Active sprint + in-progress todos.
- `todo` → Pending todos grouped by priority.

### 5. Suggest next action

End the summary with one concrete recommendation, e.g.:

> Next: Pick up `TODO-042` (no dependencies, high priority) or resolve the blocked `TODO-038`.

## Performance rules

- Do not read every file body unless necessary. Frontmatter scanning is enough for the summary.
- If a directory has more than 50 files, stop listing individual items and instead provide counts + top items.
- Cache the result in memory for the current turn if multiple filters are invoked.

## Output format

```markdown
# Project Status

**Phase:** ...
**Focus:** ...
**Active sprint:** ...

## Counters
...

## Active work
...

## Next up
...

## Blocked
...

## Recently completed
...

## Open decisions
...

## Recommendation
...
```
