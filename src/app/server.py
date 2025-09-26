# src/app/server.py
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")
    return app
app = create_app()

# 로컬 실행: uvicorn app.server:app --reload
