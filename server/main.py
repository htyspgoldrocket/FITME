"""FITME 백엔드 (FastAPI) — Phase 2.

실행: server/ 디렉토리에서
    venv\\Scripts\\uvicorn main:app --reload --port 8000

배포(6-3a): 프론트 빌드(dist)가 있으면 정적 서빙까지 겸한다(배포 유닛 1개).
프론트는 항상 같은 오리진의 /api/*로 호출하므로 라우터를 /api 프리픽스로도
등록한다. 루트 경로(/analyze 등)는 pytest·기존 도구 하위 호환용으로 유지.
"""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from routes.analyze import router as analyze_router
from routes.beta import router as beta_router
from routes.check_photo import router as check_photo_router
from routes.clothing import router as clothing_router
from routes.fit import router as fit_router
from routes.synthesize import router as synthesize_router

FRONT_DIST = Path(__file__).resolve().parent.parent / "dist"

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

_routers = (
    analyze_router,
    beta_router,
    check_photo_router,
    clothing_router,
    fit_router,
    synthesize_router,
)

# 루트 경로 등록 (하위 호환 — pytest·Vite dev 프록시가 /api를 벗겨 전달)
for _r in _routers:
    app.include_router(_r)

# /api 프리픽스 등록 (배포 — 프론트가 같은 오리진 /api/*로 직접 호출)
_api = APIRouter(prefix="/api")
for _r in _routers:
    _api.include_router(_r)


@app.get("/health")
@_api.get("/health")
def health() -> dict[str, str]:
    """서버 기동 확인용."""
    return {"status": "ok", "phase": "6-3a"}


# include_router는 호출 시점에 라우트를 복사하므로 /api/health 등록 뒤에 수행
app.include_router(_api)


class _SpaStaticFiles(StaticFiles):
    """SPA 폴백 — 파일이 없으면 index.html 반환 (새로고침·직접 URL 진입 대응)."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


# dist가 있을 때만 마운트 — 로컬 개발(Vite dev 서버)·pytest는 영향 없음.
# 마운트는 라우트보다 나중에 매칭되므로 API 경로를 가리지 않는다.
if FRONT_DIST.is_dir():
    app.mount("/", _SpaStaticFiles(directory=FRONT_DIST, html=True), name="front")
