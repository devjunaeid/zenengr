# Agentic Development Template

> A template for bootstrapping AI-driven development with opencode.
> Use this as a starting scaffold for any new or existing software project.

## What this template provides

1. **Docs-first workflow:** Every implementation starts from feature → user stories → todos → progress.
2. **Frontmatter-based docs:** Features, stories, todos, and decisions live as small, machine-readable files under `docs/`. opencode can scan them in milliseconds even as the project grows.
3. **opencode integration:**
   - `Agent.md` at the root tells opencode which files to read and which workflow to follow.
   - `AGENTS.md` gives opencode high-level context about this scaffold.
   - `opencode.json` configures project defaults, permissions, MCP, and instructions.
   - `.opencode/skill/` holds local skills; `.opencode/command/` registers `/project-init` and `/project-status`.
4. **One-command onboarding:** Run `/project-init` to let the agent discover or ask about the tech stack and populate the docs automatically.

## Quick start

### For a brand-new project

1. Copy this template into a new directory.
2. Open the directory in opencode.
3. Type `/project-init`.
4. Answer the stack/product questions (or let the agent scan an existing codebase).
5. The agent will populate `docs/index.md`, `docs/features/`, `docs/stories/`, `docs/todos/`, `docs/progress.md`, `docs/frontend-standard.md`, `docs/backend-standard.md`, `docs/ui-ux-spec.md`, and `docs/mcp-setup.md`.
6. Review the generated docs, then run `/project-status` and start implementing the first available task.

### For an existing codebase

1. Copy this template into the repository root (do not overwrite existing source files).
2. Open in opencode and run `/project-init`.
3. The agent will scan manifests like `package.json`, `pyproject.toml`, `go.mod`, etc., to pre-fill the stack, then ask you to confirm.
4. Review and refine the generated docs before starting work.

## File structure

```text
Agent.md                          # Root agent instructions — read first every session
AGENTS.md                         # opencode repository guidance
README.md                         # This file — template documentation
opencode.json                     # Project settings, permissions, MCP, instructions
.opencode/
  skill/
    project-init/                 # project-init skill
      SKILL.md
      instructions.md
    project-status/               # project-status skill
      SKILL.md
      instructions.md
  command/
    project-init.md               # /project-init slash command
    project-status.md             # /project-status slash command
docs/
  index.md                        # Auto-generated project dashboard
  progress.md                     # Living progress tracker
  stack-discovery.md              # Stack questionnaire filled by /project-init
  frontend-standard.md            # Frontend coding standards
  backend-standard.md             # Backend coding standards
  ui-ux-spec.md                   # UI/UX specification
  code-review-checklist.md        # Post-implementation review checklist
  verification-checklist.md       # Pre-merge verification checklist
  mcp-setup.md                    # MCP server recommendations
  features/                       # One file per feature (frontmatter-based)
  stories/                        # One file per user story
  todos/                          # One file per implementation task
  decisions/                      # Architecture / product decisions
  sprints/                        # Sprint plans and retrospectives
```

## Customizing the template

### Change the skills / commands

Edit `.opencode/skill/project-init/instructions.md` to adjust the onboarding questions, detected files, or generated docs.

Register additional slash commands by adding markdown files under `.opencode/command/`:

```markdown
---
description: One sentence describing what the command does.
agent: build
---

(command body — the prompt opencode runs)
```

### Add default MCP servers

Edit `opencode.json` `mcp` to include servers every project should have. Keep token values as `{env:TOKEN_NAME}` and never commit real secrets.

### Add organization-wide standards

Replace or extend `docs/frontend-standard.md` and `docs/backend-standard.md` with your team's conventions. These files are imported by every project that uses this template.

### Add domain-specific doc templates

If your projects typically need extra planning artifacts — e.g., `docs/data-model.md`, `docs/security-model.md`, `docs/api-contract.md` — add them under `docs/` and reference them in `Agent.md` so the agent reads them for context.

## Distributing the template

- Share this directory as a Git repository or a downloadable archive.
- When a developer clones it, they should replace `README.md` with their project description after running `/project-init`.
- Keep the `Agent.md`, `AGENTS.md`, `opencode.json`, `.opencode/`, and `docs/` structure intact so future opencode sessions can use the established workflow.

## Important conventions

1. **Scaffold ≠ product.** The files in this template are starting points. `/project-init` exists specifically to switch context from "this is the scaffold" to "this is the actual project being built."
2. **Docs live in `docs/`.** Do not scatter PRDs, user stories, or progress trackers across the repository root.
3. **Progress is updated after every meaningful change.** No task is "done" until `docs/progress.md` reflects it.
4. **Review gates are required.** Every task goes through the checklists in `docs/code-review-checklist.md` and `docs/verification-checklist.md`.

## Workflow summary

```
/project-init
      │
      ▼
Fill docs/stack-discovery.md
      │
      ▼
Generate docs/features/
      │
      ▼
Generate docs/stories/
      │
      ▼
Generate docs/todos/
      │
      ▼
/project-status (before each session)
      │
      ▼
Implement (frontend or backend standard)
      │
      ▼
Code review + verification checklists
      │
      ▼
Update docs/todos/ and docs/progress.md
```

## Troubleshooting

- **"/project-init" not found:** Ensure `.opencode/command/project-init.md` exists and restart opencode.
- **Skill overwrites my edits:** `/project-init` is designed to ask before overwriting non-placeholder content. If it does not, refine the rules in `.opencode/skill/project-init/instructions.md`.
- **"/project-status" not found:** Ensure `.opencode/command/project-status.md` exists and restart opencode.
- **MCP config not picked up:** Restart opencode or check that `opencode.json` is valid JSON and the server command is installed. Do not commit secrets.
