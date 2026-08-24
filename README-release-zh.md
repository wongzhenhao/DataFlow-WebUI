# DataFlow-WebUI (Release)

本发布包的完整快速开始（中英双语）：**[docs/RELEASE-PACKAGE.md](docs/RELEASE-PACKAGE.md)**

Python 推荐 3.10，最低要求也是 3.10。请先选择一种隔离环境：

```bash
# venv
python3.10 -m venv .venv
source .venv/bin/activate       # Windows PowerShell：.venv\Scripts\Activate.ps1

# 或 conda
conda create -n dataflow python=3.10 -y
conda activate dataflow
```

发布包已经包含构建好的前端，运行发布包不需要 Node.js/npm。请先按系统
说明安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)，然后执行：

```bash
cd backend && uv pip install -r requirements.txt && cd ..
./run.sh          # Windows: run.bat
```

如果无法使用 uv，可改用 `python -m pip install -r requirements.txt`。依赖
固定了 `setuptools<82`（DataFlow 仍使用 `pkg_resources`）和 `mcp<2`
（`fastapi-mcp==0.4.0` 使用 MCP v1 的 Server API）。

然后浏览器打开 http://localhost:8000/，查看 Pipeline 运行记录和每个算子的结果。
Pipeline 的创建与执行由外部 MCP Agent 完成。

MinerU 或 LLM 服务的密钥请在本机查看器的“运行凭证”面板填写。密钥只保留在
当前后端进程中，不会通过 API 返回或持久化，后端重启后需要重新填写。不要把
密钥粘贴到 Agent 对话中。

注意：服务不带任何认证，且执行 pipeline 等同于任意代码执行。默认只监听 `127.0.0.1`（仅本机）。
如需局域网访问，需显式指定 `DATAFLOW_HOST=0.0.0.0 ./run.sh`。
