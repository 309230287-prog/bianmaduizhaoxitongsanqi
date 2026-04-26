from io import BytesIO

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import Response

from product_code_mapper.api.settings_store import SettingsStore
from product_code_mapper.api.task_store import InMemoryTaskStore, task_status_payload
from product_code_mapper.excel.importer import import_company_products, import_customer_items


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings/model")
def get_model_settings(request: Request) -> dict[str, str | bool]:
    return _settings(request).model_settings.public_payload()


@router.put("/settings/model")
async def update_model_settings(request: Request) -> dict[str, str | bool]:
    payload = await request.json()
    settings = _settings(request).update_model_settings(payload)
    return settings.public_payload()


@router.post("/settings/model/test")
def test_model_settings(request: Request) -> dict[str, str | bool]:
    settings = _settings(request).model_settings
    if not settings.has_api_key:
        return {"ok": False, "message": "未配置 API Key，暂时不能连接模型。"}
    return {"ok": True, "message": "模型配置已保存，连接测试将在接入真实模型后启用。"}


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


def _settings(request: Request) -> SettingsStore:
    return request.app.state.settings_store
