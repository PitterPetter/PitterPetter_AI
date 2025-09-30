# src/app/server.py
from fastapi import FastAPI
from app.api import recommend

def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")
    app.include_router(recommend.router)
    return app

app = create_app()

# 로컬 실행: uvicorn app.server:app --reload
