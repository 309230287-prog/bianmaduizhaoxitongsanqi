from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from product_code_mapper.api.routes import router
from product_code_mapper.model.client import ModelClient
from product_code_mapper.api.settings_store import SettingsStore
from product_code_mapper.api.task_store import InMemoryTaskStore
from product_code_mapper.db.repository import create_repos


def _default_data_dir() -> Path:
    return Path("runtime_data/phase3")


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="商品编码对照系统 三期")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    data_dir = data_dir or _default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "phase3.db"

    settings_repo, task_repo = create_repos(db_path)
    settings_store = SettingsStore(repo=settings_repo)

    def model_client_factory():
        s = settings_store.model_settings
        if s.has_api_key:
            return ModelClient(
                base_url=s.base_url,
                api_key=s.api_key,
                model_name=s.model_name,
            )
        return None  # fallback to FakeModelClient

    app.state.settings_store = settings_store
    app.state.data_dir = data_dir
    app.state.task_store = InMemoryTaskStore(
        repo=task_repo,
        model_client_factory=model_client_factory,
    )
    app.include_router(router)
    return app
