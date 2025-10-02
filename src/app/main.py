from fastapi import FastAPI
from app.api import recommends

app = FastAPI(title="PitterPetter AI - Reco API")
app.include_router(recommends.router)