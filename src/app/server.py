# src/app/server.py
from fastapi import FastAPI
from app.api import recommends
from app.api import health 


def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")
    app.include_router(recommends.router)
    return app

app = create_app()


# 추천 API 라우터
app.include_router(recommends.router, prefix="/api")

# 헬스체크 라우터
app.include_router(health.router)
