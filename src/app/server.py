# src/app/server.py
from fastapi import FastAPI
from app.api import recommend
from app.api import health 


def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")
    app.include_router(recommend.router)
    return app

app = create_app()


# 추천 API 라우터
app.include_router(recommend.router, prefix="/api")

# 헬스체크 라우터
app.include_router(health.router)
