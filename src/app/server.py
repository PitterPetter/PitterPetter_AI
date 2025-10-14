from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import recommends, health, replace


def create_app() -> FastAPI:
    app = FastAPI(title="PitterPetter AI - Reco API")

    # ============================================================
    # 🌐 CORS 설정 (프론트 & API 도메인 허용)
    # ============================================================
    allowed_origins = [
        "https://loventure.us",         # 메인 도메인
        "https://www.loventure.us",     # www 서브도메인
        "https://api.loventure.us",     # API 서버 자체 호출
        "http://localhost:5173",        # 로컬 개발용
        "http://127.0.0.1:5173",        # 로컬 개발용
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ============================================================
    # 📦 라우터 등록
    # ============================================================
    app.include_router(recommends.router, prefix="/api")
    app.include_router(health.router)
    app.include_router(replace.router, prefix="/api")

    return app


# ✅ 앱 인스턴스 생성
app = create_app()
