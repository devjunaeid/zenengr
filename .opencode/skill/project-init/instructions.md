# /project-init

Initialize this agentic development scaffold for a new or existing project. This skill discovers the tech stack, updates the documentation templates, and suggests the right MCP servers and opencode skills/commands.

## When to use

Run `/project-init` when:
- A developer first clones this template for a new project.
- An existing codebase is being adopted into this scaffold.
- The tech stack or project direction has changed significantly and needs to be re-documented.

## Steps

### 1. Read existing scaffold context

Read the following files before doing anything else:

1. `Agent.md`
2. `AGENTS.md`
3. `docs/index.md`
4. `docs/stack-discovery.md`
5. `docs/progress.md`
6. `docs/frontend-standard.md`
7. `docs/backend-standard.md`
8. `docs/ui-ux-spec.md`
9. `docs/mcp-setup.md`
10. `docs/features/FEAT-001.md` (template)
11. `docs/stories/US-001.md` (template)
12. `docs/todos/TODO-001.md` (template)
13. `opencode.json`
14. `.opencode/skill/` and `.opencode/command/`

### 2. Detect whether a codebase already exists

Check for common project files:

- `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb` → Node.js / frontend / full-stack
- `pyproject.toml`, `requirements.txt`, `Pipfile` → Python
- `go.mod` → Go
- `Cargo.toml` → Rust
- `pom.xml`, `build.gradle` → Java
- `composer.json` → PHP
- `Gemfile` → Ruby
- `Dockerfile`, `docker-compose.yml` → Docker usage
- `.github/workflows/` → CI/CD
- `src/`, `app/`, `lib/`, `server/`, `api/`, etc. → Source layout

If files exist, capture:
- Project name and scripts from manifests
- Frontend and backend dependencies
- Database / ORM hints
- Existing test commands
- Lint / format tools

### 3. Capture missing info from the user

Use the question tool to fill `docs/stack-discovery.md`. Prioritize user input, but pre-fill answers from the detected codebase.

Ask these questions in one multi-question prompt:

1. **Project basics:** project name, description, current phase.
2. **Frontend stack:** framework, language, styling, component library, state, data fetching, testing, package manager.
3. **Backend stack:** runtime/language, framework, database, ORM, auth, API style, testing.
4. **Product:** top 3-5 must-have features and anything explicitly out of scope.
5. **Tooling:** deployment target, CI/CD, whether they want Git, database, browser MCPs.

If an existing codebase was detected, present the detected values as pre-selected defaults so the user can confirm or correct them.

### 4. Update documentation

With the confirmed stack and product info, update these files:

#### `docs/stack-discovery.md`
- Fill out all sections with the user's answers.
- Add an entry to the decisions log.

#### `docs/index.md`
- Update the project dashboard to reflect the new structure.

#### `docs/features/`
- Create one file per top-level feature using `docs/features/FEAT-001.md` as the template.
- IDs: FEAT-001, FEAT-002, etc.
- Include title, status `proposed`, priority, goal, acceptance criteria, and out-of-scope notes.

#### `docs/stories/`
- Derive one story file per acceptance criterion group from the features.
- IDs: US-001, US-002, etc.
- Frontmatter must link back to the parent feature via `feature: FEAT-NNN`.

#### `docs/todos/`
- Break each story into concrete task files using `docs/todos/TODO-001.md` as the template.
- IDs: TODO-001, TODO-002, etc.
- Frontmatter must link to `story` and `feature`.
- Set status to `todo` for all new items.

#### `docs/progress.md`
- Set project phase to "Setup / Design".
- Record that `/project-init` completed and stack was documented.

#### `docs/frontend-standard.md` and `docs/backend-standard.md`
- Fill in the confirmed stack and project structure.
- Capture discovered commands from `package.json` scripts or equivalent.
- If commands are unknown, leave placeholders clearly marked.

#### `docs/ui-ux-spec.md`
- Set framework-agnostic defaults if no design exists yet.
- Note that design details should be added before frontend implementation.

#### `docs/mcp-setup.md`
- Mark required/optional servers based on stack and user choices.
- Add backend-specific MCP suggestions (database, Docker, etc.).

### 5. Suggest and configure MCP servers

Based on the stack, recommend additions to `opencode.json` under `mcp`:

- Git / GitHub integration → Git/GitHub MCP
- PostgreSQL / MySQL / MongoDB → Database MCP
- Docker / container builds → Docker MCP
- Frontend-heavy work → Browser MCP
- Jira / Linear / issue tracker → Relevant MCP if available

Update `opencode.json` only after user approval. Do not commit secrets; use `{env:VAR}` for tokens.

### 6. Suggest opencode skills / commands

Ensure these remain available:

- Always: `project-init`, `project-status`
- Keep review gates via `docs/code-review-checklist.md` and `docs/verification-checklist.md`

### 7. Present summary

Output a concise markdown summary to the user covering:
- Detected or chosen stack
- Files updated
- Suggested MCP servers and skills
- Next recommended step (e.g., review `docs/features/`, then run `/project-status` and start implementing the first available `TODO-NNN`)

## Important rules

- Do not treat the scaffold files themselves as the product.
- Do not install or run package managers without user permission.
- Do not write real secrets into `opencode.json` or any committed file.
- Always ask before overwriting user-edited documentation unless the section is clearly a template placeholder.
