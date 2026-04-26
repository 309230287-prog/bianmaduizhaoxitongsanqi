from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelSettings:
    provider: str = "DeepSeek"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key.strip())

    def public_payload(self) -> dict[str, str | bool]:
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "has_api_key": self.has_api_key,
        }


class SettingsStore:
    def __init__(self) -> None:
        self.model_settings = ModelSettings()

    def update_model_settings(self, payload: dict) -> ModelSettings:
        self.model_settings = ModelSettings(
            provider=str(payload.get("provider", self.model_settings.provider)),
            model_name=str(payload.get("model_name", self.model_settings.model_name)),
            base_url=str(payload.get("base_url", self.model_settings.base_url)),
            api_key=str(payload.get("api_key", self.model_settings.api_key)),
        )
        return self.model_settings

