# DataFlow-Harness

[![](https://img.shields.io/github/repo-size/OpenDCAI/DataFlow-WebUI?color=green)](https://github.com/OpenDCAI/DataFlow-WebUI)
[![Technical Report](https://img.shields.io/badge/Technical%20Report-arXiv%3A2607.16617-B31B1B?logo=arxiv&logoColor=white)](https://arxiv.org/pdf/2607.16617)

中文文档：**[README_zh.md](README_zh.md)**

Build, run and manage AI4S-oriented [DataFlow](https://github.com/OpenDCAI/DataFlow)
pipelines with a coding agent — through MCP, with a browser result viewer, or with
skills alone. The default specialization is text-modal scientific data: papers,
abstracts, sections, and research corpora with evidence and provenance retained.

## Names you will see

| Name | What it refers to |
|---|---|
| **DataFlow** | The upstream data-processing framework ([OpenDCAI/DataFlow](https://github.com/OpenDCAI/DataFlow)). Installed as the `open-dataflow` package. Not this repo. |
| **DataFlow-Harness** | The AI4S-oriented system this repo builds: scientific-text workflow skills + MCP + WebUI working together. The name of the product, and of the paper. |
| **DataFlow-WebUI** | The repository name, and the read-only operator-result viewer specifically. Kept for URL stability. |
| **`DataFlow-WebUI-<version>.zip`** | A release package with the frontend pre-built, for running without a clone. See [docs/RELEASE-PACKAGE.md](docs/RELEASE-PACKAGE.md). |

This repo ships **three independent layers**. Install only the one you need.
They are independent at install and runtime; internally, all agent variants are
rendered from the same `skills/canonical/` source so the standalone and
MCP-aware instructions cannot drift.

Scientific-text mode is a specialization of the existing NL2Pipeline path, not
a second engine. It favors document ingestion, structured scientific extraction,
claim-evidence binding, grounded QA, and fidelity filtering while retaining the
general text fallback.

## Which layer do I want?

| | `webui` | `harness` | `skills` |
|---|---|---|---|
| **You get** | Operator-result viewer + backend + MCP | Backend + MCP, no browser UI | Agent skills only |
| **You need** | Python 3.10+, Node 20+ | Python 3.10+ | Python 3.9+ (to render the skills) |
| **Installs packages** | yes (uv + npm) | yes (uv) | **no** |
| **Runs a server** | yes, port 8000 | yes, port 8000 | **no** |
| **Agent writes pipelines** | ✅ | ✅ | ✅ |
| **Agent sees live operator registry** | ✅ | ✅ | ✗ (uses bundled reference) |
| **Execution results appear in a viewer** | ✅ | ✗ | ✗ |
| **Install time** | minutes | ~1 min | seconds |

The `skills` profile installs no packages, but it does run a Python script to
render the skill files, so Python 3.9+ must be present.

**30-second decision:**

- You want domain experts to inspect each operator's output in a browser → **`webui`**
- You drive everything from Claude Code / Codex / Cursor and never open a browser → **`harness`**
- You just want your agent to write correct DataFlow code, with no server → **`skills`**

```bash
git clone https://github.com/OpenDCAI/DataFlow-WebUI.git
cd DataFlow-WebUI

./install.sh --list                  # compare the three, in detail
./install.sh --profile skills        # or harness, or webui
```

Every profile supports `--check` (prerequisites only), `--dry-run` (show the plan, change nothing) and `--uninstall`.

Full per-layer guides: **[webui](docs/profiles/webui.md)** · **[harness](docs/profiles/harness.md)** · **[skills](docs/profiles/skills.md)**

## For agents setting this up

If an AI coding agent is configuring this repository, point it to
**[docs/agents/SETUP.md](docs/agents/SETUP.md)** before running installation.
That guide defines the authorization boundaries, exact commands, verification
steps, and actions that require human approval.

## Installation and usage

The `webui` profile installs the complete browser-based stack. Run the commands
below from the repository root and use the same activated environment for setup
and startup. Python **3.10 is recommended and is the minimum supported version**.

### Install prerequisites

You need Git, Python 3.10+, Node.js 20+ (which includes npm), and uv. Suggested
system installation methods:

| System | Python and Git | Node.js 20+ and npm | uv |
|---|---|---|---|
| macOS | `brew install python@3.10 git` | `brew install nvm` then `nvm install 20` | `brew install uv` |
| Ubuntu/Debian | `sudo apt update && sudo apt install -y python3.10 python3.10-venv git` | [nvm](https://github.com/nvm-sh/nvm), then `nvm install 20` | [uv installer](https://docs.astral.sh/uv/getting-started/installation/) |
| Windows PowerShell | `winget install Python.Python.3.10 Git.Git` | `winget install OpenJS.NodeJS.LTS` | [PowerShell installer](https://docs.astral.sh/uv/getting-started/installation/) |

On macOS/Linux, the uv installer is:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart the terminal after installing tools, then verify `python --version`,
`node --version` (must be 20 or newer), `npm --version`, and `uv --version`.

### Create and activate a Python environment

Choose **one** of the following; do not mix environments.

```bash
# venv (macOS/Linux; Windows PowerShell uses .venv\Scripts\Activate.ps1)
python3.10 -m venv .venv
source .venv/bin/activate

# Or conda (all systems)
conda create -n dataflow python=3.10 -y
conda activate dataflow
```

On Ubuntu/Debian, install `python3.10-venv` if `venv` reports that `ensurepip`
is missing. On Windows, use `py -3.10 -m venv .venv` and activate it from
PowerShell; `.sh` files do not run in plain `cmd.exe`.

### Install, start, and use

```bash
./install.sh --profile webui
./scripts/start.sh             # foreground; Ctrl+C stops it
# or: ./scripts/start.sh --daemon
```

Open <http://localhost:8000/> to inspect execution history and each operator's
output. Describe, create and run pipelines from Codex, Claude Code or Cursor;
the viewer refreshes automatically when a task is submitted.
Check or stop a background server with `./scripts/start.sh --status` and
`./scripts/start.sh --stop`.

uv is the default Python package installer. If your environment requires pip,
use `./install.sh --profile webui --pip` (or the compatibility
`./scripts/setup_all.sh --pip`).

### Configure an AI agent

The workflow is driven from a supported coding agent outside the browser.
Install and authenticate an agent, then explicitly configure its MCP connection:

```bash
# Claude Code
curl -fsSL https://claude.ai/code/install.sh | sh
export ANTHROPIC_API_KEY=sk-ant-...
./install.sh configure-agent --agent claude

# Codex (API key or `codex login` OAuth)
npm install --global @openai/codex
codex login                         # OAuth, or export OPENAI_API_KEY=sk-...
./install.sh configure-agent --agent codex

# Cursor: install the IDE, open this repository, then:
./install.sh configure-agent --agent cursor
```

Agent configuration is intentionally a separate step from installation. The
installer does not write API keys. See [Agent setup](docs/agents/SETUP.md) for
the exact authorization boundaries and verification steps.

### Runtime credentials for pipeline services

Agent authentication and pipeline-service credentials are separate. Open the
**Runtime credentials** panel in the result viewer to configure MinerU and LLM
serving keys. Keys are kept only in the backend process environment, are never
returned by the API or written to registry files, and must be entered again
after the backend restarts. Do not paste service keys into an agent chat.

## Installing never writes agent configuration

Installing and configuring an agent are two separate commands, on purpose:

```bash
./install.sh --profile harness                      # installs; writes no agent config
./install.sh configure-agent --agent claude         # project-scoped, shows a diff first
./install.sh configure-agent --agent codex --scope user   # asks before writing ~/.codex/
```

Installing **never writes MCP configuration**, in either scope. That is
`configure-agent`'s job.

### Where the skills land, per agent

`--scope` only affects Claude Code. The other two agents read from the repo, so
their assets are always installed here:

| Agent | Installed to | Available in | Verify |
|---|---|---|---|
| **Claude Code** | `./.claude/skills/` (default), or `~/.claude/skills/` with `--scope user` | this repo, or every project with `--scope user` | `/generating-dataflow-pipeline` appears in completion |
| **Codex** | `./AGENTS.md` + `./.codex/skills/` in this repo | this repo only — Codex reads `AGENTS.md` from the directory it starts in | open `AGENTS.md`; it routes to `.codex/skills/` |
| **Cursor** | `./.cursor/skills/` and `./.cursor/rules/` in this repo | this repo only, when opened as a project in Cursor | rules appear under Settings → Rules |

There is no global install for Codex or Cursor — both are directory-scoped by
design. `--scope user` does not change that.

Each profile declares the paths it must not touch, and the installer fingerprints
them before and after the install and fails if any changed. Anything it cannot
prove it wrote is never overwritten without `--force`.

Existing MCP servers in your config are merged, never overwritten. No API keys are read, written or logged.

Upgrading from `scripts/setup_all.sh`? See [docs/migration/from-setup-scripts.md](docs/migration/from-setup-scripts.md).

## What DataFlow-Harness is

DataFlow-Harness combines **skills** (procedural knowledge about operator selection, schema links and assembly order), **MCP** (a live connection to the operator registry and current pipeline state), and the **WebUI** (a read-only view of execution history and per-operator outputs). Pipeline construction and execution remain agent-driven.

<p align="center">
  <img width="1280" height="638" alt="DataFlow-Harness architecture" src="https://github.com/user-attachments/assets/d9c862ac-a1a2-42b1-9f07-440d20d59d8f" />
</p>

*Skills guide construction; MCP exposes the live registry and execution surface; the validation engine checks structure and schema compatibility; the WebUI presents results.*

### Why it helps

**Bridges the NL2Pipeline gap.** Natural-language intent becomes a persistent, platform-native pipeline artifact that an agent can validate, run and reuse while domain experts inspect its outputs.

**Procedural knowledge, not just tool lists.** Building a VQA dataset from textbooks needs PDF parsing, layout understanding, OCR, image-text alignment, QA extraction and quality filtering *in the right order*. That ordering knowledge is what the skills encode.

**Reusable workflows.** Data preparation becomes reusable pipelines rather than one-off scripts.

**Reported results.** The DataFlow-Harness paper reports a 93.3% end-to-end pass
rate on a 12-task data-engineering benchmark, with 72.5% lower cost and 49.9%
lower generation latency than vanilla Claude Code.

Those figures come from the paper's own harness and are **not reproducible from
this repository** — the benchmark tasks, run configuration and raw results are not
included here. Treat them as published findings, not as a claim you can verify by
installing this repo. Details and methodology: [DataFlow-Harness](https://huggingface.co/papers/2607.16617).

## Supported agents

| Agent | Mode | MCP config | Auth |
|---|---|---|---|
| **Claude Code** | Terminal / coding-agent client | `.mcp.json` (project) | `ANTHROPIC_API_KEY`, or `ANTHROPIC_BASE_URL` for a gateway |
| **Codex** | Codex client / terminal | `~/.codex/config.toml` | `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`), or `codex login` OAuth |
| **Cursor** | Cursor IDE | `.cursor/mcp.json` (project) | Cursor built-in |

All three agents operate outside the browser. The WebUI does not dispatch agents or edit pipelines; it displays task and operator results.

## Architecture and decisions

- [Component boundaries](docs/architecture/overview.md) — how the three layers depend on each other
- [ADR-001: single source of truth](docs/architecture/adr-001-source-of-truth.md) — why skills live in one repo
- [ADR-002: one package manager](docs/architecture/adr-002-package-managers.md) — npm vs Yarn, resolved
- [ADR-003: install/configure split](docs/architecture/adr-003-install-configure-split.md) — why installing writes no agent config
- [Branch audit](docs/architecture/branch-audit.md) — status of every remote branch

## Contributing

Skills are edited in `skills/canonical/` only. The files under `.claude/skills/`,
`.cursor/skills/`, `.cursor/rules/<skill>.mdc`, `.codex/skills/` and `AGENTS.md`
are generated build output and are **not tracked in git** — a fresh clone will not
have them:

```bash
make skills      # generate agent assets from skills/canonical/
make check       # run every static check CI runs
```

CI regenerates and diffs, so a hand-edited generated file fails the build.

## Citation

If you use the DataFlow-Harness platform, its agent workflow, MCP integration,
or editable pipeline interface, cite the DataFlow-Harness paper:

```bibtex
@article{he2026dataflow,
  title={DataFlow-Harness: A Grounded Code-Agent Platform for Constructing Editable LLM Data Pipelines},
  author={He, Runming and Wong, Zhen Hao and Liang, Hao and Meng, Zimo and Shen, Chengyu and Ma, Xiaochen and Zhang, Wentao},
  journal={arXiv preprint arXiv:2607.16617},
  year={2026}
}
```

If you use or cite the underlying DataFlow framework, cite the DataFlow paper:

```bibtex
@article{liang2025dataflow,
  title={DataFlow: An LLM-Driven Framework for Unified Data Preparation and Workflow Automation in the Era of Data-Centric AI},
  author={Liang, Hao and Ma, Xiaochen and Liu, Zhou and Wong, Zhen Hao and Zhao, Zhengyang and Meng, Zimo and He, Runming and Shen, Chengyu and Cai, Qifeng and Han, Zhaoyang and others},
  journal={arXiv preprint arXiv:2512.16676},
  year={2025}
}
```

## Community

<p align="center">
  <img src="https://github.com/user-attachments/assets/b958dc89-d76e-4e47-9277-22b3f6661944" alt="DataFlow community QR code" width="85%">
</p>

Licensed under Apache 2.0 — see [LICENSE](LICENSE).
