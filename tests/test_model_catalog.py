import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from product_matcher.services.model_catalog import (
    apply_model_selection,
    find_model_option,
    list_model_picker_groups,
)
from product_matcher.services.model_settings import default_model_settings


class ModelCatalogTests(unittest.TestCase):
    def test_model_picker_groups_follow_ide_style_structure(self) -> None:
        groups = list_model_picker_groups()

        labels = [group["label"] for group in groups]
        self.assertIn("Auto 推荐", labels)
        self.assertIn("推荐模型", labels)
        self.assertIn("阿里云百炼", labels)
        self.assertIn("DeepSeek", labels)
        self.assertIn("OpenAI Compatible", labels)
        self.assertIn("自定义模型", labels)

        flat_options = [option for group in groups for option in group["options"]]
        self.assertTrue(any(option["selection_id"] == "bailian:qwen-plus" for option in flat_options))
        self.assertTrue(any(option["selection_id"] == "deepseek:deepseek-chat" for option in flat_options))
        self.assertTrue(any(option["selection_id"] == "custom:openai-compatible" for option in flat_options))

    def test_find_model_option_returns_runtime_defaults(self) -> None:
        option = find_model_option("bailian:qwen-plus")

        self.assertEqual(option.provider_name, "bailian")
        self.assertEqual(option.model_name, "qwen-plus")
        self.assertEqual(option.base_url, "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(option.api_key_env_name, "DASHSCOPE_API_KEY")
        self.assertIn("结构化输出", option.tags)

    def test_find_deepseek_model_option_returns_runtime_defaults(self) -> None:
        option = find_model_option("deepseek:deepseek-chat")

        self.assertEqual(option.provider_name, "deepseek")
        self.assertEqual(option.model_name, "deepseek-chat")
        self.assertEqual(option.base_url, "https://api.deepseek.com")
        self.assertEqual(option.api_key_env_name, "DEEPSEEK_API_KEY")
        self.assertIn("中文语义", option.tags)

    def test_apply_known_model_selection_updates_settings(self) -> None:
        settings = default_model_settings()

        selected = apply_model_selection(settings, "bailian:qwen-plus")

        self.assertEqual(selected["model_selection_id"], "bailian:qwen-plus")
        self.assertEqual(selected["provider_name"], "bailian")
        self.assertEqual(selected["production_model_name"], "qwen-plus")
        self.assertEqual(selected["base_url"], "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(selected["api_key_env_name"], "DASHSCOPE_API_KEY")

    def test_apply_deepseek_model_selection_updates_settings(self) -> None:
        selected = apply_model_selection(default_model_settings(), "deepseek:deepseek-chat")

        self.assertEqual(selected["model_selection_id"], "deepseek:deepseek-chat")
        self.assertEqual(selected["provider_name"], "deepseek")
        self.assertEqual(selected["production_model_name"], "deepseek-chat")
        self.assertEqual(selected["base_url"], "https://api.deepseek.com")
        self.assertEqual(selected["api_key_env_name"], "DEEPSEEK_API_KEY")

    def test_apply_auto_selection_resolves_to_recommended_model(self) -> None:
        selected = apply_model_selection(default_model_settings(), "auto:recommended")

        self.assertEqual(selected["model_selection_id"], "auto:recommended")
        self.assertEqual(selected["provider_name"], "bailian")
        self.assertEqual(selected["production_model_name"], "qwen-plus")

    def test_apply_custom_openai_compatible_selection_uses_explicit_values(self) -> None:
        selected = apply_model_selection(
            default_model_settings(),
            "custom:openai-compatible",
            custom_base_url="https://models.example.test/v1",
            custom_model_name="semantic-product-model",
        )

        self.assertEqual(selected["model_selection_id"], "custom:openai-compatible")
        self.assertEqual(selected["provider_name"], "openai_compatible")
        self.assertEqual(selected["base_url"], "https://models.example.test/v1")
        self.assertEqual(selected["production_model_name"], "semantic-product-model")


if __name__ == "__main__":
    unittest.main()
