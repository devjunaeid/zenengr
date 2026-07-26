# MCP Setup

MCP servers recommended for the zenengr project. Current state reflects `/project-init` choices.

## Core MCP servers

| Server | Purpose | Status | Notes |
| ------ | ------- | ------ | ----- |
| GitHub | PRs, issues, repo search | **Enabled** | `opencode.json` `mcp.github`; token via `{env:GITHUB_TOKEN}`. |
| Git | Local git ops (status, diffs) | **Enabled** | `opencode.json` `mcp.git` (`uvx mcp-server-git`). |
| File system | Structured file access | Built-in | No config needed. |
| Web fetch | Library docs lookup | Optional | Consider adding when researching Svelte/FastAPI docs. |

## Project-specific MCP servers

| Server | Purpose | Status | Notes |
| ------ | ------- | ------ | ----- |
| PostgreSQL | Run queries / inspect schema | **To enable** | Local Postgres in Compose; see config below. |
| Docker | Container / build tasks for local Compose stack | **To enable** | Useful while building FEAT-001 dev environment. |
| Browser / Puppeteer | E2E, screenshots, DOM inspection for SvelteKit UI | **To enable** | Frontend-heavy work once UI is implemented. |
| Test runner | Run tests and parse results | Optional | Add when pytest/vitest suites land. |

> All three "to enable" servers were approved by the user during `/project-init` ("all" MCP).
> Concrete entries were added to `opencode.json` below — adjust commands/packages to your installed MCP server packages and re-enable as needed. **Tokens must use `{env:VAR}` — never commit secrets.**

## Configuration

MCP servers are declared in `opencode.json` under `mcp`. Current entries:

```json
{
  "mcp": {
    "github": { "type": "local", "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
      "enabled": true, "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "{env:GITHUB_TOKEN}" } },
    "git": { "type": "local", "command": ["uvx", "mcp-server-git"], "enabled": true },
    "postgres": { "type": "local",
      "command": ["uvx", "--python", "3.13", "postgres-mcp", "{env:DATABASE_URL_MCP}"],
      "enabled": true },
    "docker": { "type": "local", "command": ["npx", "-y", "mcp-server-docker"], "enabled": true },
    "browser": { "type": "local",
      "command": ["npx", "-y", "@modelcontextprotocol/server-puppeteer"],
      "enabled": true }
  }
}
```

Notes:

- Adjust exact package names to the MCP servers you have installed; the entries above use commonly
  published packages. Re-disable any server by setting `"enabled": false`.
- Postgres MCP connection string should point at the local `postgres` service published port
  (e.g. `postgresql://app:app@localhost:5432/app`) — set in `.env` as `DATABASE_URL_MCP`.