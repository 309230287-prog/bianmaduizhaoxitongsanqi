import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.services import model_settings


class ModelSettingsTests(unittest.TestCase):
    def test_load_model_settings_returns_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings_file = tmp_path / "model_settings.json"
            settings_dir = tmp_path

            with patch.object(model_settings, "MODEL_SETTINGS_FILE", settings_file), \
                 patch.object(model_settings, "MODEL_SETTINGS_DIR", settings_dir):
                loaded = model_settings.load_model_settings()

        self.assertEqual(loaded["provider_name"], "bailian")
        self.assertEqual(loaded["production_model_name"], "qwen-plus")
        self.assertEqual(loaded["api_key_source"], "env")
        self.assertEqual(loaded["model_selection_id"], "auto:recommended")

    def test_save_and_load_model_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings_file = tmp_path / "model_settings.json"
            settings_dir = tmp_path
            payload = {
                "version": 1,
                "model_selection_id": "bailian:qwen-plus",
                "provider_name": "bailian",
                "base_url": "https://example.test/v1",
                "production_model_name": "qwen-plus",
                "api_key_source": "local_config",
                "api_key_env_name": "IGNORED",
                "api_key_value": "sk-local-test",
                "timeout_seconds": 45,
                "max_retries": 3,
            }

            with patch.object(model_settings, "MODEL_SETTINGS_FILE", settings_file), \
                 patch.object(model_settings, "MODEL_SETTINGS_DIR", settings_dir):
                model_settings.save_model_settings(payload)
                loaded = model_settings.load_model_settings()
                saved_payload = json.loads(settings_file.read_text(encoding="utf-8"))

        self.assertEqual(loaded["base_url"], "https://example.test/v1")
        self.assertEqual(loaded["model_selection_id"], "bailian:qwen-plus")
        self.assertEqual(loaded["api_key_source"], "local_config")
        self.assertEqual(loaded["api_key_value"], "sk-local-test")
        self.assertEqual(saved_payload["max_retries"], 3)

    def test_build_settings_from_form_keeps_existing_local_key_when_blank(self) -> None:
        existing = {
            "version": 1,
            "provider_name": "bailian",
            "base_url": "https://example.test/v1",
            "production_model_name": "qwen-plus",
            "api_key_source": "local_config",
            "api_key_env_name": "DASHSCOPE_API_KEY",
            "api_key_value": "sk-existing",
            "timeout_seconds": 60,
            "max_retries": 2,
        }
        form = {
            "provider_name": "bailian",
            "base_url": "https://example.test/v1",
            "production_model_name": "qwen-plus",
            "api_key_source": "local_config",
            "api_key_value": "",
            "timeout_seconds": "60",
            "max_retries": "2",
        }

        built = model_settings.build_settings_from_form(form, existing)
        self.assertEqual(built["api_key_value"], "sk-existing")

    def test_build_settings_from_form_applies_known_model_selection(self) -> None:
        form = {
            "model_selection_id": "bailian:qwen-plus",
            "provider_name": "ignored",
            "base_url": "https://ignored.test/v1",
            "production_model_name": "ignored-model",
            "api_key_source": "env",
            "api_key_env_name": "IGNORED_KEY",
            "api_key_value": "",
            "timeout_seconds": "60",
            "max_retries": "2",
        }

        built = model_settings.build_settings_from_form(form)

        self.assertEqual(built["model_selection_id"], "bailian:qwen-plus")
        self.assertEqual(built["provider_name"], "bailian")
        self.assertEqual(built["base_url"], "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(built["production_model_name"], "qwen-plus")
        self.assertEqual(built["api_key_env_name"], "DASHSCOPE_API_KEY")

    def test_build_settings_from_form_applies_deepseek_model_selection(self) -> None:
        form = {
            "model_selection_id": "deepseek:deepseek-chat",
            "provider_name": "ignored",
            "base_url": "https://ignored.test/v1",
            "production_model_name": "ignored-model",
            "api_key_source": "env",
            "api_key_env_name": "IGNORED_KEY",
            "api_key_value": "",
            "timeout_seconds": "60",
            "max_retries": "2",
        }

        built = model_settings.build_settings_from_form(form)

        self.assertEqual(built["model_selection_id"], "deepseek:deepseek-chat")
        self.assertEqual(built["provider_name"], "deepseek")
        self.assertEqual(built["base_url"], "https://api.deepseek.com")
        self.assertEqual(built["production_model_name"], "deepseek-chat")
        self.assertEqual(built["api_key_env_name"], "DEEPSEEK_API_KEY")


    def test_build_settings_from_form_applies_custom_model_selection(self) -> None:
        form = {
            "model_selection_id": "custom:openai-compatible",
            "provider_name": "ignored",
            "base_url": "https://models.example.test/v1",
            "production_model_name": "semantic-product-model",
            "api_key_source": "env",
            "api_key_env_name": "OPENAI_API_KEY",
            "api_key_value": "",
            "timeout_seconds": "60",
            "max_retries": "2",
        }

        built = model_settings.build_settings_from_form(form)

        self.assertEqual(built["model_selection_id"], "custom:openai-compatible")
        self.assertEqual(built["provider_name"], "openai_compatible")
        self.assertEqual(built["base_url"], "https://models.example.test/v1")
        self.assertEqual(built["production_model_name"], "semantic-product-model")

    def test_build_settings_from_legacy_form_preserves_manual_model_name(self) -> None:
        form = {
            "provider_name": "bailian",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "production_model_name": "qwen-custom-trial",
            "api_key_source": "env",
            "api_key_env_name": "DASHSCOPE_API_KEY",
            "api_key_value": "",
            "timeout_seconds": "60",
            "max_retries": "2",
        }

        built = model_settings.build_settings_from_form(form)

        self.assertEqual(built["model_selection_id"], "bailian:custom")
        self.assertEqual(built["provider_name"], "bailian")
        self.assertEqual(built["production_model_name"], "qwen-custom-trial")

    def test_resolve_runtime_settings_reads_api_key_from_env(self) -> None:
        settings = {
            "version": 1,
            "model_selection_id": "bailian:qwen-plus",
            "provider_name": "bailian",
            "base_url": "https://example.test/v1",
            "production_model_name": "qwen-plus",
            "api_key_source": "env",
            "api_key_env_name": "DASHSCOPE_API_KEY",
            "api_key_value": "",
            "timeout_seconds": 60,
            "max_retries": 2,
        }
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-env-test"}, clear=False):
            runtime = model_settings.resolve_runtime_settings(settings)

        self.assertEqual(runtime["api_key"], "sk-env-test")

    def test_describe_model_settings_exposes_picker_framework(self) -> None:
        description = model_settings.describe_model_settings(
            {
                "version": 1,
                "model_selection_id": "bailian:qwen-plus",
                "provider_name": "bailian",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "production_model_name": "qwen-plus",
                "api_key_source": "env",
                "api_key_env_name": "DASHSCOPE_API_KEY",
                "api_key_value": "",
                "timeout_seconds": 60,
                "max_retries": 2,
            }
        )

        self.assertEqual(description["model_selection_id"], "bailian:qwen-plus")
        self.assertTrue(description["model_picker_groups"])
        self.assertTrue(
            any(
                option["selection_id"] == "bailian:qwen-plus"
                for group in description["model_picker_groups"]
                for option in group["options"]
            )
        )


if __name__ == "__main__":
    unittest.main()
