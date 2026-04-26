from fastapi import FastAPI

from product_code_mapper.api.settings_store import SettingsStore
from product_code_mapper.api.task_store import InMemoryTaskStore
from product_code_mapper.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="商品编码对照系统 三期")
    app.state.settings_store = SettingsStore()
    app.state.task_store = InMemoryTaskStore()
    app.include_router(router)
    return app
