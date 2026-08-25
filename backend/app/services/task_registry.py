import json
import os
import hashlib
import pandas
import datetime
import copy
import re
from typing import Dict, List, Optional, Any, Tuple
from app.core.container import container
from app.core.config import settings
from app.services.dataflow_engine import DataFlowEngine
from app.core.logger_setup import get_logger

logger = get_logger(__name__)

class TaskRegistry:
    """任务注册表，用于管理运行任务的生命周期"""
    
    def __init__(self, path: str | None = None):
        self.path = path or settings.TASK_REGISTRY
        self._ensure()
    
    def _ensure(self):
        # 只在文件不存在时初始化
        if not os.path.exists(self.path):
            initial_data = {"tasks": {}}
            self._write(initial_data)
            return

        # 文件存在但为空/损坏时兜底（可选）
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "tasks" not in data:
                self._write({"tasks": {}})
        except Exception:
            # 读取失败：备份旧文件再重建（推荐）
            broken = self.path + f".broken.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                os.replace(self.path, broken)
            except Exception:
                pass
            self._write({"tasks": {}})


    def _read(self) -> Dict:
        """读取注册表"""
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f) or {"tasks": {}}

    def _write(self, data: Dict):
        """写入注册表"""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _generate_task_id(self) -> str:
        """生成唯一的任务ID"""
        timestamp = pandas.Timestamp.now().isoformat()
        random_str = os.urandom(8).hex()
        combined = f"{timestamp}-{random_str}"
        return hashlib.md5(combined.encode("utf-8")).hexdigest()[:12]
    
    def list(self, status: Optional[str] = None, executor_type: Optional[str] = None) -> List[Dict]:
        """
        列出所有任务，可选过滤条件
        
        Args:
            status: 过滤特定状态的任务
            executor_type: 过滤特定类型的执行器 (operator/pipeline)
        """
        tasks = list(self._read()["tasks"].values())
        
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        
        if executor_type:
            tasks = [t for t in tasks if t.get("executor_type") == executor_type]
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return tasks
    
    def create(self, task: Dict) -> Dict:
        """
        创建新任务
        
        Args:
            task: 任务信息字典
        
        Returns:
            创建的任务（包含生成的ID和时间戳）
        """
        data = self._read()
        
        # 生成任务ID
        task_id = self._generate_task_id()
        task["id"] = task_id
        task["status"] = "pending"  # 初始状态
        task["created_at"] = pandas.Timestamp.now().isoformat()
        task["started_at"] = None
        task["finished_at"] = None
        task["output_id"] = None
        task["error_message"] = None
        
        # 保存任务
        tasks = data.get("tasks", {})
        tasks[task_id] = task
        data["tasks"] = tasks
        self._write(data)
        
        return task
    
    def get(self, task_id: str) -> Dict | None:
        """获取指定任务"""
        return self._read()["tasks"].get(task_id)
    
    def update(self, task_id: str, updates: Dict) -> Dict | None:
        """
        更新任务信息
        
        Args:
            task_id: 任务ID
            updates: 要更新的字段
        
        Returns:
            更新后的任务，如果任务不存在返回None
        """
        data = self._read()
        tasks = data.get("tasks", {})
        
        if task_id not in tasks:
            return None
        
        task = tasks[task_id]
        
        # 更新字段
        for key, value in updates.items():
            if value is not None:  # 只更新非None的值
                task[key] = value
        
        # 自动设置时间戳
        if "status" in updates:
            if updates["status"] == "running" and not task.get("started_at"):
                task["started_at"] = pandas.Timestamp.now().isoformat()
            elif updates["status"] in ["success", "failed", "cancelled"]:
                if not task.get("finished_at"):
                    task["finished_at"] = pandas.Timestamp.now().isoformat()
        
        tasks[task_id] = task
        data["tasks"] = tasks
        self._write(data)
        
        return task
    
    def delete(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功删除
        """
        data = self._read()
        tasks = data.get("tasks", {})
        
        if task_id in tasks:
            del tasks[task_id]
            data["tasks"] = tasks
            self._write(data)
            return True
        
        return False
    
    def get_statistics(self) -> Dict:
        """
        获取任务统计信息
        
        Returns:
            统计信息字典
        """
        tasks = self.list()
        
        stats = {
            "total": len(tasks),
            "pending": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "cancelled": 0,
            "by_executor_type": {
                "operator": 0,
                "pipeline": 0
            }
        }
        
        for task in tasks:
            status = task.get("status", "pending")
            stats[status] = stats.get(status, 0) + 1
            
            executor_type = task.get("executor_type", "")
            if executor_type in stats["by_executor_type"]:
                stats["by_executor_type"][executor_type] += 1
        
        return stats

    def get_current_time(self):
        """获取当前时间的ISO格式字符串"""
        return datetime.datetime.now().isoformat()

    def start_execution(self, pipeline_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """开始执行Pipeline"""
        # 获取Pipeline配置
        if pipeline_id:
            pipeline = container.pipeline_registry.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline with id {pipeline_id} not found")
            pipeline_config = pipeline.get("config", {})
            logger.info(f"Executing predefined pipeline: {pipeline_id}")
        else:
            if not config:
                raise ValueError("Either pipeline_id or config must be provided")
            pipeline_config = config
            logger.info("Executing pipeline with provided config")
        
        # 生成执行ID
        task_id = self._generate_task_id()
        
        # 创建初始结果记录
        initial_result = {
            "task_id": task_id,
            "pipeline_id": pipeline_id,
            "pipeline_config": pipeline_config,
            "status": "queued",
            "output": {},
            "logs": [f"[{self.get_current_time()}] Pipeline execution queued"]
        }
                
        # 直接保存到文件
        data = self._read()
        data["tasks"][task_id] = initial_result
        self._write(data)
        
        return task_id, pipeline_config, initial_result
    
    def list_executions(self) -> List[Dict[str, Any]]:
        """列出所有任务执行记录"""
        data = self._read()
        # 直接返回字典列表，不需要转换为对象
        executions = []
        for task_id, record in data.get("tasks", {}).items():
            item = copy.deepcopy(record)
            view = self._build_execution_view(task_id, data)
            item["pipeline_config"] = view["pipeline_config"]
            item.setdefault("output", {})["operators_detail"] = view["operators_detail"]
            item["output"]["operator_logs"] = view["operator_logs"]
            executions.append(item)
        return executions
    
    def get_execution_status(
        self, 
        task_id: str,
    ) -> Dict[str, Any]:
        """
        获取执行状态（包含算子粒度）
        
        Args:
            task_id: 执行 ID
        
        Returns:
            执行状态字典
        """
        # 读取执行记录
        data = self._read()
        execution_data = data.get("tasks", {}).get(task_id)
        
        if not execution_data:
            return None
        
        view = self._build_execution_view(task_id, data)
        
        return {
            "task_id": task_id,
            "pipeline_id": execution_data.get("pipeline_id"),
            "pipeline_config": view["pipeline_config"],
            "status": execution_data.get("status"),
            "operators_detail": view["operators_detail"],
            "operator_logs": view["operator_logs"],
            "logs": execution_data.get("logs", []),
            "parent_task_id": execution_data.get("parent_task_id"),
            "resume_from_step": execution_data.get("resume_from_step"),
            "started_at": execution_data.get("started_at"),
            "completed_at": execution_data.get("completed_at"),
        }
    
    def get_execution_logs(self, task_id: str, operator_name: Optional[str] = None) -> List[str]:
        """获取任务日志，可选过滤指定算子"""
        data = self._read()
        execution_data = data.get("tasks", {}).get(task_id)
        if not execution_data:
            return []
        
        # 如果是查询全局日志/流水线日志
        if not operator_name:
            return execution_data.get("logs", [])
        
        # Assuming we only care about completed logs or what's available.
        output = execution_data.get("output", {})
        operator_logs = output.get("operator_logs", {})
        
        # Try to find by operator name
        target_logs = []
        
        # First check structured logs
        if operator_name in operator_logs:
            return operator_logs[operator_name]
            
        # If not indexed by simple name, maybe key is op_key
        # Try finding key ending with name or just name
        for k, v in operator_logs.items():
            if k == operator_name or k.startswith(f"{operator_name}_"):
                return v

        # Default fallback to searching in main logs?
        return []

    def _cache_file_for_local_step(
        self,
        task_id: str,
        execution_data: Dict[str, Any],
        step: int,
    ) -> str:
        """Resolve one task-local operator output without assuming task success."""
        output = execution_data.get("output") or {}
        for result in output.get("execution_results") or []:
            if (
                result.get("index") == step
                and result.get("cache_file")
                and os.path.exists(result["cache_file"])
            ):
                return result["cache_file"]

        filename = f"dataflow_cache_step_step{step + 1}.jsonl"
        task_cache = os.path.join(settings.CACHE_DIR, f"{task_id}_output", filename)
        if os.path.exists(task_cache):
            return task_cache

        # Compatibility with executions created before task-specific cache folders.
        legacy_candidates = (
            os.path.join(settings.CACHE_DIR, filename),
            os.path.join(settings.CACHE_DIR, f"dataflow_cache_step_{step}.jsonl"),
        )
        return next((path for path in legacy_candidates if os.path.exists(path)), task_cache)

    def _effective_local_details(
        self,
        task_id: str,
        execution_data: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Return display details, repairing legacy duplicate-name failure marking."""
        output = execution_data.get("output") or {}
        details = copy.deepcopy(output.get("operators_detail") or {})
        actual_failed_index = (output.get("error_context") or {}).get("operator_index")

        for detail in details.values():
            index = detail.get("index")
            if not isinstance(index, int):
                continue
            cache_file = self._cache_file_for_local_step(task_id, execution_data, index)
            detail["result_available"] = os.path.exists(cache_file)
            if (
                detail.get("status") == "failed"
                and actual_failed_index is not None
                and index != actual_failed_index
                and detail["result_available"]
            ):
                detail["status"] = "completed"
                detail.pop("error", None)
        return details

    def _build_execution_view(
        self,
        task_id: str,
        data: Optional[Dict[str, Any]] = None,
        visited: Optional[set] = None,
    ) -> Dict[str, Any]:
        """Build the virtual full pipeline shown for a resumed execution."""
        data = data or self._read()
        execution_data = data.get("tasks", {}).get(task_id)
        if not execution_data:
            return {"operators_detail": {}, "operator_logs": {}, "pipeline_config": {}}

        visited = set(visited or ())
        if task_id in visited:
            logger.warning(f"Ignoring cyclic execution lineage at task {task_id}")
            return {"operators_detail": {}, "operator_logs": {}, "pipeline_config": {}}
        visited.add(task_id)

        local_details = self._effective_local_details(task_id, execution_data)
        local_logs = copy.deepcopy((execution_data.get("output") or {}).get("operator_logs") or {})
        local_config = copy.deepcopy(execution_data.get("pipeline_config") or {})
        parent_task_id = execution_data.get("parent_task_id")
        resume_from_step = execution_data.get("resume_from_step")
        if not parent_task_id or not isinstance(resume_from_step, int):
            return {
                "operators_detail": local_details,
                "operator_logs": local_logs,
                "pipeline_config": local_config,
            }

        parent_view = self._build_execution_view(parent_task_id, data, visited)
        offset = resume_from_step + 1
        merged_details = {
            key: value
            for key, value in parent_view["operators_detail"].items()
            if value.get("index", -1) < offset
        }
        merged_logs = copy.deepcopy(parent_view["operator_logs"])
        for _, detail in sorted(local_details.items(), key=lambda item: item[1].get("index", -1)):
            mapped = copy.deepcopy(detail)
            mapped["index"] = detail.get("index", 0) + offset
            merged_details[f'{mapped.get("name", "operator")}_{mapped["index"]}'] = mapped
        for key, value in local_logs.items():
            merged_logs[f"resume:{key}"] = value

        parent_config = parent_view["pipeline_config"]
        merged_config = copy.deepcopy(local_config)
        merged_config["operators"] = (
            copy.deepcopy((parent_config.get("operators") or [])[:offset])
            + copy.deepcopy(local_config.get("operators") or [])
        )
        if parent_config.get("input_dataset") is not None:
            merged_config["input_dataset"] = copy.deepcopy(parent_config["input_dataset"])

        return {
            "operators_detail": merged_details,
            "operator_logs": merged_logs,
            "pipeline_config": merged_config,
        }

    def resolve_execution_step(
        self,
        task_id: str,
        step: int,
        data: Optional[Dict[str, Any]] = None,
        visited: Optional[set] = None,
    ) -> Dict[str, Any]:
        """Map a displayed (global) step to its physical task/cache source."""
        data = data or self._read()
        execution_data = data.get("tasks", {}).get(task_id)
        if not execution_data:
            return None

        visited = set(visited or ())
        if task_id in visited:
            raise ValueError(f"Cyclic execution lineage at task {task_id}")
        visited.add(task_id)

        parent_task_id = execution_data.get("parent_task_id")
        resume_from_step = execution_data.get("resume_from_step")
        if parent_task_id and isinstance(resume_from_step, int) and step <= resume_from_step:
            return self.resolve_execution_step(parent_task_id, step, data, visited)

        local_step = step
        if parent_task_id and isinstance(resume_from_step, int):
            local_step = step - (resume_from_step + 1)
        if local_step < 0:
            raise ValueError(f"Invalid step index: {step}")

        config_ops = (execution_data.get("pipeline_config") or {}).get("operators") or []
        local_details = self._effective_local_details(task_id, execution_data)
        max_local_step = max(
            [len(config_ops) - 1]
            + [detail.get("index", -1) for detail in local_details.values()]
        )
        if local_step > max_local_step:
            raise ValueError(f"Invalid step index: {step}")

        detail = next(
            (value for value in local_details.values() if value.get("index") == local_step),
            {},
        )
        return {
            "source_task_id": task_id,
            "source_step": local_step,
            "cache_file": self._cache_file_for_local_step(task_id, execution_data, local_step),
            "operator_name": detail.get("name") or f"step_{step}",
            "operator_status": detail.get("status"),
        }

    def _infer_resume_lineage(
        self,
        pipeline_config: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Tuple[str, int]]:
        """Infer lineage when a pipeline starts from another task's cache dataset."""
        input_dataset = pipeline_config.get("input_dataset")
        dataset_id = input_dataset.get("id") if isinstance(input_dataset, dict) else input_dataset
        if not dataset_id:
            return None
        dataset = container.dataset_registry.get(dataset_id)
        root = dataset.get("root") if dataset else None
        if not root:
            return None

        match = re.fullmatch(r"dataflow_cache_step_step(\d+)\.jsonl", os.path.basename(root))
        cache_dir = os.path.basename(os.path.dirname(root))
        if not match or not cache_dir.endswith("_output"):
            return None

        source_task_id = cache_dir[:-len("_output")]
        data = data or self._read()
        source_task = data.get("tasks", {}).get(source_task_id)
        if not source_task:
            return None

        source_local_step = int(match.group(1)) - 1
        if source_local_step < 0:
            return None
        source_resume_step = source_task.get("resume_from_step")
        if source_task.get("parent_task_id") and isinstance(source_resume_step, int):
            source_global_step = source_resume_step + 1 + source_local_step
        else:
            source_global_step = source_local_step

        source = self.resolve_execution_step(source_task_id, source_global_step, data)
        if not source or os.path.normcase(os.path.abspath(source["cache_file"])) != os.path.normcase(os.path.abspath(root)):
            return None
        return source_task_id, source_global_step

    def get_execution_result(
        self, 
        task_id: str,
        step: Optional[int] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        获取执行结果
        
        Args:
            task_id: 执行 ID
            step: 步骤索引（可选，None 表示返回最后一个步骤的输出）
            limit: 返回的数据条数（默认5条）
        
        Returns:
            执行结果字典
        """
        data = self._read()
        execution_data = data.get("tasks", {}).get(task_id)
        
        if not execution_data:
            return None
        
        # 获取输出
        logs = execution_data.get("logs", [])
        view = self._build_execution_view(task_id, data)
        
        # 获取执行结果和算子进度
        operators_detail = view["operators_detail"]
        operator_logs = view["operator_logs"]

        if step is None:
            available = []
            for detail in operators_detail.values():
                index = detail.get("index")
                if not isinstance(index, int):
                    continue
                source = self.resolve_execution_step(task_id, index, data)
                if source and os.path.exists(source["cache_file"]):
                    available.append(index)
            step = max(available, default=0)
        
        # 读取缓存文件（使用绝对路径）
        try:
            source = self.resolve_execution_step(task_id, step, data)
        except ValueError:
            if operators_detail or (view["pipeline_config"].get("operators") or []):
                raise
            source = None
        cache_file = source["cache_file"] if source else ""
        
        sample_data = []
        total_count = 0
        file_exists = False
        
        if os.path.exists(cache_file):
            file_exists = True
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    for line in f:
                        total_count += 1
                        if len(sample_data) < limit:
                            try:
                                sample_data.append(json.loads(line.strip()))
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                logger.error(f"Failed to read cache file {cache_file}: {e}")
        
        operator_name = source.get("operator_name") if source else None
        operator_status = source.get("operator_status") if source else None

        return {
            "task_id": task_id,
            "pipeline_id": execution_data.get("pipeline_id"),
            "pipeline_config": view["pipeline_config"],
            "status": execution_data.get("status"),
            "step": step,
            "operator_name": operator_name,
            "operator_status": operator_status,
            "sample_data": sample_data,
            "sample_count": len(sample_data),
            "total_count": total_count,
            "file_exists": file_exists,
            "cache_file": cache_file,
            "source_task_id": source.get("source_task_id") if source else None,
            "source_step": source.get("source_step") if source else None,
            "logs": logs,
            "operator_logs": operator_logs,
            "started_at": execution_data.get("started_at"),
            "completed_at": execution_data.get("completed_at"),
            "operators_detail": operators_detail 
        }
    
    async def start_execution_async(
        self, 
        pipeline_id: Optional[str] = None, 
        config: Optional[Dict[str, Any]] = None,
        parent_task_id: Optional[str] = None,
        resume_from_step: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        异步开始执行Pipeline（使用 Ray）
        
        Args:
            pipeline_id: 预定义 Pipeline ID
            config: 自定义 Pipeline 配置
        
        Returns:
            包含 task_id 的字典
        """
        from app.services.ray_pipeline_executor import ray_executor
        
        # 获取Pipeline配置
        if pipeline_id:
            pipeline = container.pipeline_registry.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline with id {pipeline_id} not found")
            pipeline_config = pipeline.get("config", {})
            pipeline_name = pipeline.get("name", "Unknown Pipeline")
            logger.info(f"Executing predefined pipeline asynchronously: {pipeline_id}")
        else:
            if not config:
                raise ValueError("Either pipeline_id or config must be provided")
            pipeline_config = config
            pipeline_name = "Custom Pipeline"
            logger.info("Executing pipeline with provided config asynchronously")

        registry_data = self._read()
        if not parent_task_id:
            inferred_lineage = self._infer_resume_lineage(pipeline_config, registry_data)
            if inferred_lineage:
                parent_task_id, resume_from_step = inferred_lineage
                logger.info(
                    f"Inferred resumed execution from task {parent_task_id} "
                    f"step {resume_from_step}"
                )

        if resume_from_step is not None and not parent_task_id:
            raise ValueError("parent_task_id is required when resume_from_step is provided")
        if parent_task_id:
            if parent_task_id not in registry_data.get("tasks", {}):
                raise ValueError(f"Parent task with id {parent_task_id} not found")
            if resume_from_step is None:
                parent_view = self._build_execution_view(parent_task_id, registry_data)
                available = []
                for detail in parent_view["operators_detail"].values():
                    index = detail.get("index")
                    if not isinstance(index, int):
                        continue
                    source = self.resolve_execution_step(parent_task_id, index, registry_data)
                    if source and os.path.exists(source["cache_file"]):
                        available.append(index)
                if not available:
                    raise ValueError(f"Parent task {parent_task_id} has no reusable operator output")
                resume_from_step = max(available)
            source = self.resolve_execution_step(parent_task_id, resume_from_step, registry_data)
            if not source or not os.path.exists(source["cache_file"]):
                raise ValueError(
                    f"Parent task {parent_task_id} has no result for step {resume_from_step}"
                )
        
        # 生成执行ID
        task_id = self._generate_task_id()
        
        # 创建 Task
        task_data = {
            "dataset_id": pipeline_config.get("input_dataset", ""),
            "executor_name": pipeline_name,
            "executor_type": "pipeline",
            "meta": {
                "pipeline_id": pipeline_id if pipeline_id else "custom",
                "task_id": task_id
            }
        }
        task = container.task_registry.create(task_data)
        task_id = task["id"]
        
        logger.info(f"Task created: {task_id}")
        
        # 创建初始结果
        initial_result = {
            "task_id": task_id,
            "pipeline_id": pipeline_id,
            "pipeline_config": pipeline_config,
            "status": "queued",
            "output": {},
            "logs": [f"[{self.get_current_time()}] Pipeline execution queued"],
            "operator_progress": {}
        }
        if parent_task_id:
            initial_result["parent_task_id"] = parent_task_id
            initial_result["resume_from_step"] = resume_from_step
        
        # 保存初始状态
        data = self._read()
        data["tasks"][task_id] = initial_result
        self._write(data)
        dataflow_runtime = DataFlowEngine.decode_hashed_arguments(pipeline_config, task_id)
        
        # 提交到 Ray 异步执行
        await ray_executor.submit_execution(
            pipeline_config=pipeline_config,
            dataflow_runtime=dataflow_runtime,
            task_id=task_id,
            pipeline_registry_path=self.path,
            pipeline_execution_path=self.path
        )
        
        logger.info(f"Pipeline execution submitted to Ray: {task_id}")
        
        return {
            "task_id": task_id
        }

    def kill_execution(self, task_id: str) -> bool:
        """
        终止指定的 Pipeline 执行任务
        
        Args:
            task_id: 执行 ID
        
        Returns:
            是否成功终止
        """
        from app.services.ray_pipeline_executor import ray_executor
        from datetime import datetime
        
        # 1. 直接读取最新数据
        data = self._read()
        task_record = data.get("tasks", {}).get(task_id)
        
        if not task_record:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # 检查任务状态
        status = task_record.get("status", "pending")
        if status in ["success", "failed", "cancelled"]:
            logger.warning(f"Task {task_id} is already {status}, cannot kill")
            return False
        
        try:
            # 2. 物理 Kill
            # 注意：先 Kill 进程，后改状态。
            # 这样即使 Kill 之后 worker 还有最后一丝余力想写文件，也会因为进程被切断而停止
            killed_via_ray = ray_executor.kill_execution(task_id)
            
            # 3. 构造状态更新
            now = datetime.now().isoformat()
            task_record["status"] = "cancelled"
            task_record["finished_at"] = now
            task_record["error_message"] = "Task was killed by user"
            
            # ✅ 关键：同步更新内部算子的状态，让 UI 显示更准确
            if "output" in task_record and "operators_detail" in task_record["output"]:
                for op_key, op_info in task_record["output"]["operators_detail"].items():
                    if op_info.get("status") in ["running", "initializing"]:
                        op_info["status"] = "cancelled"
                        op_info["completed_at"] = now
            
            # 4. 强制写回磁盘（覆盖式更新）
            data["tasks"][task_id] = task_record
            self._write(data)
            
            logger.info(f"Task {task_id} killed. Ray_success: {killed_via_ray}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to kill task {task_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # 即使发生异常，也尝试更新任务状态
            try:
                now = datetime.now().isoformat()
                task_record["status"] = "cancelled"
                task_record["finished_at"] = now
                task_record["error_message"] = f"Task kill failed: {str(e)}"
                
                # 同步更新内部算子的状态
                if "output" in task_record and "operators_detail" in task_record["output"]:
                    for op_key, op_info in task_record["output"]["operators_detail"].items():
                        if op_info.get("status") in ["running", "initializing"]:
                            op_info["status"] = "cancelled"
                            op_info["completed_at"] = now
                
                data["tasks"][task_id] = task_record
                self._write(data)
                logger.info(f"Task {task_id} status updated to cancelled despite error")
                return True
            except Exception as update_error:
                logger.error(f"Failed to update task {task_id} status after kill failure: {update_error}")
                return False
