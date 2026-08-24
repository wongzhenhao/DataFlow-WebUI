# Profile: `webui`

The complete stack: read-only operator-result viewer, FastAPI backend, MCP
server, and all skills.

```bash
./install.sh --profile webui
```

## What this is for

You want domain experts to open a browser, select an execution, and inspect the
ordered operators plus each step's records. Pipeline construction and execution
happen in Codex, Claude Code or Cursor rather than in the browser.

## What this is not for

- A machine without Node.js → use [`harness`](harness.md)
- No server at all → use [`skills`](skills.md)

## Prerequisites

- Python 3.10+ (3.10 recommended) in an activated venv or conda environment
- uv (the default Python package installer; use `--pip` as a fallback)
- Node.js 20+ with npm (recommended: [nvm](https://github.com/nvm-sh/nvm) — `nvm install 20`)
- At least one coding-agent client to construct or execute pipelines:
  - Claude Code: `curl -fsSL https://claude.ai/code/install.sh | sh`
  - Codex: `npm i -g @openai/codex`
  - Cursor: [download the IDE](https://cursor.com)

This project uses **npm**, not Yarn, despite a tracked `yarn.lock` — see [ADR-002](../architecture/adr-002-package-managers.md).

If `python3` resolves to an older Python, select a 3.10+ interpreter explicitly:

```bash
DATAFLOW_PYTHON="$(command -v python3.10)" ./install.sh --profile webui
```

## Install

```bash
./install.sh --profile webui --check      # prerequisites only
./install.sh --profile webui --dry-run    # print the plan
./install.sh --profile webui
# If uv is unavailable or disallowed:
./install.sh --profile webui --pip
```

Steps: install `open-dataflow` with uv → backend deps → `npm install` +
`npm run build` → initialize the DataFlow core directory → render and
install all skills. Pass `--pip` to use pip explicitly. The frontend is rebuilt
on every WebUI install so a previous canvas build cannot survive an upgrade.

## Run

```bash
./scripts/start.sh              # foreground
./scripts/start.sh --daemon     # background
./scripts/start.sh --status
./scripts/start.sh --stop
```

Then open **http://localhost:8000/**. The backend serves both the result viewer
and the MCP endpoint. If you changed `DATAFLOW_PORT`, use that port.

There is **no authentication** — single-user local tool. `0.0.0.0` exposes it to your network; use `DATAFLOW_HOST=127.0.0.1` to keep it local.

## Connect an agent

```bash
./install.sh configure-agent --agent claude
./install.sh configure-agent --agent codex --scope user
./install.sh configure-agent --agent cursor
```

### Configuring Codex on Python 3.10

Editing `~/.codex/config.toml` requires parsing it first — the configurator will
not touch a file it cannot validate. Python 3.11+ has `tomllib` built in. On
3.10, install the declared dependency once:

```bash
pip install -r installers/requirements-configure.txt
```

Without it, `configure-agent --agent codex` refuses and prints the block to add
by hand. Claude and Cursor are unaffected — their configs are JSON.

### Auth

```bash
export ANTHROPIC_API_KEY=sk-ant-...          # Claude Code
export ANTHROPIC_BASE_URL=https://gateway/v1 # optional gateway

export OPENAI_API_KEY=sk-...                 # Codex, key mode
export OPENAI_BASE_URL=https://gateway/v1    # optional gateway
codex login                                  # Codex, OAuth mode (no key)
```

Export agent credentials in the shell that starts the agent client. The
installer never stores them.

### Pipeline-service credentials

MinerU and LLM serving keys are separate from agent authentication. Use the
viewer's **Runtime credentials** panel to create serving metadata and enter the
required keys. They are held only in the backend process environment, never
returned or persisted, and must be entered again after a backend restart.
Never paste them into an agent conversation.

### Usage flow

1. Start the backend and open the result viewer.
2. Use Codex, Claude Code or Cursor to create and validate a pipeline through MCP.
3. Ask the agent to execute only when you intend to run it.
4. Select the new task in the viewer; it refreshes automatically and exposes
   each operator's output and downloads.

## Minimal verification

1. `./scripts/start.sh --status` reports running
2. `http://localhost:8000/` shows **Operator Result Viewer**
3. Ask the external agent to list operator categories through MCP — expect
   `core_text`, `general_text`, `reasoning`, …
4. Run a small pipeline explicitly; a task and its operator results should
   appear in the viewer

## Upgrade

```bash
git pull
./install.sh --profile webui
./scripts/start.sh --stop && ./scripts/start.sh --daemon
```

## Uninstall

```bash
./install.sh --uninstall            # installed skills
rm -rf frontend/node_modules frontend/dist
```

Python packages and your pipelines under `backend/data/` are left alone.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| "UI index file not found" in logs | Frontend not built | `cd frontend && npm install && npm run build` |
| Blank page at `:8000` | Partial frontend build | Delete `frontend/dist`, re-run the WebUI install |
| `DataFlow core is incomplete` | A prior initialization failed partway through | Move the incomplete `backend/data/dataflow_core/` aside, then re-run the install |
| Agent invents operators | Skill not loaded | Re-run `./install.sh --profile webui --force` |
| `lang="zh"` yields 0 rows on English data | Stale skill | Same as above — the skill encodes the language-detection policy |
| Cursor sees no MCP tools | Not enabled in IDE, or backend down | Enable in Settings; check `./scripts/start.sh --status` |
| Pipeline validation warns `serving_credential_not_configured` | Runtime key is absent after a fresh start | Open **Runtime credentials**, enter the key locally, then retry |
