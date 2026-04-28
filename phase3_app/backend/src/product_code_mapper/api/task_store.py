from __future__ import annotations

from dataclasses import asdict, dataclass, field
from io import BytesIO
from json import loads as json_loads
from threading import RLock, Thread
from uuid import uuid4

from product_code_mapper.db.repository import TaskRepo
from product_code_mapper.domain.models import Candidate, CompanyProduct, CustomerItem, MatchResult
from product_code_mapper.domain.statuses import MatchStatus
from product_code_mapper.excel.exporter import export_run_result
from product_code_mapper.model.client import FakeModelClient
from product_code_mapper.excel.field_confirmation import (
    FieldConfirmation,
    suggest_company_mapping,
    suggest_customer_mapping,
)
from product_code_mapper.excel.review_importer import ReviewImportResult, import_reviewed_excel
from product_code_mapper.runs.engine import MatchRunEngine, MatchRunResult
from product_code_mapper.runs.metrics import RunMetrics
from product_code_mapper.runs.state_machine import RunStateMachine, RunStatus


@dataclass
class TaskRecord:
    task_id: str
    customer_items: list[CustomerItem] = field(default_factory=list)
    status: str = "created"
    result: MatchRunResult | None = None
    partial_metrics: RunMetrics | None = None
    current_run_id: str | None = None
    review_import: ReviewImportResult | None = None
    fields_confirmed: bool = False


class InMemoryTaskStore:
    """Task store backed by TaskRepo (SQLite) with in-memory runtime state."""

    def __init__(self, repo: TaskRepo | None = None,
                 model_client_factory: "callable | None" = None) -> None:
        self._repo = repo
        self._model_client_factory = model_client_factory
        self.company_products: list[CompanyProduct] = []
        self.tasks: dict[str, TaskRecord] = {}
        self._state_machines: dict[str, RunStateMachine] = {}
        self._threads: dict[str, Thread] = {}
        self._lock = RLock()
        if repo:
            self._load_company_products()

    def _load_company_products(self) -> None:
        if self._repo is None:
            return
        rows = self._repo.get_company_products()
        self.company_products = [
            CompanyProduct(
                code=r["company_code"],
                name=r["company_name"],
                brand=r["brand"],
                spec=r["spec"],
                unit=r["unit"],
                package=r["package"],
            )
            for r in rows
        ]

    def replace_company_products(self, products: list[CompanyProduct]) -> int:
        self.company_products = products
        if self._repo:
            catalog_id = uuid4().hex
            self._repo.replace_company_products(
                catalog_version_id=catalog_id,
                file_name="我司商品库.xlsx",
                file_path="",
                products=[
                    {
                        "code": p.code,
                        "name": p.name,
                        "brand": p.brand,
                        "spec": p.spec,
                        "unit": p.unit,
                        "package": p.package,
                        "extra_fields": p.extra_fields,
                    }
                    for p in products
                ],
                file_hash=catalog_id,
            )
            self._repo.log_action("company_catalog_updated", target_type="catalog",
                                  target_id=catalog_id, message=f"导入我司商品库 {len(products)} 条")
        return len(products)

    def create_task(self, customer_items: list[CustomerItem]) -> TaskRecord:
        task_id = uuid4().hex
        task = TaskRecord(task_id=task_id, customer_items=customer_items)
        self.tasks[task_id] = task
        if self._repo:
            self._repo.insert_task(task_id, f"对照任务_{task_id[:8]}", "客户商品库.xlsx", "")
            rows = [
                {
                    "task_row_id": item.row_id,
                    "task_id": task_id,
                    "original_row_number": item.original_row_index,
                    "raw_row_json": "",
                    "customer_name": str(item.fields.get("商品名称", "")),
                    "customer_spec": str(item.fields.get("规格", "")),
                    "customer_unit": str(item.fields.get("单位", "")),
                    "customer_brand": str(item.fields.get("品牌", "")),
                    "customer_note": str(item.fields.get("备注", "")),
                }
                for item in customer_items
            ]
            self._repo.insert_task_rows(rows)
            self._repo.log_action("task_created", target_type="task", target_id=task_id,
                                  message=f"新建对照任务 {len(customer_items)} 条")
        return task

    def create_manual_task(self, payload: dict) -> TaskRecord:
        fields = _manual_fields_from_payload(payload)
        if not fields["商品名称"].strip():
            raise ValueError("商品名称不能为空")

        task_id = uuid4().hex
        item = CustomerItem(row_id="manual-1", original_row_index=2, fields=fields)
        task = TaskRecord(task_id=task_id, customer_items=[item])
        self.tasks[task_id] = task
        if self._repo:
            self._repo.insert_task(task_id, f"手工单品_{task_id[:8]}", "手工输入", "")
            self._repo.insert_task_rows([{
                "task_row_id": item.row_id,
                "task_id": task_id,
                "original_row_number": item.original_row_index,
                "raw_row_json": "",
                "customer_name": fields["商品名称"],
                "customer_spec": fields["规格"],
                "customer_unit": fields["单位"],
                "customer_brand": fields["品牌"],
                "customer_note": fields["备注"],
            }])
            self._repo.log_action("manual_task_created", target_type="task", target_id=task_id,
                                  message=f"手工新建单品任务: {fields['商品名称']}")
        return task

    def _get_model_client(self):
        if self._model_client_factory is not None:
            client = self._model_client_factory()
            if client is not None:
                return client
        raise RuntimeError("模型未配置，请先在初始化配置中填写 API Key 并测试连接")

    def start_task(self, task_id: str) -> TaskRecord:
        task = self.get_task(task_id)
        self._ensure_ready_to_start(task)
        existing = self._state_machines.get(task_id)
        if existing and not existing.is_terminal:
            return task

        run_id = uuid4().hex
        state_machine = RunStateMachine()
        state_machine.on_status_change = self._status_callback(task_id, run_id)
        task.current_run_id = run_id
        task.partial_metrics = RunMetrics(total_count=len(task.customer_items), auto_code_count=0)
        task.status = "running"
        self._state_machines[task_id] = state_machine
        if self._repo:
            self._repo.update_task_status(task_id, "running")
            self._repo.insert_run(run_id, task_id, round_no=1,
                                  total_count=len(task.customer_items))
        state_machine.start()

        thread = Thread(
            target=self._execute_task_run,
            args=(task_id, run_id, state_machine, 1),
            daemon=True,
        )
        self._threads[task_id] = thread
        thread.start()
        return task

    def _execute_task_run(
        self,
        task_id: str,
        run_id: str,
        state_machine: RunStateMachine,
        round_no: int,
    ) -> None:
        task = self.get_task(task_id)
        try:
            model = self._get_model_client()
            result = MatchRunEngine(model_client=model).run_full(
                task.customer_items,
                self.company_products,
                state_machine=state_machine,
                progress_callback=self._progress_callback(task_id, run_id),
            )
            with self._lock:
                task.result = result
                task.partial_metrics = result.metrics
            if self._repo:
                self._repo.update_run_metrics(run_id, task.result.metrics)
                self._repo.insert_run_results(run_id, task.result)
            if state_machine.status == RunStatus.STOPPING:
                state_machine.confirm_stopped()
                if self._repo:
                    self._repo.log_action("task_stopped", target_type="task", target_id=task_id,
                                          message="任务已停止")
                return

            state_machine.mark_completed()
            if self._repo:
                self._repo.log_action("task_completed", target_type="task", target_id=task_id,
                                      message=f"任务完成: 自动落码 {task.result.metrics.auto_code_count} 条")
        except Exception as exc:
            state_machine.mark_failed()
            with self._lock:
                task.status = "failed"
            if self._repo:
                self._repo.update_task_status(task_id, "failed")
                self._repo.update_run_status(run_id, "failed", stopped_reason=str(exc))
                self._repo.log_action("task_failed", target_type="task", target_id=task_id,
                                      message=f"任务失败: {exc}")

    def _status_callback(self, task_id: str, run_id: str):
        def callback(old_status: RunStatus, new_status: RunStatus) -> None:
            with self._lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = new_status.value
            if self._repo:
                self._repo.update_task_status(task_id, new_status.value)
                self._repo.update_run_status(run_id, new_status.value)

        return callback

    def get_task(self, task_id: str) -> TaskRecord:
        try:
            return self.tasks[task_id]
        except KeyError as exc:
            # Try loading from repo
            if self._repo:
                task_data = self._repo.get_task(task_id)
                if task_data:
                    rows = self._repo.get_task_rows(task_id)
                    items = [
                        CustomerItem(
                            row_id=r["task_row_id"],
                            original_row_index=r["original_row_number"],
                            fields={
                                "商品名称": r["customer_name"],
                                "规格": r["customer_spec"],
                                "单位": r["customer_unit"],
                                "品牌": r["customer_brand"],
                                "备注": r["customer_note"],
                            },
                        )
                        for r in rows
                    ]
                    task = TaskRecord(
                        task_id=task_id,
                        customer_items=items,
                        status=task_data["status"],
                        fields_confirmed=self._has_confirmed_field_mappings(task_id),
                    )
                    task.result = self._load_latest_completed_result(task_id, items)
                    self.tasks[task_id] = task
                    return task
            raise KeyError(f"任务不存在: {task_id}") from exc

    def pause_task(self, task_id: str) -> TaskRecord:
        sm = self._state_machines.get(task_id)
        if sm is None:
            raise RuntimeError("任务没有正在执行的运行实例")
        sm.request_pause()
        task = self.get_task(task_id)
        return task

    def resume_task(self, task_id: str) -> TaskRecord:
        sm = self._state_machines.get(task_id)
        if sm is None:
            raise RuntimeError("任务没有正在执行的运行实例")
        sm.resume()
        task = self.get_task(task_id)
        return task

    def stop_task(self, task_id: str) -> TaskRecord:
        sm = self._state_machines.get(task_id)
        if sm is None:
            raise RuntimeError("任务没有正在执行的运行实例")
        sm.request_stop()
        task = self.get_task(task_id)
        return task

    def get_task_run_status(self, task_id: str) -> dict:
        sm = self._state_machines.get(task_id)
        task = self.get_task(task_id)
        run_status = sm.status.value if sm else task.status
        can_export = sm.can_export if sm else task.status == "completed" and task.result is not None
        payload: dict = {
            "task_id": task_id,
            "task_status": task.status,
            "run_status": run_status,
            "can_export": can_export,
            "customer_count": len(task.customer_items),
            "fields_confirmed": task.fields_confirmed,
        }
        if task.result:
            payload["metrics"] = asdict(task.result.metrics)
        elif task.partial_metrics:
            payload["metrics"] = asdict(task.partial_metrics)
        return payload

    def _progress_callback(self, task_id: str, run_id: str):
        def callback(row_results: dict[str, MatchResult], round_no: int, total_count: int) -> None:
            metrics = _metrics_from_results(total_count, dict(row_results), total_rounds=round_no)
            with self._lock:
                task = self.tasks.get(task_id)
                if task:
                    task.partial_metrics = metrics
            if self._repo:
                processed_count = len(row_results)
                self._repo.update_run_progress(run_id, processed_count)

        return callback

    def get_field_suggestions(self, task_id: str) -> dict:
        task = self.get_task(task_id)
        customer_headers = _headers_from_items(task.customer_items)
        company_headers = _headers_from_company_products(self.company_products)
        customer = suggest_customer_mapping(customer_headers)
        company = suggest_company_mapping(company_headers)
        missing_required = [
            *[f"客户库缺少{field}" for field in customer.missing_required_fields()],
            *[f"我司库缺少{field}" for field in company.missing_required_fields()],
        ]
        return {
            "task_id": task_id,
            "customer_mappings": customer.to_dicts(),
            "company_mappings": company.to_dicts(),
            "missing_required": missing_required,
            "fields_confirmed": task.fields_confirmed,
            "can_start": task.fields_confirmed and not missing_required,
        }

    def confirm_fields(self, task_id: str, *,
                        customer_mappings: list[dict],
                        company_mappings: list[dict]) -> dict:
        task = self.get_task(task_id)
        if task.status not in ("created",):
            raise ValueError("只能在任务创建后、开始前确认字段")

        required_missing: list[str] = []
        customer_fields = {m["business_field"] for m in customer_mappings if m.get("importance_level") != "ignored"}
        company_fields = {m["business_field"] for m in company_mappings if m.get("importance_level") != "ignored"}
        if "商品名称" not in customer_fields:
            required_missing.append("客户商品名称字段未确认")
        for field_name in ["商品编码", "商品名称"]:
            if field_name not in company_fields:
                required_missing.append(f"我司{field_name}字段未确认")

        if self._repo:
            self._repo.save_field_mappings(task_id, "customer", customer_mappings)
            self._repo.save_field_mappings(task_id, "company", company_mappings)
            self._repo.log_action("fields_confirmed", target_type="task", target_id=task_id,
                                  message="字段确认完成")
        task.fields_confirmed = len(required_missing) == 0

        return {
            "task_id": task_id,
            "confirmed": len(required_missing) == 0,
            "missing_required": required_missing,
            "customer_mappings_count": len(customer_mappings),
            "company_mappings_count": len(company_mappings),
        }

    def get_field_mappings(self, task_id: str) -> list[dict]:
        if self._repo:
            return self._repo.get_field_mappings(task_id)
        return []

    def add_manual_row(self, task_id: str, payload: dict) -> dict:
        task = self.get_task(task_id)
        row_id = f"manual-{len(task.customer_items) + 1}"
        fields = _manual_fields_from_payload(payload)
        if not fields["商品名称"].strip():
            raise ValueError("商品名称不能为空")

        item = CustomerItem(
            row_id=row_id,
            original_row_index=len(task.customer_items) + 2,
            fields=fields,
        )
        task.customer_items.append(item)
        if self._repo:
            self._repo.insert_task_rows([{
                "task_row_id": row_id,
                "task_id": task_id,
                "original_row_number": item.original_row_index,
                "raw_row_json": "",
                "customer_name": fields["商品名称"],
                "customer_spec": fields["规格"],
                "customer_unit": fields["单位"],
                "customer_brand": fields["品牌"],
                "customer_note": fields["备注"],
            }])
        return {"row_id": row_id, "display_text": item.display_text}

    def preview_next_round(self, task_id: str, file_content) -> dict:
        task = self.get_task(task_id)
        company_codes = frozenset(p.code for p in self.company_products)
        result = import_reviewed_excel(file_content, company_codes)
        if result.is_valid:
            task.review_import = result
        return result

    def start_next_round(self, task_id: str) -> TaskRecord:
        task = self.get_task(task_id)
        previous_result = task.result
        if previous_result is None:
            raise RuntimeError("没有上一轮结果，请先完成第一轮")
        if task.review_import is None or not task.review_import.is_valid:
            raise RuntimeError("请先上传并校验人工审核后的 Excel")

        locked_results = _locked_results_from_review(
            task.review_import,
            previous_result,
            self.company_products,
        )
        rerun_items = [
            item for item in task.customer_items
            if item.row_id not in locked_results
        ]
        task.status = "running"
        if self._repo:
            self._repo.update_task_status(task_id, "running")

        model = self._get_model_client()
        merged_results = _as_result_dict(previous_result)
        merged_results.update(locked_results)
        rerun_result = None
        if rerun_items:
            rerun_result = MatchRunEngine(model_client=model).run_full(
                rerun_items,
                self.company_products,
            )
            merged_results.update(rerun_result.row_results)

        task.result = MatchRunResult(
            metrics=_metrics_from_results(len(task.customer_items), merged_results, total_rounds=2),
            audit_entries=previous_result.audit_entries + (rerun_result.audit_entries if rerun_result else []),
            row_results=merged_results,
            customer_items=task.customer_items,
            total_rounds=2,
        )
        task.status = "completed"
        if self._repo:
            self._repo.update_task_status(task_id, "completed")
            run_id = uuid4().hex
            self._repo.insert_run(run_id, task_id, round_no=2,
                                  total_count=len(task.customer_items))
            self._repo.update_run_metrics(run_id, task.result.metrics)
            self._repo.insert_run_results(run_id, task.result)
            self._repo.update_run_status(run_id, "completed")
            self._repo.log_action("next_round_completed", target_type="task", target_id=task_id,
                                  message=f"第二轮完成: 自动落码 {task.result.metrics.auto_code_count} 条")
        return task

    def export_task(self, task_id: str) -> bytes:
        sm = self._state_machines.get(task_id)
        if sm and not sm.can_export:
            raise RuntimeError("本轮尚未完成，不能导出正式 Excel")
        task = self.get_task(task_id)
        if task.result is None:
            raise RuntimeError("任务尚未完成，不能导出")

        stream = BytesIO()
        export_run_result(task.result, stream)
        if self._repo:
            self._repo.log_action("export", target_type="task", target_id=task_id,
                                  message="导出 Excel")
        return stream.getvalue()

    def _ensure_ready_to_start(self, task: TaskRecord) -> None:
        if not self.company_products:
            raise RuntimeError("请先导入我司商品库")
        if not task.fields_confirmed:
            raise RuntimeError("请先完成字段确认，再开始对照")
        self._get_model_client()

    def _has_confirmed_field_mappings(self, task_id: str) -> bool:
        if self._repo is None:
            return False
        mappings = self._repo.get_field_mappings(task_id)
        if not mappings:
            return False
        customer_fields = {
            row["business_field"]
            for row in mappings
            if row["source"] == "customer" and row["importance_level"] != "ignored"
        }
        company_fields = {
            row["business_field"]
            for row in mappings
            if row["source"] == "company" and row["importance_level"] != "ignored"
        }
        return "商品名称" in customer_fields and {"商品编码", "商品名称"}.issubset(company_fields)

    def _load_latest_completed_result(
        self,
        task_id: str,
        customer_items: list[CustomerItem],
    ) -> MatchRunResult | None:
        if self._repo is None:
            return None
        latest_run = self._repo.get_latest_run(task_id)
        if not latest_run or latest_run["status"] != "completed":
            return None
        rows = self._repo.get_run_results(latest_run["run_id"])
        if not rows:
            return None
        products_by_code = {product.code: product for product in self.company_products}
        row_results: dict[str, MatchResult] = {}
        for row in rows:
            product = products_by_code.get(row["selected_company_code"])
            selected = Candidate(product=product, score=100) if product else None
            audit = _json_or_empty_dict(row.get("audit_json", "{}"))
            if row.get("candidates_json"):
                audit.setdefault("candidate_summaries", _json_or_empty_list(row["candidates_json"]))
            row_results[row["task_row_id"]] = MatchResult(
                row_id=row["task_row_id"],
                status=MatchStatus(row["result_status"]),
                selected_candidate=selected,
                reason_summary=row["reason_summary"],
                evidence_summary=row["evidence_summary"],
                risk_summary=row["risk_summary"],
                audit=audit,
            )
        return MatchRunResult(
            metrics=_metrics_from_results(
                len(customer_items),
                row_results,
                total_rounds=int(latest_run.get("round_no", 1)),
            ),
            audit_entries=[],
            row_results=row_results,
            customer_items=customer_items,
            total_rounds=int(latest_run.get("round_no", 1)),
        )


def task_status_payload(task: TaskRecord) -> dict:
    payload: dict = {
        "task_id": task.task_id,
        "status": task.status,
        "customer_count": len(task.customer_items),
    }
    if task.result:
        payload["metrics"] = asdict(task.result.metrics)
    return payload


def _manual_fields_from_payload(payload: dict) -> dict[str, str]:
    return {
        "商品名称": str(payload.get("商品名称", "")),
        "品牌": str(payload.get("品牌", "")),
        "规格": str(payload.get("规格", "")),
        "单位": str(payload.get("单位", "")),
        "类别": str(payload.get("类别", "")),
        "备注": str(payload.get("备注", "")),
        "编号": str(payload.get("编号", "")),
    }


def _headers_from_items(items: list[CustomerItem]) -> list[str]:
    headers: list[str] = []
    for item in items:
        for header in item.fields:
            if header not in headers:
                headers.append(header)
    return headers


def _headers_from_company_products(products: list[CompanyProduct]) -> list[str]:
    headers: list[str] = []
    for product in products:
        for header in product.extra_fields:
            if header not in headers:
                headers.append(header)
    if headers:
        return headers
    return ["商品编码", "商品名称", "品牌", "规格", "单位", "包装"]


def _json_or_empty_dict(value: str) -> dict:
    try:
        parsed = json_loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except ValueError:
        return {}


def _json_or_empty_list(value: str) -> list:
    try:
        parsed = json_loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except ValueError:
        return []


def _as_result_dict(result: MatchRunResult) -> dict[str, MatchResult]:
    if isinstance(result.row_results, dict):
        return dict(result.row_results)
    return {row_result.row_id: row_result for row_result in result.row_results}


def _locked_results_from_review(
    review: ReviewImportResult,
    previous_result: MatchRunResult,
    company_products: list[CompanyProduct],
) -> dict[str, MatchResult]:
    previous = _as_result_dict(previous_result)
    products_by_code = {product.code: product for product in company_products}
    locked: dict[str, MatchResult] = {}

    for row in review.rows:
        row_id = str(row.get("task_row_id", ""))
        review_result = str(row.get("review_result", ""))
        specified_code = str(row.get("specified_code", ""))
        if not row_id or not review_result:
            continue

        if specified_code and specified_code in products_by_code:
            product = products_by_code[specified_code]
            locked[row_id] = MatchResult(
                row_id=row_id,
                status=MatchStatus.SUGGESTED_REVIEW,
                selected_candidate=Candidate(product=product, score=100),
                reason_summary="人工审核已指定我司编码，第二轮不覆盖",
                evidence_summary=f"人工指定编码: {specified_code}",
                risk_summary=str(row.get("review_note", "")),
                audit={"human_review_locked": True},
            )
            continue

        if review_result in ("已确认", "已确认修改"):
            if row_id in previous:
                locked[row_id] = previous[row_id]
            continue

        if review_result in ("无匹配", "需新增"):
            locked[row_id] = MatchResult(
                row_id=row_id,
                status=MatchStatus.NO_RELIABLE_MATCH,
                reason_summary="人工审核确认无可靠匹配",
                evidence_summary=str(row.get("review_note", "")),
                audit={"human_review_locked": True},
            )

    return locked


def _metrics_from_results(
    total_count: int,
    row_results: dict[str, MatchResult],
    *,
    total_rounds: int,
) -> RunMetrics:
    return RunMetrics(
        total_count=total_count,
        auto_code_count=_count_status(row_results, MatchStatus.AUTO_CODE),
        auto_code_with_diff_count=_count_status(row_results, MatchStatus.AUTO_CODE_WITH_DIFFERENCE),
        suggested_review_count=_count_status(row_results, MatchStatus.SUGGESTED_REVIEW),
        manual_review_count=_count_status(row_results, MatchStatus.MANUAL_REVIEW),
        no_reliable_match_count=_count_status(row_results, MatchStatus.NO_RELIABLE_MATCH),
        returned_to_nature_count=0,
        hard_case_count=0,
        total_rounds=total_rounds,
    )


def _count_status(results: dict[str, MatchResult], status: MatchStatus) -> int:
    return sum(1 for result in results.values() if result.status == status)
