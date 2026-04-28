from __future__ import annotations

from dataclasses import dataclass

from product_code_mapper.db.repository import SettingsRepo


@dataclass
class ModelSettings:
    provider: str = "DeepSeek"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    data_dir: str = ""
    export_dir: str = ""

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key.strip())

    def public_payload(self) -> dict[str, str | bool]:
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "has_api_key": self.has_api_key,
            "data_dir": self.data_dir,
            "export_dir": self.export_dir,
        }


class SettingsStore:
    """Persists settings via SettingsRepo (SQLite)."""

    def __init__(self, repo: SettingsRepo | None = None) -> None:
        self._repo = repo
        self.model_settings = ModelSettings()
        if repo:
            self._load_from_repo()

    def _load_from_repo(self) -> None:
        if self._repo is None:
            return
        self.model_settings = ModelSettings(
            provider=self._repo.get("provider", "DeepSeek"),
            model_name=self._repo.get("model_name", "deepseek-chat"),
            base_url=self._repo.get("base_url", "https://api.deepseek.com"),
            api_key=self._repo.get("api_key", ""),
            data_dir=self._repo.get("data_dir", ""),
            export_dir=self._repo.get("export_dir", ""),
        )

    def update_model_settings(self, payload: dict) -> ModelSettings:
        self.model_settings = ModelSettings(
            provider=str(payload.get("provider", self.model_settings.provider)),
            model_name=str(payload.get("model_name", self.model_settings.model_name)),
            base_url=str(payload.get("base_url", self.model_settings.base_url)),
            api_key=str(payload.get("api_key", self.model_settings.api_key)),
            data_dir=str(payload.get("data_dir", self.model_settings.data_dir)),
            export_dir=str(payload.get("export_dir", self.model_settings.export_dir)),
        )
        if self._repo:
            self._repo.set("provider", self.model_settings.provider)
            self._repo.set("model_name", self.model_settings.model_name)
            self._repo.set("base_url", self.model_settings.base_url)
            self._repo.set("api_key", self.model_settings.api_key)
            self._repo.set("data_dir", self.model_settings.data_dir)
            self._repo.set("export_dir", self.model_settings.export_dir)
        return self.model_settings
