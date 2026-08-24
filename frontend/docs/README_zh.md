# DataFlow 算子结果查看器

当前前端是面向领域专家的只读结果查看器。Pipeline 的设计、校验和执行由
Codex、Claude Code 或 Cursor 等外部 Agent 通过 MCP 完成；浏览器只展示：

- Pipeline 的算子顺序与运行状态
- 每个算子的输入、输出和错误信息
- JSONL 行级结果与字段变化
- Pipeline 服务所需的运行凭证状态

前端不提供聊天框、可编辑 DAG 或“运行 Pipeline”按钮。

## 开发环境

- Node.js 20
- npm
- 已在 `127.0.0.1:8000` 启动的 DataFlow 后端

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173/`。开发代理会把 `/api` 和 `/mcp` 请求转发到
`http://127.0.0.1:8000`，不重写路径。

从仓库根目录安装完整 WebUI 时，也可以运行：

```bash
./install.sh --profile webui --agent codex
```

## Pipeline 服务运行凭证

MinerU 或 LLM Serving 所需的 API Key 由用户在本机结果查看器的“运行凭证”
面板中填写。后端只在当前进程内存和环境中使用凭证，不会通过 API 返回明文，
也不会写入仓库、Pipeline JSON 或数据集。后端重启后需要重新填写。

Agent 自身的登录或 MCP 认证与这些 Pipeline 服务凭证相互独立。不要把 API Key
粘贴到 Agent 对话中。

## 生产构建

```bash
npm run build
```

产物位于 `frontend/dist/`。`webui` 安装会重新构建该目录，避免升级后继续使用
旧版画布界面。

## 当前代码入口

```text
src/
├── views/review/index.vue        # 当前唯一业务页面
├── js/viewerI18n.js              # 查看器中英文文本
├── router/index.js               # 路由到结果查看器
├── axios/                        # 后端 API 客户端并注入 $api / $axios
├── App.vue
└── main.js
```

旧的画布组件仍保留在源码中供后续迁移参考，但不在当前路由和生产入口中使用。

## 常见问题

- 页面无法加载：确认后端已在 `127.0.0.1:8000` 启动。
- 没有运行记录：先让外部 Agent 创建并执行 Pipeline。
- 算子因凭证失败：在“运行凭证”面板检查对应服务是否显示已配置。
- 构建失败：确认 Node.js 主版本为 20，然后重新执行 `npm install`。
