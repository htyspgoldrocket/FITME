# -*- coding: utf-8 -*-
"""POST /fit — 신체 치수 × 의류 스펙 → FitResult (Phase 4-4).

파이프라인: recommend_size(4-2, 하의 허리 A안) → 추천 사이즈의 FitScore(4-1)
→ generate_feedback(4-3, 실패 시 사실 기반 템플릿 폴백 — 요청은 실패하지 않음).

추천 불가(비교 가능한 부위 실측이 없는 사이즈표)는 HTTP 오류가 아니라
ok=False + error(한국어)로 전달한다 — 가짜 사이즈를 만들지 않는다 (규칙 1).

def 엔드포인트(threadpool) — generate_feedback가 동기 HTTP(Claude API)를 쓴다.
"""

from fastapi import APIRouter

from models.schemas import FitRequest, FitResponse, FitResult
from services.fit import recommend_size
from services.fit_feedback import generate_feedback

router = APIRouter()


@router.post("/fit", response_model=FitResponse, response_model_exclude_none=True)
def fit_endpoint(req: FitRequest) -> FitResponse:
    rec = recommend_size(req.measurements, req.clothing)
    label = rec["recommendedSize"]

    if label is None:
        return FitResponse(
            ok=False,
            warnings=rec["warnings"],
            error=" ".join(rec["warnings"]) or "사이즈 추천이 어려워요",
        )

    feedback = generate_feedback(req.measurements, req.clothing, rec)
    scores = next(
        p["scores"] for p in rec["perSize"] if p["label"] == label
    )
    result = FitResult(
        measurements=req.measurements,
        clothing=req.clothing,
        recommendedSize=label,
        scores=scores,
        recommendation=feedback["text"],
        # imageUrl은 서버가 채우지 않는다 — 합성은 별도 온디맨드 /synthesize
        # (VTON 비용)이고, 성공 시 프론트 App이 핏 캐시에 채운다 (5-4)
    )
    return FitResponse(ok=True, result=result, warnings=rec["warnings"])
