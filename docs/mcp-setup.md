# MCP Setup

MCP servers recommended for the zenengr project. Current state reflects `/project-init` choices.

## Core MCP servers

| Server | Purpose | Status | Notes |
| ------ | ------- | ------ | ----- |
| Git | Local git ops (status, diffs) | **Enabled** | `opencode.json` `mcp.git` (`uvx mcp-server-git`). |
| File system | Structured file access | Built-in | No config needed. |
| Fetch | Web docs & library lookup | **Enabled** | `opencode.json` `mcp.fetch` (`uvx mcp-server-fetch`). |
| GitHub | PRs, issues, repo search | Removed | Removed from `opencode.json`. |

## Project-specific MCP servers

| Server | Purpose | Status | Notes |
| ------ | ------- | ------ | ----- |
| PostgreSQL | Run queries / inspect schema | **Enabled** | Connects to local Postgres in Compose (`app`/`app@localhost:5432/app`). |
| Redis | Inspect cache keys, TTLs, invalidate cache | **Enabled** | Connects to local Redis in Compose (`redis://localhost:6379`). |
| Docker | Container / build tasks for local Compose stack | **Enabled** | Useful while building and running dev containers. |
| Browser / Playwright | E2E, screenshots, DOM inspection for SvelteKit UI | **Enabled** | Frontend-heavy work for SvelteKit UI verification. |
| Test runner | Run tests and parse results | Optional | Add when pytest/vitest suites land. |

> MCP servers are declared in `opencode.json` under `mcp`. **Tokens must use `{env:VAR}` — never commit secrets.**

## Configuration

MCP servers are declared in `opencode.json` under `mcp`. Current entries:

```json
{
  "mcp": {
    "git": { "type": "local",
      "command": ["uvx", "--with", "mcp>=1.2,<2", "mcp-server-git"],
      "enabled": true },
    "postgres": { "type": "local",
      "command": ["uvx", "--python", "3.13", "--with", "mcp>=1.2,<2", "postgres-mcp",
        "postgresql://app:app@localhost:5432/app"],
      "enabled": true },
    "redis": { "type": "local",
      "command": ["npx", "-y", "@redis/mcp-server"],
      "environment": { "REDIS_URL": "redis://localhost:6379" },
      "enabled": true },
    "fetch": { "type": "local",
      "command": ["uvx", "--with", "mcp>=1.2,<2", "mcp-server-fetch"],
      "enabled": true },
    "docker": { "type": "local", "command": ["npx", "-y", "mcp-server-docker"], "enabled": true },
    "browser": { "type": "local",
      "command": ["npx", "@playwright/mcp@latest"],
      "enabled": true }
  }
}
```

Notes:

- The `git` and `postgres` servers run under `uvx` and must pin `mcp>=1.2,<2` (via `--with`).
  Without the pin, uv resolves `mcp` 2.x, which removed the low-level `list_tools` API
  (`mcp-server-git` crashes with `AttributeError: 'Server' object has no attribute 'list_tools'`)
  and moved FastMCP out of `mcp.server.fastmcp` (`postgres-mcp` crashes with
  `ModuleNotFoundError`). Verified connected 2026-08-10.
- Postgres MCP points at the local `postgres` Compose service
  (`postgresql://app:app@localhost:5432/app`). Set the URL directly here or via
  `DATABASE_URL_MCP` if the connection string ever changes.
- Disable any server by setting `"enabled": false`.