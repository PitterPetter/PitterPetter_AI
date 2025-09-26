# PitterPetter_AI
# AI Service (FastAPI + LangGraph)

## Quickstart
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt 
cp .env.example .env
uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000
