"""촬영 품질 판정 테스트 (2-7c + 2026-07-21 거리 밴드 개선).

전부 합성 마커 이미지 — API 0회, 픽스처 불필요.
거리 판정: 마커 px 크기 밴드(MIN/MAX_MARKER_WIDTH_PX)가 원거리(노이즈)와
근거리(깊이 편향 r>1.05 — 실기기 실증)를 양방향으로 걸러내는지 확인한다.
"""

import cv2
import numpy as np

from services.measure import MAX_MARKER_WIDTH_PX, MIN_MARKER_WIDTH_PX
from services.photo_check import check_photo
from services.reference_detect import ARUCO_DICT_ID, MARKER_ID

W, H = 1080, 1440  # CapturedImage 규격 (프레임은 실캡처와 동일 크기 — 2-8d)


def _page_with_marker(marker_side: int, center=(0.5, 0.4)) -> np.ndarray:
    """흰 배경 위 ArUco 마커 합성 프레임. center는 비율 좌표."""
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID), MARKER_ID, marker_side
    )
    page = np.full((H, W), 255, dtype=np.uint8)
    cx, cy = int(W * center[0]), int(H * center[1])
    x0, y0 = cx - marker_side // 2, cy - marker_side // 2
    page[y0 : y0 + marker_side, x0 : x0 + marker_side] = marker
    return cv2.cvtColor(page, cv2.COLOR_GRAY2BGR)


IN_BAND = int((MIN_MARKER_WIDTH_PX + MAX_MARKER_WIDTH_PX) // 2)  # 47


def test_in_band_marker_ready():
    """적정 크기(밴드 내)·중앙·정면 → ready."""
    result = check_photo(_page_with_marker(IN_BAND), "precise")
    assert result["ready"] is True
    assert result["markerSizeOk"] is True
    assert result["reasons"] == []


def test_too_small_marker_says_come_closer():
    """밴드 아래(원거리) → ready 거부 + '다가와' 안내."""
    result = check_photo(_page_with_marker(30), "precise")
    assert result["ready"] is False
    assert result["markerSizeOk"] is False
    assert any("다가와" in r for r in result["reasons"])


def test_too_large_marker_says_step_back():
    """밴드 위(근거리 — 깊이 편향 구간) → ready 거부 + '물러나' 안내.

    실기기 실증(2026-07-21): 구 기준(하한 60만)은 이 구간을 통과시켜
    r=1.09~1.11 깊이 편향 사진이 자동 촬영됐다 — 회귀 방어선.
    """
    result = check_photo(_page_with_marker(100), "precise")
    assert result["ready"] is False
    assert result["markerSizeOk"] is False
    assert any("물러나" in r for r in result["reasons"])


def test_old_min_60px_now_rejected():
    """구 하한 경계(60px)는 이제 근거리로 거부된다 (v1 59.9px→r=1.121 실증)."""
    result = check_photo(_page_with_marker(60), "precise")
    assert result["markerSizeOk"] is False


def test_off_center_marker_rejected():
    """마커가 화면 가장자리 → 중앙 위치 거부 (크기는 적정)."""
    result = check_photo(_page_with_marker(IN_BAND, center=(0.9, 0.4)), "precise")
    assert result["ready"] is False
    assert result["markerCentered"] is False


def test_no_marker_not_detected():
    """마커 없는 프레임 → detected:false + 안내 (가짜 판정 없음)."""
    blank = np.full((H, W, 3), 255, dtype=np.uint8)
    result = check_photo(blank, "precise")
    assert result["ready"] is False
    assert result["reference"]["detected"] is False
    assert len(result["reasons"]) == 1
