from fastapi import FastAPI

from product_code_mapper.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="商品编码对照系统 三期")
    app.include_router(router)
    return app

