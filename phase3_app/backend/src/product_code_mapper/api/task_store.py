from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from uuid import uuid4

from product_code_mapper.domain.models import CompanyProduct, CustomerItem
from product_code_mapper.excel.exporter import export_run_result
from product_code_mapper.model.client import FakeModelClient
from product_code_mapper.runs.engine import MatchRunEngine, MatchRunResult


@dataclass
class TaskRecord:
    task_id: str
    customer_items: list[CustomerItem]
    status: str = "created"
    result: MatchRunResult | None = None


class InMemoryTaskStore:
    def __init__(self) -> None:
        self.company_products: list[CompanyProduct] = []
        self.tasks: dict[str, TaskRecord] = {}

    def replace_company_products(self, products: list[CompanyProduct]) -> int:
        self.company_products = products
        return len(products)

    def create_task(self, customer_items: list[CustomerItem]) -> TaskRecord:
        task_id = uuid4().hex
        task = TaskRecord(task_id=task_id, customer_items=customer_items)
        self.tasks[task_id] = task
        return task

    def start_task(self, task_id: str) -> TaskRecord:
        task = self.get_task(task_id)
        task.status = "running"
        task.result = MatchRunEngine(model_client=FakeModelClient()).run_once(
            task.customer_items,
            self.company_products,
        )
        task.status = "completed"
        return task

    def get_task(self, task_id: str) -> TaskRecord:
        try:
            return self.tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"任务不存在: {task_id}") from exc

    def export_task(self, task_id: str) -> bytes:
        task = self.get_task(task_id)
        if task.result is None:
            raise RuntimeError("任务尚未完成，不能导出")

        stream = BytesIO()
        export_run_result(task.result, stream)
        return stream.getvalue()


def task_status_payload(task: TaskRecord) -> dict:
    payload = {
        "task_id": task.task_id,
        "status": task.status,
        "customer_count": len(task.customer_items),
    }
    if task.result:
        payload["metrics"] = asdict(task.result.metrics)
    return payload

