"""Expose the supported DataFlow backend operations as MCP tools."""
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from app.core.logger_setup import get_logger

logger = get_logger(__name__)

_mcp_instance: FastApiMCP = None


def create_mcp_server(app: FastAPI) -> FastApiMCP:
    """
    创建并挂载 MCP Server 到 FastAPI app。
    挂载路径为 /mcp，Claude Code CLI 通过项目根目录的 .mcp.json 自动连接此地址。
    """
    global _mcp_instance

    mcp = FastApiMCP(
        app,
        name="DataFlow MCP Server",
        description="Tools for managing DataFlow pipelines, tasks, operators and datasets",
        # 白名单：只暴露已审核的查询、构建、校验和执行操作。
        include_operations=[
            "list_operator_categories",         # GET /api/v1/operators/categories  ← 便宜入口，带 use_for/not_for 指引；agent 必须先调
            "recommend_operator_categories",    # POST /api/v1/operators/recommend_categories  ← 结合任务描述/列名给出最多 2 个候选 category
            "list_operators",                   # GET /api/v1/operators/by_category?category=xxx  category 必填，缺省/非法会 40010/40011
            "get_operator_detail_by_name",      # GET /api/v1/operators/details/{name} 单个算子详情
            "list_pipelines",                   # GET /api/v1/pipelines/
            "create_pipeline",                  # POST /api/v1/pipelines/
            "update_pipeline",                  # PUT /api/v1/pipelines/{pipeline_id}
            "get_pipeline",                     # GET /api/v1/pipelines/{pipeline_id}
            "execute_pipeline",                 # POST /api/v1/tasks/execute
            "execute_pipeline_async",           # POST /api/v1/tasks/execute-async
            "get_execution_status",             # GET /api/v1/tasks/execution/{task_id}/status
            "get_task_result",                  # GET /api/v1/tasks/execution/{task_id}/result
            "list_datasets",                    # GET /api/v1/datasets/
            "get_dataset_columns",              # GET /api/v1/datasets/columns/{ds_id}
            "get_dataset_preview",              # GET /api/v1/datasets/preview/{ds_id}  ← 必须在设置 lang 等语义参数前调用，agent 凭样本判断数据语言
            "register_dataset",                 # POST /api/v1/datasets/
            "list_serving",                     # GET /api/v1/serving/
            "list_servings",                    # GET /api/v1/serving/plural_alias (backward-compatible alias)
            "validate_pipeline_config",         # POST /api/v1/pipelines/validate
        ],
    )
    mcp.mount()  # 挂载到 /mcp 路径

    _mcp_instance = mcp
    logger.info("MCP Server mounted at /mcp")

    return mcp
def get_mcp_instance() -> FastApiMCP:
    """获取全局 MCP 实例（用于调试）"""
    return _mcp_instance
