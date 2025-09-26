from fastapi import FastAPI
from app.api import recommend

app = FastAPI(title="PitterPetter AI - Reco API")
app.include_router(recommend.router)