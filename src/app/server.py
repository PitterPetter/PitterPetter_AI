from fastapi import FastAPI
from app.api import recommends, health


def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")

    # ✅ prefix 있는 라우터만 등록
    app.include_router(recommends.router, prefix="/api")
    app.include_router(health.router)

    return app


app = create_app()
