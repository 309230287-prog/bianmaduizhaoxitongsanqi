from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import Response

from product_code_mapper.api.settings_store import SettingsStore
from product_code_mapper.api.task_store import InMemoryTaskStore, task_status_payload
from product_code_mapper.excel.importer import (
    ExcelImportError,
    import_company_products,
    import_customer_items,
)


router = APIRouter()

# ═══════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════

@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ═══════════════════════════════════════════════════
# Config — 初始化配置 / 自检 / 诊断
# ═══════════════════════════════════════════════════

@router.get("/config/status")
def config_status(request: Request) -> dict:
    settings = _settings(request).model_settings
    store = _store(request)
    return {
        "model_configured": settings.has_api_key,
        "model_name": settings.model_name,
        "has_company_catalog": len(store.company_products) > 0,
        "company_product_count": len(store.company_products),
        "active_tasks": len(store.tasks),
        "tasks": store.list_task_summaries(),
    }


@router.get("/config/self-check")
def config_self_check(request: Request) -> dict:
    issues: list[str] = []
    settings = _settings(request).model_settings

    if not settings.has_api_key:
        issues.append("API Key 未配置")
    if not settings.model_name.strip():
        issues.append("模型名称未配置")
    if not settings.base_url.strip():
        issues.append("Base URL 未配置")

    # Chinese path check
    test_dir = request.app.state.data_dir
    try:
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "中文路径自检.txt"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
    except OSError as exc:
        issues.append(f"文件读写自检失败: {exc}")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "model_ready": settings.has_api_key,
        "data_dir_writable": True,
    }


@router.get("/diagnostics/status")
def diagnostics_status(request: Request) -> dict:
    store = _store(request)
    settings = _settings(request).model_settings
    return {
        "model_provider": settings.provider,
        "model_name": settings.model_name,
        "model_configured": settings.has_api_key,
        "company_product_count": len(store.company_products),
        "active_task_count": len(store.tasks),
        "tasks": [
            {
                "task_id": tid,
                "status": t.status,
                "customer_count": len(t.customer_items),
            }
            for tid, t in store.tasks.items()
        ],
    }


@router.get("/logs/recent")
def logs_recent(request: Request, limit: int = 100) -> dict[str, list]:
    store = _store(request)
    if store._repo:
        return {"actions": store._repo.list_action_logs(limit)}
    return {"actions": []}


# ═══════════════════════════════════════════════════
# Model Settings
# ═══════════════════════════════════════════════════

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

    import httpx
    url = f"{settings.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.model_name,
        "messages": [{"role": "user", "content": "你好，请回复一个词：OK"}],
        "temperature": 0,
        "max_tokens": 16,
    }
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
        reply = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
        if reply:
            return {"ok": True, "message": f"连接成功，模型回复: {reply[:80]}"}
        return {"ok": False, "message": "连接成功但模型未返回内容"}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "message": f"API 返回错误 ({e.response.status_code}): {str(e)[:100]}"}
    except Exception as e:
        return {"ok": False, "message": f"连接失败: {str(e)[:120]}"}


# ═══════════════════════════════════════════════════
# Company Catalog
# ═══════════════════════════════════════════════════

@router.post("/catalog/company/import")
async def import_company_catalog(request: Request, file: UploadFile) -> dict[str, int]:
    try:
        products = import_company_products(BytesIO(await file.read()))
    except ExcelImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store = _store(request)
    return {"imported_count": store.replace_company_products(products)}


@router.get("/catalog/company/current")
def current_company_catalog(request: Request) -> dict:
    store = _store(request)
    return {
        "product_count": len(store.company_products),
        "sample_products": [
            {"code": p.code, "name": p.name, "brand": p.brand, "spec": p.spec, "unit": p.unit}
            for p in store.company_products[:10]
        ],
    }


# ═══════════════════════════════════════════════════
# Tasks — 创建 / 字段确认 / 手工输入 / 运行 / 导出
# ═══════════════════════════════════════════════════

@router.post("/tasks")
async def create_task(request: Request, file: UploadFile) -> dict[str, str | int]:
    try:
        customer_items = import_customer_items(BytesIO(await file.read()))
    except ExcelImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = _store(request).create_task(customer_items)
    return {
        "task_id": task.task_id,
        "status": task.status,
        "customer_count": len(task.customer_items),
    }


@router.post("/tasks/manual")
async def create_manual_task(request: Request) -> dict[str, str | int]:
    try:
        task = _store(request).create_manual_task(await request.json())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "task_id": task.task_id,
        "status": task.status,
        "customer_count": len(task.customer_items),
    }


@router.get("/tasks/{task_id}")
def get_task(request: Request, task_id: str) -> dict:
    try:
        _store(request).get_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _store(request).get_task_run_status(task_id)


@router.get("/tasks/{task_id}/status")
def get_task_status(request: Request, task_id: str) -> dict:
    try:
        return _store(request).get_task_run_status(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/start")
def start_task(request: Request, task_id: str) -> dict:
    try:
        _store(request).start_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _store(request).get_task_run_status(task_id)


@router.post("/tasks/{task_id}/pause")
def pause_task(request: Request, task_id: str) -> dict:
    try:
        _store(request).pause_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _store(request).get_task_run_status(task_id)


@router.post("/tasks/{task_id}/resume")
def resume_task(request: Request, task_id: str) -> dict:
    try:
        _store(request).resume_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _store(request).get_task_run_status(task_id)


@router.post("/tasks/{task_id}/stop")
def stop_task(request: Request, task_id: str) -> dict:
    try:
        _store(request).stop_task(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _store(request).get_task_run_status(task_id)


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


# ═══════════════════════════════════════════════════
# Field Confirmation
# ═══════════════════════════════════════════════════

@router.post("/tasks/{task_id}/fields/confirm")
async def confirm_task_fields(request: Request, task_id: str) -> dict:
    try:
        payload = await request.json()
        result = _store(request).confirm_fields(
            task_id,
            customer_mappings=payload.get("customer_mappings", []),
            company_mappings=payload.get("company_mappings", []),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/tasks/{task_id}/fields/suggestions")
def get_task_field_suggestions(request: Request, task_id: str) -> dict:
    try:
        return _store(request).get_field_suggestions(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/fields")
def get_task_fields(request: Request, task_id: str) -> dict:
    try:
        mappings = _store(request).get_field_mappings(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"mappings": mappings}


# ═══════════════════════════════════════════════════
# Manual Input
# ═══════════════════════════════════════════════════

@router.post("/tasks/{task_id}/manual-row")
async def add_manual_row(request: Request, task_id: str) -> dict:
    try:
        payload = await request.json()
        row = _store(request).add_manual_row(task_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return row


# ═══════════════════════════════════════════════════
# Next Round — 第二轮回导
# ═══════════════════════════════════════════════════

@router.post("/tasks/{task_id}/next-round/preview")
async def preview_next_round(request: Request, task_id: str, file: UploadFile) -> dict:
    try:
        content = await file.read()
        result = _store(request).preview_next_round(task_id, BytesIO(content))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "confirmed_count": result.confirmed_count,
        "modified_count": result.modified_count,
        "no_match_count": result.no_match_count,
    }


@router.post("/tasks/{task_id}/next-round/start")
def start_next_round(request: Request, task_id: str) -> dict:
    try:
        _store(request).start_next_round(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _store(request).get_task_run_status(task_id)


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

def _store(request: Request) -> InMemoryTaskStore:
    return request.app.state.task_store


def _settings(request: Request) -> SettingsStore:
    return request.app.state.settings_store
