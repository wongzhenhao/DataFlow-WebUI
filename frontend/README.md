<p align="center">
  <img src="src/assets/logo/logo.png" alt="DataFlow" width="120px"/>
</p>

# DataFlow Operator Result Viewer

Chinese version: [docs/README_zh.md](docs/README_zh.md)

This Vue 3 + Vite frontend is intentionally read-only. A domain expert can:

- select a pipeline execution;
- inspect the ordered operator statuses;
- compare an operator's input and output records;
- download each step's JSONL result;
- configure MinerU and LLM serving credentials for the current backend process.

Pipeline creation, editing, validation and execution happen through Codex,
Claude Code, Cursor or the backend API. The browser does not contain a chat
panel, DAG editor or Run button.

## Requirements

- Node.js 20+
- npm (the repository does not use Yarn)
- the FastAPI backend running on `127.0.0.1:8000` for local development

## Install and run

From `frontend/`:

```bash
npm install
npm run dev
```

Open <http://localhost:5173/>. `vite.config.js` proxies `/api` and `/mcp` to
`http://127.0.0.1:8000` without rewriting the path.

For the normal full-stack installation, run this from the repository root
instead:

```bash
./install.sh --profile webui
./scripts/start.sh
```

The backend then serves the built viewer at <http://localhost:8000/>.

## Runtime credentials

The **Runtime credentials** panel accepts MinerU and API-serving keys over the
local backend connection. Keys are write-only API inputs: the frontend clears
the input after submission, the backend never returns the value, and registry
files contain only serving metadata. Credentials live in the backend process
environment and must be entered again after a restart.

Do not put keys in source files, `.env` files, generated JSONL, or agent chats.

## Production build

```bash
npm run build
```

The output is written to `frontend/dist/`. The root installer rebuilds this
directory on every `webui` install so upgrades cannot keep a stale canvas build.

## Relevant structure

```text
src/
├── views/review/index.vue        # execution and operator result viewer
├── js/viewerI18n.js             # compact viewer translations
├── axios/                       # generated and custom API access
├── router/index.js              # viewer-only route
├── App.vue
└── main.js
```

The active app exposes `$api` and `$axios` through the API plugin. Legacy canvas
components remain in the source tree for now but are not routed or bundled into
the production viewer.

## Troubleshooting

| Symptom | Check |
|---|---|
| Viewer cannot load executions | Backend is running and `/api/v1/tasks/executions` is reachable |
| Runtime credential count resets | Expected after a backend restart; enter the keys again |
| A completed step shows no preview | Use Download; the viewer falls back to the task-specific JSONL result |
| Production page is stale | Re-run `./install.sh --profile webui` or `npm run build` |
