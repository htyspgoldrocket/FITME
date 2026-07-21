"""POST /analyze — 신체 치수 분석 (Phase 2-8a: 실제 측정 파이프라인 배선).

파이프라인: 기준물 검출(2-2/2-3) → 척도(2-4) → 프레임별 랜드마크 추출(2-5)
→ 다중 프레임 중앙값·신뢰도(2-7) → 키 캘리브레이션·BMI 보정(2-7b, profile 있을 때).

⚠️ 프레임당 Claude Vision 1회 호출 — 기본 7프레임이면 요청당 API 7회.
"""

import base64
import binascii

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException

from models.schemas import AnalyzeRequest, AnalyzeResponse
from services.claude_vision import extract_body_landmarks
from services.measure import compute_scale, measure_with_statistics
from services.reference_detect import detect_aruco, detect_card

router = APIRouter()

# 프레임 수 상한 — 기본 7(2-7 확정) + 여유 2. 초과분은 API 비용 보호를 위해 버린다.
MAX_FRAMES = 9


def _decode_bgr(image_base64: str) -> np.ndarray:
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="base64 이미지 디코딩 실패")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="이미지 형식을 해석할 수 없습니다")
    return image


@router.post("/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    image = _decode_bgr(req.image.base64)

    detect = detect_card if req.mode == "simple" else detect_aruco
    reference = detect(image)
    if not reference["detected"]:
        name = "신용카드" if req.mode == "simple" else "ArUco 마커"
        return AnalyzeResponse(
            ok=False,
            reference=reference,
            error=f"{name}를 찾지 못했습니다. 기준물이 가려지지 않게 "
                  "정면으로 평평하게 보이도록 다시 촬영해 주세요.",
        )

    scale = compute_scale(reference)

    # 다중 프레임(전략 3) — frames가 없으면 대표 이미지 1장으로 측정.
    # 프레임 크기는 CapturedImage 규격상 대표 이미지와 동일하다 (Phase 1 캡처 계약).
    frames = (req.image.frames or [req.image.base64])[:MAX_FRAMES]
    runs: list[dict] = []
    failed = 0
    for frame_b64 in frames:
        try:
            runs.append(
                extract_body_landmarks(
                    frame_b64, req.image.width, req.image.height, req.image.mimeType
                )
            )
        except ValueError:
            # 해당 프레임만 버림 — 인프라 오류(키 없음·네트워크)는 그대로 500으로 드러낸다
            failed += 1

    if not runs:
        return AnalyzeResponse(
            ok=False,
            reference=reference,
            error="신체 좌표를 추출하지 못했습니다. 전신이 프레임에 꽉 차고 "
                  "밝게 나오도록 다시 촬영해 주세요.",
        )

    profile = req.profile.model_dump() if req.profile is not None else None
    result = measure_with_statistics(runs, scale, req.mode, reference, profile=profile)

    warnings = list(result["warnings"])
    if failed:
        warnings.append(
            f"{len(frames)}개 프레임 중 {failed}개에서 좌표 추출 실패 — "
            f"나머지 {len(runs)}개로 측정했습니다"
        )

    return AnalyzeResponse(
        ok=True,
        reference=reference,
        measurements=result["measurements"],
        warnings=warnings,
        stats=result["stats"],
        landmarks=result["landmarks"],
    )
