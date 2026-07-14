"""POST /analyze — 신체 치수 분석 (Phase 2).

⚠️ Phase 2-1 상태: 아직 실제 측정을 하지 않는 의도된 STUB이다 (규칙 1의 명시된 예외).
실제 구현 예정:
  - 기준물 검출(OpenCV)      → Step 2-2(카드) / 2-3(ArUco)
  - 호모그래피·척도           → Step 2-4
  - 신체 부위 인식(Claude)    → Step 2-5
  - cm 산출·둘레 근사         → Step 2-6
  - 다중 프레임·신뢰도        → Step 2-7
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.schemas import AnalyzeRequest, BodyMeasurements, ReferenceInfo

router = APIRouter()

# 프론트 stub(src/lib/api.ts)과 동일한 더미 값 — 규격 확인용
_STUB_CONFIDENCE = {
    "height": "high",
    "shoulder_width": "high",
    "chest_circumference": "medium",
    "waist_circumference": "medium",
    "hip_circumference": "medium",
    "arm_length": "high",
    "inseam": "medium",
    "torso_length": "medium",
}


@router.post("/analyze")
def analyze(req: AnalyzeRequest) -> JSONResponse:
    """더미 BodyMeasurements 반환. 요청 본문은 검증만 하고 사용하지 않는다."""
    is_simple = req.mode == "simple"
    dummy = BodyMeasurements(
        height=175,
        shoulder_width=45,
        chest_circumference=96,
        waist_circumference=80,
        hip_circumference=95,
        arm_length=58,
        inseam=78,
        torso_length=62,
        confidence=_STUB_CONFIDENCE,
        mode=req.mode,
        reference=ReferenceInfo(
            type="card" if is_simple else "aruco",
            realWidthMm=85.6 if is_simple else 50,
            realHeightMm=53.98 if is_simple else 50,
            detected=True,  # stub이므로 항상 True (실제 검출 아님)
        ),
    )
    # BodyMeasurements 규격 + stub 표시 필드.
    # "stub" 키는 Step 2-6에서 실제 측정으로 교체되면서 제거된다.
    return JSONResponse(
        {**dummy.model_dump(), "stub": "Phase 2-1 더미 응답입니다. 실제 측정값이 아닙니다."}
    )
