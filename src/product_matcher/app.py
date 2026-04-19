from __future__ import annotations

from threading import Thread
from time import perf_counter
from uuid import uuid4
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from product_matcher.models import (
    STANDARD_FIELDS,
    match_results_to_dicts,
    normalized_records_to_dicts,
    preview_to_dict,
)
from product_matcher.paths import PROJECT_ROOT, RUNTIME_DIR
from product_matcher.services.excel_preview import (
    WorkbookPreviewError,
    build_workbook_preview,
    describe_mapping,
    sanitize_mapping,
    suggest_mapping,
)
from product_matcher.services.exporter import build_export_workbook, suggested_export_name
from product_matcher.services.logging_service import (
    ACTION_LOG_FILE,
    APP_LOG_FILE,
    log_action,
    log_exception,
    log_runtime,
)
from product_matcher.services import ai_pipeline
from product_matcher.services import job_status as job_status_service
from product_matcher.services import model_settings as model_settings_service
from product_matcher.services.ai_client import AIClientError
from product_matcher.services.matching import build_match_preview
from product_matcher.services.normalization import (
    BRAND_DICTIONARY_FILE,
    PRODUCT_KEYWORD_FILE,
    build_normalized_samples,
    collect_mapped_values,
    load_brand_dictionary,
    load_product_dictionary,
)
from product_matcher.services.storage import (
    create_upload_session,
    load_mapping_template,
    load_upload_session,
    save_mapping_template,
)
from product_matcher_phase2.model_trial_runner import build_chat_json_model_caller, run_trial_from_files

BASE_DIR = Path(__file__).resolve().parent
PHASE2_TRIAL_INPUT_FILE = PROJECT_ROOT / "samples" / "phase2" / "model_trial_inputs_v0.2.jsonl"
PHASE2_TRIAL_DIAGNOSTICS_FILE = PROJECT_ROOT / "samples" / "phase2" / "model_trial_diagnostics_deepseek_v0.1.md"

app = FastAPI(
    title="商品智能匹配系统 MVP",
    version="0.9.0",
    description="当前版本可完成双 Excel 上传、字段对照、单模型标准化样例、本地候选缩圈、单模型裁决、日志追踪和 Excel 导出。",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

AI_NORMALIZE_LIMIT = 50
NORMALIZE_SAMPLE_LIMIT = 8
MATCH_SAMPLE_LIMIT = 20


@app.on_event("startup")
async def startup_event() -> None:
    log_runtime(
        "INFO",
        "application_started",
        runtime_dir=str(RUNTIME_DIR),
        app_log=str(APP_LOG_FILE),
        action_log=str(ACTION_LOG_FILE),
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = uuid4().hex[:10]
    request.state.request_id = request_id
    started_at = perf_counter()
    try:
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        log_runtime(
            "INFO",
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        log_exception(
            "request_failed",
            exc,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
        )
        raise


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", _build_context())


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/settings/save", response_class=HTMLResponse)
async def save_settings(request: Request) -> HTMLResponse:
    form = await request.form()
    existing_settings = _load_model_settings_or_default()
    try:
        settings = model_settings_service.build_settings_from_form(form, existing_settings)
        saved_settings = model_settings_service.save_model_settings(settings)
        log_action(
            "save_settings",
            request_id=request.state.request_id,
            provider_name=saved_settings["provider_name"],
            production_model_name=saved_settings["production_model_name"],
            api_key_source=saved_settings["api_key_source"],
        )
        context = _build_context(
            settings_success_message="模型配置已保存。",
            model_settings=model_settings_service.describe_model_settings(saved_settings),
        )
    except model_settings_service.ModelSettingsError as exc:
        log_action("save_settings_failed", request_id=request.state.request_id, error=str(exc))
        context = _build_context(
            settings_error_message=str(exc),
            model_settings=_build_settings_preview(form, existing_settings),
        )
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/settings/test", response_class=HTMLResponse)
async def test_settings(request: Request) -> HTMLResponse:
    form = await request.form()
    existing_settings = _load_model_settings_or_default()
    try:
        settings = model_settings_service.build_settings_from_form(form, existing_settings)
        result = model_settings_service.test_model_connection(settings)
        log_action(
            "test_settings",
            request_id=request.state.request_id,
            provider_name=result["provider_name"],
            production_model_name=result["production_model_name"],
        )
        context = _build_context(
            settings_success_message=result["message"],
            model_settings=model_settings_service.describe_model_settings(settings),
        )
    except model_settings_service.ModelSettingsError as exc:
        log_action("test_settings_failed", request_id=request.state.request_id, error=str(exc))
        context = _build_context(
            settings_error_message=str(exc),
            model_settings=_build_settings_preview(form, existing_settings),
        )
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/settings/reset", response_class=HTMLResponse)
async def reset_settings(request: Request) -> HTMLResponse:
    settings = model_settings_service.recommended_model_settings()
    saved_settings = model_settings_service.save_model_settings(settings)
    log_action(
        "reset_settings",
        request_id=request.state.request_id,
        provider_name=saved_settings["provider_name"],
        production_model_name=saved_settings["production_model_name"],
    )
    context = _build_context(
        settings_success_message="模型配置已恢复为推荐值。",
        model_settings=model_settings_service.describe_model_settings(saved_settings),
    )
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/preview", response_class=HTMLResponse)
async def preview_workbooks(
    request: Request,
    action_name: str = Form("preview_upload"),
    company_file: UploadFile = File(...),
    customer_file: UploadFile = File(...),
) -> HTMLResponse:
    try:
        company_content = await company_file.read()
        customer_content = await customer_file.read()
        company_preview = build_workbook_preview(company_file.filename, company_content)
        customer_preview = build_workbook_preview(customer_file.filename, customer_content)
        session_id = create_upload_session(
            company_file.filename,
            company_content,
            customer_file.filename,
            customer_content,
        )

        saved_mapping = load_mapping_template(company_preview, customer_preview)
        if saved_mapping:
            company_mapping, customer_mapping = saved_mapping
            company_mapping = sanitize_mapping(company_preview.columns, "company", company_mapping)
            customer_mapping = sanitize_mapping(customer_preview.columns, "customer", customer_mapping)
            mapping_hint = "已自动套用最近一次同结构 Excel 的字段对照。"
        else:
            company_mapping = suggest_mapping(company_preview.columns, "company")
            customer_mapping = suggest_mapping(customer_preview.columns, "customer")
            mapping_hint = "已根据表头自动给出字段建议，你可以继续调整后再执行。"

        log_action(
            action_name,
            request_id=request.state.request_id,
            session_id=session_id,
            company_filename=company_file.filename,
            customer_filename=customer_file.filename,
            company_total_rows=company_preview.total_rows,
            customer_total_rows=customer_preview.total_rows,
            company_suggested_mapping=describe_mapping(company_preview.columns, company_mapping),
            customer_suggested_mapping=describe_mapping(customer_preview.columns, customer_mapping),
        )

        context = _build_context(
            company_preview=preview_to_dict(company_preview),
            customer_preview=preview_to_dict(customer_preview),
            session_id=session_id,
            company_mapping=company_mapping,
            customer_mapping=customer_mapping,
            mapping_hint=mapping_hint,
        )
    except WorkbookPreviewError as exc:
        log_exception("preview_failed", exc, request_id=request.state.request_id)
        context = _build_context(error_message=str(exc))
    finally:
        await company_file.close()
        await customer_file.close()

    return templates.TemplateResponse(request, "index.html", context)


@app.post("/normalize", response_class=HTMLResponse)
async def normalize_preview(
    request: Request,
    action_name: str = Form("normalize"),
    session_id: str = Form(...),
    company_filename: str = Form(...),
    customer_filename: str = Form(...),
) -> HTMLResponse:
    try:
        form = await request.form()
        context = _build_preview_context(request, action_name, session_id, company_filename, customer_filename, form)
    except (WorkbookPreviewError, FileNotFoundError) as exc:
        log_exception("normalize_failed", exc, request_id=request.state.request_id, session_id=session_id)
        context = _build_context(error_message=str(exc))

    return templates.TemplateResponse(request, "index.html", context)


@app.post("/match", response_class=HTMLResponse)
async def match_preview(
    request: Request,
    action_name: str = Form("match"),
    session_id: str = Form(...),
    company_filename: str = Form(...),
    customer_filename: str = Form(...),
) -> HTMLResponse:
    try:
        form = await request.form()
        context = _build_preview_context(request, action_name, session_id, company_filename, customer_filename, form)
        company_records, customer_records, runtime_settings, runtime_warning = _build_records(
            session_id,
            context,
            company_limit=50000,
            customer_limit=MATCH_SAMPLE_LIMIT,
        )
        match_results, engine_message, engine_fallback = _build_match_results(
            customer_records,
            company_records,
            runtime_settings,
        )
        context["match_results"] = match_results_to_dicts(match_results)
        context["match_summary"] = _build_match_summary(match_results)
        context["match_engine_message"] = engine_message
        context["match_engine_fallback"] = engine_fallback
        if runtime_warning and not runtime_settings:
            context["pipeline_status_message"] = f"当前未启用生产模型，匹配已回退到本地逻辑：{runtime_warning}"
            context["pipeline_ready"] = False
        log_action(
            action_name,
            request_id=request.state.request_id,
            session_id=session_id,
            summary=context["match_summary"],
            match_engine_message=engine_message,
            pipeline_mode="fallback" if engine_fallback else "single_model",
        )
    except (WorkbookPreviewError, FileNotFoundError) as exc:
        log_exception("match_failed", exc, request_id=request.state.request_id, session_id=session_id)
        context = _build_context(error_message=str(exc))

    return templates.TemplateResponse(request, "index.html", context)


@app.post("/export", response_class=HTMLResponse)
async def export_results(
    request: Request,
    action_name: str = Form("export"),
    session_id: str = Form(...),
    company_filename: str = Form(...),
    customer_filename: str = Form(...),
) -> HTMLResponse:
    form = await request.form()
    context = _build_preview_context(request, action_name, session_id, company_filename, customer_filename, form)
    export_job = job_status_service.create_job(
        "export",
        {
            "session_id": session_id,
            "company_filename": company_filename,
            "customer_filename": customer_filename,
        },
    )
    _start_export_job(
        export_job["job_id"],
        request.state.request_id,
        session_id,
        customer_filename,
        {
            "company_mapping": dict(context["company_mapping"]),
            "customer_mapping": dict(context["customer_mapping"]),
        },
    )
    log_action(
        action_name,
        request_id=request.state.request_id,
        session_id=session_id,
        export_job_id=export_job["job_id"],
        job_status=export_job["status"],
    )
    context["export_job"] = export_job
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/phase2/trial", response_class=HTMLResponse)
async def start_phase2_trial(
    request: Request,
    sample_limit: int = Form(3),
) -> HTMLResponse:
    sample_limit = _normalize_phase2_sample_limit(sample_limit)
    phase2_job = job_status_service.create_job(
        "phase2_model_trial",
        {
            "input_file": str(PHASE2_TRIAL_INPUT_FILE),
            "sample_limit": sample_limit,
        },
    )
    _start_phase2_trial_job(phase2_job["job_id"], request.state.request_id, sample_limit)
    log_action(
        "phase2_trial_started",
        request_id=request.state.request_id,
        phase2_trial_job_id=phase2_job["job_id"],
        sample_limit=sample_limit,
    )
    context = _build_context(
        phase2_trial_job=phase2_job,
        phase2_trial_message="二期语义试跑任务已创建，页面会自动刷新进度。",
    )
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JSONResponse:
    try:
        payload = job_status_service.load_job(job_id)
    except FileNotFoundError:
        return JSONResponse({"error": "未找到任务。"}, status_code=404)
    return JSONResponse(payload)


@app.get("/export/download/{job_id}")
async def download_export_file(job_id: str) -> Response:
    payload = job_status_service.load_job(job_id)
    if payload.get("status") != "completed":
        return Response(content="导出任务尚未完成。", status_code=409)

    output_path = Path(str(payload.get("output_path", "")).strip())
    if not output_path.exists():
        return Response(content="导出文件不存在。", status_code=404)

    filename = str(payload.get("output_filename", "")).strip() or output_path.name
    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
    }
    return Response(
        content=output_path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@app.get("/phase2/trial/download/{job_id}")
async def download_phase2_trial_file(job_id: str) -> Response:
    payload = job_status_service.load_job(job_id)
    if payload.get("job_type") != "phase2_model_trial":
        return Response(content="不是二期语义试跑任务。", status_code=404)
    if payload.get("status") != "completed":
        return Response(content="二期语义试跑任务尚未完成。", status_code=409)

    output_path = Path(str(payload.get("output_path", "")).strip())
    if not output_path.exists():
        return Response(content="二期语义试跑结果文件不存在。", status_code=404)

    filename = str(payload.get("output_filename", "")).strip() or output_path.name
    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
    }
    return Response(
        content=output_path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )



def _build_records(
    session_id: str,
    context: dict,
    company_limit: int,
    customer_limit: int,
):
    session = load_upload_session(session_id)
    brand_dictionary = _load_brand_dictionary(session, context)
    product_dictionary = _load_product_dictionary()
    runtime_settings, runtime_warning = _resolve_runtime_settings_for_pipeline()
    cache_dir = session["session_dir"] / "cache"

    company_records = _build_configured_normalized_samples(
        session["company_path"],
        context["company_mapping"],
        source_type="company",
        brand_dictionary=brand_dictionary,
        product_dictionary=product_dictionary,
        limit=company_limit,
        runtime_settings=runtime_settings,
        cache_dir=cache_dir,
        force_ai=False,
    )
    customer_records = _build_configured_normalized_samples(
        session["customer_path"],
        context["customer_mapping"],
        source_type="customer",
        brand_dictionary=brand_dictionary,
        product_dictionary=product_dictionary,
        limit=customer_limit,
        runtime_settings=runtime_settings,
        cache_dir=cache_dir,
        force_ai=bool(runtime_settings) and customer_limit <= AI_NORMALIZE_LIMIT,
    )
    return company_records, customer_records, runtime_settings, runtime_warning



def _build_preview_context(
    request: Request,
    action_name: str,
    session_id: str,
    company_filename: str,
    customer_filename: str,
    form,
) -> dict:
    session = load_upload_session(session_id)
    company_preview_obj = build_workbook_preview(company_filename, session["company_path"].read_bytes())
    customer_preview_obj = build_workbook_preview(customer_filename, session["customer_path"].read_bytes())
    submitted_company_mapping = _extract_mapping(form, "company")
    submitted_customer_mapping = _extract_mapping(form, "customer")
    company_mapping = sanitize_mapping(company_preview_obj.columns, "company", submitted_company_mapping)
    customer_mapping = sanitize_mapping(customer_preview_obj.columns, "customer", submitted_customer_mapping)
    save_mapping_template(company_preview_obj, customer_preview_obj, company_mapping, customer_mapping)

    log_action(
        action_name,
        request_id=request.state.request_id,
        session_id=session_id,
        company_filename=company_filename,
        customer_filename=customer_filename,
        submitted_company_mapping=describe_mapping(company_preview_obj.columns, submitted_company_mapping),
        submitted_customer_mapping=describe_mapping(customer_preview_obj.columns, submitted_customer_mapping),
        effective_company_mapping=describe_mapping(company_preview_obj.columns, company_mapping),
        effective_customer_mapping=describe_mapping(customer_preview_obj.columns, customer_mapping),
    )

    brand_dictionary = _load_brand_dictionary(session, {"company_mapping": company_mapping, "customer_mapping": customer_mapping})
    product_dictionary = _load_product_dictionary()
    runtime_settings, runtime_warning = _resolve_runtime_settings_for_pipeline()
    cache_dir = session["session_dir"] / "cache"

    company_normalized = _build_configured_normalized_samples(
        session["company_path"],
        company_mapping,
        source_type="company",
        brand_dictionary=brand_dictionary,
        product_dictionary=product_dictionary,
        limit=NORMALIZE_SAMPLE_LIMIT,
        runtime_settings=runtime_settings,
        cache_dir=cache_dir,
        force_ai=bool(runtime_settings),
    )
    customer_normalized = _build_configured_normalized_samples(
        session["customer_path"],
        customer_mapping,
        source_type="customer",
        brand_dictionary=brand_dictionary,
        product_dictionary=product_dictionary,
        limit=NORMALIZE_SAMPLE_LIMIT,
        runtime_settings=runtime_settings,
        cache_dir=cache_dir,
        force_ai=bool(runtime_settings),
    )
    return _build_context(
        company_preview=preview_to_dict(company_preview_obj),
        customer_preview=preview_to_dict(customer_preview_obj),
        session_id=session_id,
        company_mapping=company_mapping,
        customer_mapping=customer_mapping,
        company_normalized=normalized_records_to_dicts(company_normalized),
        customer_normalized=normalized_records_to_dicts(customer_normalized),
        mapping_hint="当前字段对照已保存，后续上传相同结构的 Excel 会自动复用。",
        pipeline_status_message=(
            f"当前已启用生产模型：{runtime_settings['production_model_name']}。标准化样例会优先走单模型链路。"
            if runtime_settings
            else f"当前未启用生产模型，标准化样例已回退到本地解析：{runtime_warning}"
        ),
        pipeline_ready=bool(runtime_settings),
    )


def _load_brand_dictionary(session: dict, context: dict) -> set[str]:
    company_brands = collect_mapped_values(session["company_path"], context["company_mapping"], "brand", limit=50000)
    customer_brands = collect_mapped_values(session["customer_path"], context["customer_mapping"], "brand", limit=50000)
    return load_brand_dictionary(company_brands, customer_brands)


def _load_product_dictionary() -> dict[str, str]:
    return load_product_dictionary()



def _build_match_summary(match_results) -> dict[str, int]:
    summary = {
        "total": len(match_results),
        "auto_matched": 0,
        "suggested": 0,
        "manual_review": 0,
        "unmatched": 0,
    }
    for item in match_results:
        summary[item.match_status] = summary.get(item.match_status, 0) + 1
    return summary



def _build_context(**overrides):
    settings_payload = overrides.pop("model_settings", None)
    settings_warning = None
    if settings_payload is None:
        settings_payload, settings_warning = _load_model_settings_summary()
    pipeline_status_message = overrides.pop("pipeline_status_message", None)
    pipeline_ready = overrides.pop("pipeline_ready", None)
    if pipeline_status_message is None or pipeline_ready is None:
        runtime_settings, runtime_warning = _resolve_runtime_settings_for_pipeline()
        if pipeline_status_message is None:
            if runtime_settings:
                pipeline_status_message = (
                    f"当前已启用生产模型：{runtime_settings['production_model_name']}。"
                    "标准化样例和匹配裁决会优先走单模型主链路。"
                )
            else:
                pipeline_status_message = f"当前未启用生产模型，系统会回退到本地逻辑：{runtime_warning}"
        if pipeline_ready is None:
            pipeline_ready = bool(runtime_settings)

    base = {
        "company_preview": None,
        "customer_preview": None,
        "standard_fields": STANDARD_FIELDS,
        "error_message": None,
        "session_id": None,
        "company_mapping": {},
        "customer_mapping": {},
        "company_normalized": None,
        "customer_normalized": None,
        "match_results": None,
        "match_summary": None,
        "mapping_hint": None,
        "brand_dictionary_path": str(BRAND_DICTIONARY_FILE),
        "product_dictionary_path": str(PRODUCT_KEYWORD_FILE),
        "app_log_path": str(APP_LOG_FILE),
        "action_log_path": str(ACTION_LOG_FILE),
        "model_settings": settings_payload,
        "settings_warning_message": settings_warning,
        "settings_error_message": None,
        "settings_success_message": None,
        "pipeline_status_message": pipeline_status_message,
        "pipeline_ready": pipeline_ready,
        "match_engine_message": None,
        "match_engine_fallback": None,
        "export_job": None,
        "phase2_trial_input_path": str(PHASE2_TRIAL_INPUT_FILE),
        "phase2_trial_diagnostics": _load_phase2_trial_diagnostics_summary(),
        "phase2_trial_job": None,
        "phase2_trial_message": None,
    }
    base.update(overrides)
    return base



def _extract_mapping(form, prefix: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field in STANDARD_FIELDS:
        value = form.get(f"{prefix}_{field.key}", "")
        mapping[field.key] = str(value) if value else ""
    return mapping


def _load_model_settings_or_default() -> dict:
    try:
        return model_settings_service.load_model_settings()
    except model_settings_service.ModelSettingsError:
        return model_settings_service.recommended_model_settings()


def _load_model_settings_summary() -> tuple[dict, str | None]:
    try:
        settings = model_settings_service.load_model_settings()
        return model_settings_service.describe_model_settings(settings), None
    except model_settings_service.ModelSettingsError as exc:
        fallback = model_settings_service.recommended_model_settings()
        return model_settings_service.describe_model_settings(fallback), str(exc)


def _load_phase2_trial_diagnostics_summary() -> dict:
    summary = {
        "available": False,
        "title": "最近二期诊断",
        "source_path": str(PHASE2_TRIAL_DIAGNOSTICS_FILE),
        "source_label": PHASE2_TRIAL_DIAGNOSTICS_FILE.name,
        "total_count": None,
        "schema_validation_error": None,
        "business_rule_validation_error": None,
        "schema_valid_after_normalization": None,
        "model_call_error": None,
        "status_match_count": None,
        "selected_code_mismatch_count": None,
        "unsafe_auto_code_count": None,
        "current_parser_valid_count": None,
        "current_status_match_count": None,
        "current_selected_code_match_count": None,
        "current_selected_code_mismatch_count": None,
        "current_unsafe_auto_code_count": None,
        "note": "该报告说明模型试跑未通过，不代表模型验证成功。",
    }
    if not PHASE2_TRIAL_DIAGNOSTICS_FILE.exists():
        return summary

    try:
        text = PHASE2_TRIAL_DIAGNOSTICS_FILE.read_text(encoding="utf-8")
    except OSError:
        return summary

    summary["available"] = True
    summary["total_count"] = _extract_markdown_int(text, "- Total rows: ")
    summary["schema_validation_error"] = _extract_markdown_int(text, "- `schema_validation_error`: ")
    summary["business_rule_validation_error"] = _extract_markdown_int(
        text,
        "- `business_rule_validation_error`: ",
    )
    summary["schema_valid_after_normalization"] = _extract_markdown_int(
        text,
        "- `schema_valid_after_normalization`: ",
    )
    summary["model_call_error"] = _extract_markdown_int(text, "- `model_call_error`: ")
    summary["status_match_count"] = _extract_markdown_int(text, "- `status_match_count`: ")
    summary["selected_code_mismatch_count"] = _extract_markdown_int(
        text,
        "- `selected_code_mismatch_count`: ",
    )
    summary["unsafe_auto_code_count"] = _extract_markdown_int(text, "- `unsafe_auto_code_count`: ")
    summary["current_parser_valid_count"] = _extract_markdown_int(
        text,
        "- `current_parser_valid_count`: ",
    )
    summary["current_status_match_count"] = _extract_markdown_int(
        text,
        "- `current_status_match_count`: ",
    )
    summary["current_selected_code_match_count"] = _extract_markdown_int(
        text,
        "- `current_selected_code_match_count`: ",
    )
    summary["current_selected_code_mismatch_count"] = _extract_markdown_int(
        text,
        "- `current_selected_code_mismatch_count`: ",
    )
    summary["current_unsafe_auto_code_count"] = _extract_markdown_int(
        text,
        "- `current_unsafe_auto_code_count`: ",
    )
    return summary


def _extract_markdown_int(text: str, prefix: str) -> int | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _build_settings_preview(form, existing_settings: dict) -> dict:
    preview = model_settings_service.recommended_model_settings()
    preview.update(existing_settings)
    preview["provider_name"] = str(form.get("provider_name", preview["provider_name"])).strip() or preview["provider_name"]
    preview["base_url"] = str(form.get("base_url", preview["base_url"])).strip() or preview["base_url"]
    preview["production_model_name"] = (
        str(form.get("production_model_name", preview["production_model_name"])).strip() or preview["production_model_name"]
    )
    preview["api_key_source"] = str(form.get("api_key_source", preview["api_key_source"])).strip() or preview["api_key_source"]
    preview["api_key_env_name"] = (
        str(form.get("api_key_env_name", preview["api_key_env_name"])).strip() or preview["api_key_env_name"]
    )
    preview["timeout_seconds"] = str(form.get("timeout_seconds", preview["timeout_seconds"])).strip() or preview["timeout_seconds"]
    preview["max_retries"] = str(form.get("max_retries", preview["max_retries"])).strip() or preview["max_retries"]
    if preview["api_key_source"] == "local_config":
        preview["api_key_value"] = str(existing_settings.get("api_key_value", "")).strip()
    else:
        preview["api_key_value"] = ""
    return model_settings_service.describe_model_settings(preview)


def _resolve_runtime_settings_for_pipeline() -> tuple[dict | None, str | None]:
    settings = _load_model_settings_or_default()
    try:
        return model_settings_service.resolve_runtime_settings(settings), None
    except model_settings_service.ModelSettingsError as exc:
        return None, str(exc)


def _build_configured_normalized_samples(
    workbook_path,
    mapping: dict[str, str],
    source_type: str,
    brand_dictionary: set[str],
    product_dictionary: dict[str, str],
    *,
    limit: int,
    runtime_settings: dict | None,
    cache_dir,
    force_ai: bool = False,
):
    if runtime_settings and (force_ai or limit <= AI_NORMALIZE_LIMIT):
        try:
            return ai_pipeline.build_ai_normalized_samples(
                workbook_path,
                mapping,
                source_type,
                runtime_settings,
                brand_dictionary,
                product_dictionary,
                limit=limit,
                cache_dir=cache_dir,
            )
        except AIClientError:
            pass

    return build_normalized_samples(
        workbook_path,
        mapping,
        source_type=source_type,
        brand_dictionary=brand_dictionary,
        product_dictionary=product_dictionary,
        limit=limit,
    )


def _build_match_results(
    customer_records,
    company_records,
    runtime_settings: dict | None,
    *,
    candidate_limit: int = 3,
    progress_callback=None,
):
    if runtime_settings:
        try:
            return (
                ai_pipeline.build_ai_match_preview(
                    customer_records,
                    company_records,
                    runtime_settings,
                    candidate_limit=candidate_limit,
                    progress_callback=progress_callback,
                ),
                f"当前链路：本地候选召回 + {runtime_settings['production_model_name']} 裁决。",
                False,
            )
        except AIClientError as exc:
            return (
                build_match_preview(customer_records, company_records, candidate_limit=candidate_limit),
                f"模型裁决失败，已回退到本地匹配：{exc}",
                True,
            )

    return (
        build_match_preview(customer_records, company_records, candidate_limit=candidate_limit),
        "当前未启用生产模型，已回退到本地匹配。",
        True,
    )


def _start_export_job(
    job_id: str,
    request_id: str,
    session_id: str,
    customer_filename: str,
    mapping_context: dict,
) -> None:
    worker = Thread(
        target=_run_export_job,
        args=(job_id, request_id, session_id, customer_filename, mapping_context),
        daemon=True,
    )
    worker.start()


def _run_export_job(
    job_id: str,
    request_id: str,
    session_id: str,
    customer_filename: str,
    mapping_context: dict,
) -> None:
    try:
        job_status_service.update_job(
            job_id,
            status="running",
            progress=3,
            message="正在准备导出任务。",
        )
        company_records, customer_records, runtime_settings, runtime_warning = _build_records(
            session_id,
            mapping_context,
            company_limit=50000,
            customer_limit=50000,
        )
        job_status_service.update_job(
            job_id,
            status="running",
            progress=15,
            message="基础数据已读取，开始执行匹配。",
        )
        match_results, engine_message, engine_fallback = _build_match_results(
            customer_records,
            company_records,
            runtime_settings,
            progress_callback=_build_export_progress_callback(job_id),
        )
        job_status_service.update_job(
            job_id,
            status="running",
            progress=92,
            message="匹配完成，正在生成导出文件。",
        )
        session = load_upload_session(session_id)
        content = build_export_workbook(session["customer_path"], match_results)
        filename = suggested_export_name(customer_filename)
        output_path = job_status_service.save_job_output(job_id, filename, content)
        summary = _build_match_summary(match_results)
        job_status_service.update_job(
            job_id,
            status="completed",
            progress=100,
            message="导出完成，可以下载结果文件了。",
            output_filename=filename,
            output_path=str(output_path),
            summary=summary,
            match_engine_message=engine_message,
            pipeline_mode="fallback" if engine_fallback else "single_model",
        )
        log_action(
            "export_completed",
            request_id=request_id,
            session_id=session_id,
            export_job_id=job_id,
            export_filename=filename,
            summary=summary,
            match_engine_message=engine_message,
            pipeline_mode="fallback" if engine_fallback else "single_model",
            runtime_warning=runtime_warning,
        )
    except Exception as exc:
        job_status_service.update_job(
            job_id,
            status="failed",
            progress=100,
            message=f"导出失败：{exc}",
            error=str(exc),
        )
        log_exception("export_job_failed", exc, request_id=request_id, session_id=session_id, export_job_id=job_id)


def _build_export_progress_callback(job_id: str):
    def callback(completed_batches: int, total_batches: int) -> None:
        if total_batches <= 0:
            progress = 70
        else:
            ratio = completed_batches / total_batches
            progress = 20 + int(ratio * 68)
        job_status_service.update_job(
            job_id,
            status="running",
            progress=min(progress, 90),
            message=f"正在执行模型匹配（{completed_batches}/{total_batches} 批）。",
        )

    return callback


def _normalize_phase2_sample_limit(sample_limit: int) -> int:
    if sample_limit <= 0:
        return 1
    return min(sample_limit, 10)


def _start_phase2_trial_job(job_id: str, request_id: str, sample_limit: int) -> None:
    worker = Thread(
        target=_run_phase2_trial_job,
        args=(job_id, request_id, sample_limit),
        daemon=True,
    )
    worker.start()


def _run_phase2_trial_job(job_id: str, request_id: str, sample_limit: int) -> None:
    try:
        job_status_service.update_job(
            job_id,
            status="running",
            progress=5,
            message="正在准备二期语义试跑。",
        )
        if not PHASE2_TRIAL_INPUT_FILE.exists():
            raise FileNotFoundError(f"未找到二期试跑输入文件：{PHASE2_TRIAL_INPUT_FILE}")

        runtime_settings, runtime_warning = _resolve_runtime_settings_for_pipeline()
        if not runtime_settings:
            raise RuntimeError(f"当前模型不可用：{runtime_warning}")

        job_status_service.update_job(
            job_id,
            status="running",
            progress=15,
            message=f"已启用模型 {runtime_settings['production_model_name']}，开始试跑 {sample_limit} 条样本。",
        )
        output_filename = f"phase2_model_trial_results_{job_id[:8]}.xlsx"
        output_path = job_status_service.EXPORT_OUTPUT_DIR / f"{job_id}_{output_filename}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        model_caller = build_chat_json_model_caller(runtime_settings)
        summary = run_trial_from_files(
            PHASE2_TRIAL_INPUT_FILE,
            output_path,
            model_caller,
            limit=sample_limit,
        )
        job_status_service.update_job(
            job_id,
            status="completed",
            progress=100,
            message="二期语义试跑完成，可以下载结果文件。",
            output_filename=output_filename,
            output_path=str(output_path),
            summary=summary,
            model_name=runtime_settings["production_model_name"],
        )
        log_action(
            "phase2_trial_completed",
            request_id=request_id,
            phase2_trial_job_id=job_id,
            sample_limit=sample_limit,
            summary=summary,
            model_name=runtime_settings["production_model_name"],
        )
    except Exception as exc:
        job_status_service.update_job(
            job_id,
            status="failed",
            progress=100,
            message=f"二期语义试跑失败：{exc}",
            error=str(exc),
        )
        log_exception("phase2_trial_failed", exc, request_id=request_id, phase2_trial_job_id=job_id)
