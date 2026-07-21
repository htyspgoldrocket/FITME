"""촬영 품질 판정 (Step 2-7c) — 촬영 가이드 층위 3의 백엔드.

역할: 촬영 "전" 프레임이 측정에 적합한지 빠르게 판정한다 (자동 촬영 트리거).
AI 호출 없음 — 기존 검출(2-2 카드 / 2-3 ArUco)과 2-7의 판정 상수를 재활용한다.
전체 측정(/analyze)과 역할이 다르다: 여기는 "찍어도 되는가"만 본다.

판정 기준 (전부 단일 출처 상수):
  - 마커 크기:  measure.MIN/MAX_MARKER_WIDTH_PX 밴드 (작음=원거리 척도 노이즈 /
                큼=근거리 깊이 편향 — 2026-07-21 실기기 r=1.09~1.11 실증으로 밴드화.
                거리 판정을 겸한다: 사용자에게 "가까이/물러나" 방향을 안내)
  - 기울기:     measure.TILT_RATIO_RANGE (가로/세로 척도 비 ≈1이 정면 —
                원본 fixture 실측 0.4201/0.4201이 근거)
  - 중앙 위치:  아래 CENTER_* 상수 (마커=가슴 위치 기준. ⚠️ 근거: 추정 —
                전신이 프레임에 차고 몸이 정중앙일 때 가슴이 올 수 있는 넉넉한 범위)
"""

from __future__ import annotations

import numpy as np

from services.reference_detect import detect_aruco, detect_card
from services.measure import (
    MAX_MARKER_WIDTH_PX,
    MIN_MARKER_WIDTH_PX,
    TILT_RATIO_RANGE,
    compute_scale,
)

# 마커(가슴 부착) 중심이 있어야 하는 화면 영역 — 비율 좌표. ⚠️ 추정 기준.
CENTER_X_RANGE = (0.25, 0.75)   # 몸이 정중앙이면 마커 x는 중앙 50% 안
CENTER_Y_RANGE = (0.12, 0.65)   # 전신이 프레임에 차면 가슴 y는 상단 12%~65%


def check_photo(image_bgr: np.ndarray, mode: str) -> dict:
    """프레임 1장을 판정해 PhotoCheckResult 형태의 dict를 반환한다."""
    detect = detect_card if mode == "simple" else detect_aruco
    ref = detect(image_bgr)

    if not ref["detected"]:
        thing = "카드" if mode == "simple" else "마커"
        return {
            "ready": False,
            "reference": ref,
            "markerSizeOk": False,
            "markerCentered": False,
            "tiltOk": False,
            "reasons": [
                f"{thing}가 보이지 않습니다 — {thing}를 가슴 앞에 평평하게 들고, "
                "밝은 곳에서 정면을 향해 주세요"
            ],
        }

    scale = compute_scale(ref)
    trace = scale["trace"]
    h, w = image_bgr.shape[:2]
    reasons: list[str] = []

    # 거리 판정 겸용 — 작음=너무 멂(노이즈), 큼=너무 가까움(깊이 편향 r>1.05 실증)
    size_ok = bool(MIN_MARKER_WIDTH_PX <= trace["widthPx"] <= MAX_MARKER_WIDTH_PX)
    if trace["widthPx"] < MIN_MARKER_WIDTH_PX:
        reasons.append("너무 멀리 있습니다 — 카메라 쪽으로 조금 다가와 주세요")
    elif trace["widthPx"] > MAX_MARKER_WIDTH_PX:
        reasons.append("너무 가까이 있습니다 — 뒤로 물러나 주세요")

    tilt_ratio = trace["mmPerPxWidth"] / trace["mmPerPxHeight"]
    tilt_ok = TILT_RATIO_RANGE[0] <= tilt_ratio <= TILT_RATIO_RANGE[1]
    if not tilt_ok:
        reasons.append("기준물이 비스듬합니다 — 기준물을 몸에 평평하게 대고 정면을 향해 주세요")

    corners = np.asarray(ref["cornersPx"], dtype=float)
    cx, cy = corners.mean(axis=0) / (w, h)
    # bool() 캐스팅 필수: numpy 비교 결과(numpy.bool_)는 Python bool과 타입이 달라
    # `is True` 판정·JSON 직렬화에서 계약(boolean)과 어긋난다
    centered = bool(
        CENTER_X_RANGE[0] <= cx <= CENTER_X_RANGE[1]
        and CENTER_Y_RANGE[0] <= cy <= CENTER_Y_RANGE[1]
    )
    if not centered:
        reasons.append("몸이 화면 중앙에서 벗어났습니다 — 몸을 화면 정중앙에 맞춰 주세요")

    return {
        "ready": bool(size_ok and tilt_ok and centered),
        "reference": ref,
        "markerSizeOk": bool(size_ok),
        "markerCentered": centered,
        "tiltOk": bool(tilt_ok),
        "reasons": reasons,
    }
