# -*- coding: utf-8 -*-
"""POST /synthesize — 사람 사진 + 의류 스펙 → 합성 이미지 (Phase 5-2c).

⚠️ 서버가 쓰는 VTON 모델(services/vton.py, cuuupid/idm-vton)은 CC BY-NC-SA 4.0
(상업 사용 금지) — 출시 전 FASHN API 등으로 교체 필요 (CLAUDE.md 12장).

실패는 HTTP 오류가 아니라 SynthesizeResponse.ok=False + error(한국어) + code로
전달한다 (AnalyzeResponse/ClothingResponse와 같은 방식 — 규칙 1).

⚠️ replicate 클라이언트가 동기 HTTP를 쓰므로 `def` 엔드포인트여야 한다 —
FastAPI가 threadpool에서 실행 (clothing.py의 Playwright와 동일 이유, 배운 것 4번).
"""

import base64
import binascii
from io import BytesIO

from fastapi import APIRouter, Depends

from models.schemas import SynthesizeRequest, SynthesizeResponse
from services.access_guard import guard_ai_route
from services.vton import VtonError, synthesize

router = APIRouter()


# 6-1: AI 비용 라우트 — 베타 코드·사용량 상한 (FITME_BETA_CODE 설정 시에만 활성)
@router.post(
    "/synthesize",
    response_model=SynthesizeResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(guard_ai_route)],
)
def synthesize_endpoint(req: SynthesizeRequest) -> SynthesizeResponse:
    clothing = req.clothing
    if not clothing.imageUrl:
        return SynthesizeResponse(
            ok=False,
            error="이 상품은 합성용 이미지가 없어요",
            code="no-garment-image",
        )

    try:
        human_bytes = base64.b64decode(req.humanImage.base64, validate=True)
    except (binascii.Error, ValueError):
        return SynthesizeResponse(
            ok=False, error="사진 데이터를 읽지 못했어요", code="synthesis-failed"
        )

    try:
        result_bytes = synthesize(
            BytesIO(human_bytes),
            clothing.imageUrl,
            clothing.category,
            garment_des=clothing.productName or "",
        )
    except VtonError as e:
        return SynthesizeResponse(ok=False, error=str(e), code=e.code)

    return SynthesizeResponse(
        ok=True, imageBase64=base64.b64encode(result_bytes).decode("ascii")
    )
