import json
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import product_matcher.app as app_module
from product_matcher.app import app
from product_matcher.models import NormalizedRecord
from product_matcher.services import job_status, logging_service, model_settings, storage
from product_matcher.services.matching import build_match_preview
from product_matcher.services.normalization import build_normalized_samples


class _FakeUrlOpenResponse:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


class AppFlowTests(unittest.TestCase):
    def test_home_can_save_and_test_model_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings_dir = tmp_path / "settings"
            settings_file = settings_dir / "model_settings.json"
            log_dir = tmp_path / "logs"
            client = TestClient(app)

            with patch.object(model_settings, "MODEL_SETTINGS_DIR", settings_dir), \
                 patch.object(model_settings, "MODEL_SETTINGS_FILE", settings_file), \
                 patch.object(logging_service, "LOG_DIR", log_dir), \
                 patch.object(logging_service, "APP_LOG_FILE", log_dir / "app.log"), \
                 patch.object(logging_service, "ACTION_LOG_FILE", log_dir / "actions.jsonl"):
                home = client.get("/")
                self.assertEqual(home.status_code, 200)
                self.assertIn("模型设置", home.text)
                self.assertIn("模型选择器", home.text)
                self.assertIn('name="model_selection_id"', home.text)
                self.assertIn("bailian:qwen-plus", home.text)
                self.assertIn("data-model-option", home.text)
                self.assertIn("syncModelSelectionFields", home.text)

                save_response = client.post(
                    "/settings/save",
                    data={
                        "model_selection_id": "bailian:qwen-plus",
                        "provider_name": "bailian",
                        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                        "production_model_name": "qwen-plus",
                        "api_key_source": "env",
                        "api_key_env_name": "DASHSCOPE_API_KEY",
                        "api_key_value": "",
                        "timeout_seconds": "60",
                        "max_retries": "2",
                    },
                )
                self.assertEqual(save_response.status_code, 200)
                self.assertIn("模型配置已保存。", save_response.text)
                self.assertIn("bailian:qwen-plus", save_response.text)
                self.assertTrue(settings_file.exists())

                fake_response = _FakeUrlOpenResponse(b'{"id":"ok","choices":[{"message":{"content":"pong"}}]}')
                with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-env-test"}, clear=False), \
                     patch.object(model_settings.urllib_request, "urlopen", return_value=fake_response):
                    test_response = client.post(
                        "/settings/test",
                        data={
                            "model_selection_id": "bailian:qwen-plus",
                            "provider_name": "bailian",
                            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                            "production_model_name": "qwen-plus",
                            "api_key_source": "env",
                            "api_key_env_name": "DASHSCOPE_API_KEY",
                            "api_key_value": "",
                            "timeout_seconds": "60",
                            "max_retries": "2",
                        },
                    )

                self.assertEqual(test_response.status_code, 200)
                self.assertIn("模型连接测试通过。", test_response.text)

    def test_home_shows_recent_phase2_diagnostics_summary(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("最近二期诊断", response.text)
        self.assertIn("schema_validation_error", response.text)
        self.assertIn("schema_valid_after_normalization", response.text)
        self.assertIn("9", response.text)
        self.assertIn("model_call_error", response.text)
        self.assertIn("1", response.text)
        self.assertIn("该报告说明模型试跑未通过，不代表模型验证成功。", response.text)

    def test_home_shows_placeholder_when_phase2_diagnostics_report_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_report = Path(tmp_dir) / "missing.md"
            client = TestClient(app)

            with patch.object(app_module, "PHASE2_TRIAL_DIAGNOSTICS_FILE", missing_report):
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("最近二期诊断", response.text)
        self.assertIn("暂无诊断报告", response.text)

    def test_home_can_save_openai_compatible_model_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings_dir = tmp_path / "settings"
            settings_file = settings_dir / "model_settings.json"
            log_dir = tmp_path / "logs"
            client = TestClient(app)

            with patch.object(model_settings, "MODEL_SETTINGS_DIR", settings_dir), \
                 patch.object(model_settings, "MODEL_SETTINGS_FILE", settings_file), \
                 patch.object(logging_service, "LOG_DIR", log_dir), \
                 patch.object(logging_service, "APP_LOG_FILE", log_dir / "app.log"), \
                 patch.object(logging_service, "ACTION_LOG_FILE", log_dir / "actions.jsonl"):
                save_response = client.post(
                    "/settings/save",
                    data={
                        "model_selection_id": "custom:openai-compatible",
                        "provider_name": "openai_compatible",
                        "base_url": "https://models.example.test/v1",
                        "production_model_name": "semantic-product-model",
                        "api_key_source": "env",
                        "api_key_env_name": "OPENAI_API_KEY",
                        "api_key_value": "",
                        "timeout_seconds": "60",
                        "max_retries": "2",
                    },
                )

        self.assertEqual(save_response.status_code, 200)
        self.assertIn("模型配置已保存。", save_response.text)
        self.assertIn("custom:openai-compatible", save_response.text)
        self.assertIn("OpenAI Compatible", save_response.text)
        self.assertIn("semantic-product-model", save_response.text)

    def test_phase2_trial_runs_from_product_page_and_writes_job_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            trial_input_path = tmp_path / "trial_inputs.jsonl"
            trial_input_path.write_text(
                "\n".join(
                    [
                        '{"sample_id":"GS0001","sample_group":"manual_review","expected_company_code":"","expected_result_status":"manual_review","payload":{"customer_record":{"record_id":"C1"},"candidate_products":[]}}',
                        '{"sample_id":"GS0002","sample_group":"manual_review","expected_company_code":"","expected_result_status":"manual_review","payload":{"customer_record":{"record_id":"C2"},"candidate_products":[]}}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            jobs_dir = tmp_path / "jobs"
            output_dir = tmp_path / "outputs"
            log_dir = tmp_path / "logs"
            client = TestClient(app)
            captured = {}

            def fake_build_caller(runtime_settings):
                captured["runtime_settings"] = runtime_settings
                return lambda payload: {"ok": payload}

            def fake_run_trial(input_path, output_path, model_caller, *, limit=None):
                captured["input_path"] = Path(input_path)
                captured["limit"] = limit
                captured["model_probe"] = model_caller({"probe": True})
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"fake xlsx")
                return {
                    "total_count": 2,
                    "json_valid_count": 2,
                    "json_valid_rate": 1.0,
                    "status_match_count": 1,
                    "status_match_rate": 0.5,
                    "auto_code_count": 0,
                }

            with patch.object(app_module, "PHASE2_TRIAL_INPUT_FILE", trial_input_path), \
                 patch.object(job_status, "JOBS_DIR", jobs_dir), \
                 patch.object(job_status, "EXPORT_OUTPUT_DIR", output_dir), \
                 patch.object(logging_service, "LOG_DIR", log_dir), \
                 patch.object(logging_service, "APP_LOG_FILE", log_dir / "app.log"), \
                 patch.object(logging_service, "ACTION_LOG_FILE", log_dir / "actions.jsonl"), \
                 patch.object(app_module, "_resolve_runtime_settings_for_pipeline", return_value=(
                     {"provider_name": "deepseek", "production_model_name": "deepseek-chat", "api_key": "sk-test"},
                     None,
                 )), \
                 patch.object(app_module, "build_chat_json_model_caller", side_effect=fake_build_caller), \
                 patch.object(app_module, "run_trial_from_files", side_effect=fake_run_trial):
                home = client.get("/")
                self.assertEqual(home.status_code, 200)
                self.assertIn("二期语义工作台", home.text)
                self.assertIn("/phase2/trial", home.text)

                response = client.post("/phase2/trial", data={"sample_limit": "2"})

                self.assertEqual(response.status_code, 200)
                self.assertIn("二期语义试跑任务", response.text)
                job_id = re.search(r'data-phase2-job-id="([^"]+)"', response.text).group(1)

                payload = self._wait_for_phase2_job(jobs_dir, job_id)

                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["summary"]["total_count"], 2)
                self.assertEqual(payload["summary"]["json_valid_count"], 2)
                self.assertEqual(captured["input_path"], trial_input_path)
                self.assertEqual(captured["limit"], 2)
                self.assertEqual(captured["runtime_settings"]["production_model_name"], "deepseek-chat")
                self.assertEqual(captured["model_probe"], {"ok": {"probe": True}})
                self.assertTrue(Path(payload["output_path"]).exists())

                download = client.get(f"/phase2/trial/download/{job_id}")
                self.assertEqual(download.status_code, 200)
                self.assertEqual(download.content, b"fake xlsx")

    def test_match_prefers_ai_pipeline_when_model_runtime_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            uploads_dir = tmp_path / "uploads"
            template_file = tmp_path / "mapping_templates.json"
            log_dir = tmp_path / "logs"
            company_file = tmp_path / "company.xlsx"
            customer_file = tmp_path / "customer.xlsx"
            self._build_company_workbook(company_file)
            self._build_customer_workbook(customer_file)

            client = TestClient(app)
            runtime_settings = {
                "provider_name": "bailian",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "production_model_name": "qwen-plus",
                "api_key": "sk-test",
                "timeout_seconds": 30,
                "max_retries": 1,
            }

            def fake_ai_normalize(
                workbook_path,
                mapping,
                source_type,
                _runtime_settings,
                brand_dictionary,
                product_dictionary,
                *,
                limit=8,
                cache_dir=None,
            ) -> list[NormalizedRecord]:
                records = build_normalized_samples(
                    workbook_path,
                    mapping,
                    source_type=source_type,
                    brand_dictionary=brand_dictionary,
                    product_dictionary=product_dictionary,
                    limit=limit,
                )
                enhanced: list[NormalizedRecord] = []
                for record in records:
                    enhanced.append(
                        NormalizedRecord(
                            source_type=record.source_type,
                            row_no=record.row_no,
                            source_code=record.source_code,
                            source_name=record.source_name,
                            source_brand=record.source_brand,
                            source_spec=record.source_spec,
                            source_unit=record.source_unit,
                            source_category=record.source_category,
                            cleaned_name=record.cleaned_name,
                            parsed_brand=record.parsed_brand,
                            parsed_name=record.parsed_name,
                            parsed_spec=record.parsed_spec,
                            parsed_unit=record.parsed_unit,
                            parsed_category=record.parsed_category,
                            parse_notes=f"模型标准化；{record.parse_notes}".strip("；"),
                        )
                    )
                return enhanced

            def fake_ai_match(
                customer_records,
                company_records,
                _runtime_settings,
                *,
                candidate_limit=3,
                progress_callback=None,
            ):
                results = build_match_preview(customer_records, company_records, candidate_limit=candidate_limit)
                for result in results:
                    result.summary = "模型已完成匹配裁决"
                return results

            with patch.object(storage, "UPLOADS_DIR", uploads_dir), \
                 patch.object(storage, "TEMPLATE_FILE", template_file), \
                 patch.object(logging_service, "LOG_DIR", log_dir), \
                 patch.object(logging_service, "APP_LOG_FILE", log_dir / "app.log"), \
                 patch.object(logging_service, "ACTION_LOG_FILE", log_dir / "actions.jsonl"), \
                 patch.object(app_module.model_settings_service, "resolve_runtime_settings", return_value=runtime_settings), \
                 patch.object(app_module.ai_pipeline, "build_ai_normalized_samples", side_effect=fake_ai_normalize) as mock_ai_normalize, \
                 patch.object(app_module.ai_pipeline, "build_ai_match_preview", side_effect=fake_ai_match) as mock_ai_match:
                with company_file.open("rb") as cf, customer_file.open("rb") as uf:
                    preview = client.post(
                        "/preview",
                        files={
                            "company_file": (
                                "company.xlsx",
                                cf.read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                            "customer_file": (
                                "customer.xlsx",
                                uf.read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                        },
                    )
                self.assertEqual(preview.status_code, 200)

                session_id = re.search(r'name="session_id" value="([^"]+)"', preview.text).group(1)
                company_name = re.search(r'name="company_filename" value="([^"]+)"', preview.text).group(1)
                customer_name = re.search(r'name="customer_filename" value="([^"]+)"', preview.text).group(1)

                form = {
                    "action_name": "normalize",
                    "session_id": session_id,
                    "company_filename": company_name,
                    "customer_filename": customer_name,
                    "company_product_code": "col_1",
                    "customer_product_code": "col_1",
                    "company_product_name": "col_2",
                    "customer_product_name": "col_2",
                    "company_brand": "col_3",
                    "customer_brand": "col_3",
                    "company_spec": "col_4",
                    "customer_spec": "col_4",
                    "company_unit": "col_5",
                    "customer_unit": "col_5",
                    "company_category": "col_6",
                    "customer_category": "col_6",
                }

                normalize = client.post("/normalize", data=form)
                self.assertEqual(normalize.status_code, 200)
                self.assertIn("模型标准化", normalize.text)
                self.assertGreaterEqual(mock_ai_normalize.call_count, 2)

                form["action_name"] = "match"
                match_response = client.post("/match", data=form)
                self.assertEqual(match_response.status_code, 200)
                self.assertIn("模型已完成匹配裁决", match_response.text)
                self.assertIn("qwen-plus", match_response.text)
                self.assertTrue(mock_ai_match.called)

    def test_preview_normalize_match_export_and_template_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            uploads_dir = tmp_path / "uploads"
            template_file = tmp_path / "mapping_templates.json"
            log_dir = tmp_path / "logs"
            jobs_dir = tmp_path / "jobs"
            export_dir = tmp_path / "exports"
            company_file = tmp_path / "company.xlsx"
            customer_file = tmp_path / "customer.xlsx"
            self._build_company_workbook(company_file)
            self._build_customer_workbook(customer_file)

            client = TestClient(app)
            with patch.object(storage, "UPLOADS_DIR", uploads_dir), \
                 patch.object(storage, "TEMPLATE_FILE", template_file), \
                 patch.object(job_status, "JOBS_DIR", jobs_dir), \
                 patch.object(job_status, "EXPORT_OUTPUT_DIR", export_dir), \
                 patch.object(logging_service, "LOG_DIR", log_dir), \
                 patch.object(logging_service, "APP_LOG_FILE", log_dir / "app.log"), \
                 patch.object(logging_service, "ACTION_LOG_FILE", log_dir / "actions.jsonl"):
                with company_file.open("rb") as cf, customer_file.open("rb") as uf:
                    preview = client.post(
                        "/preview",
                        files={
                            "company_file": (
                                "company.xlsx",
                                cf.read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                            "customer_file": (
                                "customer.xlsx",
                                uf.read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                        },
                    )
                self.assertEqual(preview.status_code, 200)
                self.assertIn("字段对照表", preview.text)
                session_id = re.search(r'name="session_id" value="([^"]+)"', preview.text).group(1)
                company_name = re.search(r'name="company_filename" value="([^"]+)"', preview.text).group(1)
                customer_name = re.search(r'name="customer_filename" value="([^"]+)"', preview.text).group(1)

                form = {
                    "action_name": "normalize",
                    "session_id": session_id,
                    "company_filename": company_name,
                    "customer_filename": customer_name,
                    "company_product_code": "col_1",
                    "customer_product_code": "col_1",
                    "company_product_name": "col_2",
                    "customer_product_name": "col_2",
                    "company_brand": "col_3",
                    "customer_brand": "col_3",
                    "company_spec": "col_4",
                    "customer_spec": "col_4",
                    "company_unit": "col_5",
                    "customer_unit": "col_5",
                    "company_category": "col_6",
                    "customer_category": "col_6",
                }

                normalize = client.post("/normalize", data=form)
                self.assertEqual(normalize.status_code, 200)
                self.assertIn("我司标准化样例", normalize.text)

                form["action_name"] = "match"
                match_response = client.post("/match", data=form)
                self.assertEqual(match_response.status_code, 200)
                self.assertIn("初版匹配样例", match_response.text)
                self.assertIn("样例总数", match_response.text)

                form["action_name"] = "export"
                export = client.post("/export", data=form)
                self.assertEqual(export.status_code, 200)
                self.assertIn("导出任务", export.text)
                job_id = re.search(r'data-job-id="([^"]+)"', export.text).group(1)

                payload = self._wait_for_job(client, job_id)
                self.assertEqual(payload["status"], "completed")

                download = client.get(f"/export/download/{job_id}")
                self.assertEqual(download.status_code, 200)
                self.assertIn(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    download.headers["content-type"],
                )
                self.assertGreater(len(download.content), 1000)

                with company_file.open("rb") as cf, customer_file.open("rb") as uf:
                    preview_again = client.post(
                        "/preview",
                        files={
                            "company_file": (
                                "company.xlsx",
                                cf.read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                            "customer_file": (
                                "customer.xlsx",
                                uf.read(),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                        },
                    )
                self.assertEqual(preview_again.status_code, 200)
                self.assertIn("已自动套用最近一次同结构 Excel 的字段对照。", preview_again.text)

                action_log = (log_dir / "actions.jsonl").read_text(encoding="utf-8")
                self.assertIn("preview_upload", action_log)
                self.assertIn("normalize", action_log)
                self.assertIn("match", action_log)
                self.assertIn("export", action_log)
                self.assertIn("export_completed", action_log)
                app_log = (log_dir / "app.log").read_text(encoding="utf-8")
                self.assertIn("request_completed", app_log)

    def _wait_for_job(self, client: TestClient, job_id: str, timeout_seconds: float = 5.0) -> dict:
        deadline = time.time() + timeout_seconds
        last_payload = {}
        while time.time() < deadline:
            response = client.get(f"/jobs/{job_id}")
            self.assertEqual(response.status_code, 200)
            last_payload = response.json()
            if last_payload.get("status") in {"completed", "failed"}:
                return last_payload
            time.sleep(0.1)
        self.fail(f"Job {job_id} did not finish in time: {last_payload}")

    def _wait_for_phase2_job(self, jobs_dir: Path, job_id: str, timeout_seconds: float = 5.0) -> dict:
        deadline = time.time() + timeout_seconds
        job_path = jobs_dir / f"{job_id}.json"
        last_payload = {}
        while time.time() < deadline:
            if job_path.exists():
                last_payload = json.loads(job_path.read_text(encoding="utf-8"))
                if last_payload.get("status") in {"completed", "failed"}:
                    return last_payload
            time.sleep(0.05)
        self.fail(f"Phase2 job {job_id} did not finish in time: {last_payload}")

    def _build_company_workbook(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["SPUID", "SPU名称", "品牌", "规格", "单位", "分类"])
        sheet.append(["C001", "海天酱油", "海天", "500ml", "瓶", "调味品"])
        sheet.append(["C002", "李锦记蚝油", "李锦记", "500g", "瓶", "调味品"])
        workbook.save(path)

    def _build_customer_workbook(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["编号", "商品名称", "品牌", "规格", "单位", "类别"])
        sheet.append(["U001", "海天酱油", "海天", "500ml", "瓶", "调味品"])
        sheet.append(["U002", "李锦记蚝油", "李锦记", "500g", "瓶", "调味品"])
        workbook.save(path)


if __name__ == "__main__":
    unittest.main()
