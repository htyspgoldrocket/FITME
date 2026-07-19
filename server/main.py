"""FITME 백엔드 (FastAPI) — Phase 2.

실행: server/ 디렉토리에서
    venv\\Scripts\\uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analyze import router as analyze_router
from routes.check_photo import router as check_photo_router
from routes.clothing import router as clothing_router
from routes.fit import router as fit_router

app = FastAPI(title="FITME API", version="0.2.0")

# 프론트(Vite dev 서버)에서의 호출 허용.
# 배포·터널 검증 시 필요한 오리진은 그때 협의해 추가한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(check_photo_router)
app.include_router(clothing_router)
app.include_router(fit_router)


@app.get("/health")
def health() -> dict[str, str]:
    """서버 기동 확인용."""
    return {"status": "ok", "phase": "4-4"}
