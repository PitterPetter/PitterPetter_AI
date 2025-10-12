from fastapi import FastAPI
from app.api import recommends, health, replace


def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")

    # ✅ prefix 있는 라우터만 등록
    app.include_router(recommends.router, prefix="/api")
    app.include_router(health.router)
    app.include_router(replace.router, prefix="/api")  # replace.py의 router 추가

    return app

app = create_app()
