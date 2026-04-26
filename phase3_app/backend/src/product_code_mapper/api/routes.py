from io import BytesIO

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import Response

from product_code_mapper.api.task_store import InMemoryTaskStore, task_status_payload
from product_code_mapper.excel.importer import import_company_products, import_customer_items


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/catalog/company/import")
async def import_company_catalog(request: Request, file: UploadFile) -> dict[str, int]:
    products = import_company_products(BytesIO(await file.read()))
    store = _store(request)
    return {"imported_count": store.replace_company_products(products)}


@router.post("/tasks")
async def create_task(request: Request, file: UploadFile) -> dict[str, str | int]:
    customer_items = import_customer_items(BytesIO(await file.read()))
    task = _store(request).create_task(customer_items)
    return {
        "task_id": task.task_id,
        "status": task.status,
        "customer_count": len(task.customer_items),
    }


@router.post("/tasks/{task_id}/start")
def start_task(request: Request, task_id: str) -> dict:
    try:
        task = _store(request).start_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return task_status_payload(task)


@router.get("/tasks/{task_id}/status")
def get_task_status(request: Request, task_id: str) -> dict:
    try:
        task = _store(request).get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return task_status_payload(task)


@router.get("/tasks/{task_id}/export")
def export_task(request: Request, task_id: str) -> Response:
    try:
        content = _store(request).export_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="match-result.xlsx"'},
    )


def _store(request: Request) -> InMemoryTaskStore:
    return request.app.state.task_store
