"""Phase 2-4 자동 검증 — 호모그래피 척도 계산 (measure.py).

2-4 개발 시 수행한 합성 검증(기하 정밀도·공통 인터페이스)을 테스트로 고정한다.
실사진 의존 테스트는 로컬 전용 픽스처가 없으면 skip (2-2/2-3과 동일 방식).
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from services.measure import compute_scale, distance_mm, points_px_to_plane_mm
from services.reference_detect import detect_aruco

FIXTURES = Path(__file__).parent / "fixtures"
ARUCO_PHOTO = FIXTURES / "person01_aruco.jpg"

needs_aruco_photo = pytest.mark.skipif(
    not ARUCO_PHOTO.exists(),
    reason="로컬 전용 픽스처 사진 없음 (fixtures/README.md 참조)",
)


def _aruco_ref(corners) -> dict:
    return {
        "type": "aruco",
        "realWidthMm": 70.0,
        "realHeightMm": 70.0,
        "detected": True,
        "cornersPx": corners,
    }


def _card_ref(corners) -> dict:
    return {
        "type": "card",
        "realWidthMm": 85.6,
        "realHeightMm": 53.98,
        "detected": True,
        "cornersPx": corners,
    }


# ---------- 1) 기하 검증: 원근 하에서 실거리 복원 (2-4 검증 고정) ----------

def test_distance_recovered_under_perspective():
    """기울어진 카메라 시뮬레이션에서 500mm 거리를 0.01mm 이내로 복원."""
    marker_mm = np.array([[100, 100], [170, 100], [170, 170], [100, 170]], dtype=np.float32)
    cam = cv2.getPerspectiveTransform(
        np.array([[0, 0], [600, 0], [600, 600], [0, 600]], dtype=np.float32),
        np.array([[120, 80], [980, 140], [900, 1020], [60, 950]], dtype=np.float32),
    )

    def project(pts_mm):
        pts = np.asarray(pts_mm, dtype=np.float64).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, cam.astype(np.float64)).reshape(-1, 2)

    scale = compute_scale(_aruco_ref(project(marker_mm).tolist()))
    p_a, p_b = project([(50.0, 400.0), (550.0, 400.0)])  # 실제 500mm
    d = distance_mm(scale, p_a, p_b)
    assert abs(d - 500.0) < 0.01, f"복원 거리 {d:.4f}mm (기대 500mm)"


# ---------- 2) 카드/ArUco 공통 인터페이스 ----------

def test_scale_card_axis_aligned():
    """정면 카드(원근 없음): 428px 너비 = 85.6mm → 1px = 0.2mm 정확히."""
    corners = [[0, 0], [428, 0], [428, 269.9], [0, 269.9]]  # 85.6/0.2, 53.98/0.2
    scale = compute_scale(_card_ref(corners))
    assert scale["mmPerPx"] == pytest.approx(0.2, abs=1e-4)
    assert scale["trace"]["refType"] == "card"


def test_scale_aruco_axis_aligned():
    """정면 마커(원근 없음): 140px = 70mm → 1px = 0.5mm 정확히."""
    corners = [[10, 10], [150, 10], [150, 150], [10, 150]]
    scale = compute_scale(_aruco_ref(corners))
    assert scale["mmPerPx"] == pytest.approx(0.5, abs=1e-6)
    assert scale["trace"]["refType"] == "aruco"


# ---------- 3) 미검출/불량 입력 거부 ----------

def test_not_detected_raises():
    ref = _aruco_ref(None)
    ref["detected"] = False
    with pytest.raises(ValueError):
        compute_scale(ref)


def test_detected_but_no_corners_raises():
    ref = _aruco_ref(None)  # detected:True인데 cornersPx 없음 — 불량 입력
    with pytest.raises(ValueError):
        compute_scale(ref)


def test_wrong_corner_count_raises():
    with pytest.raises(ValueError):
        compute_scale(_aruco_ref([[0, 0], [1, 0], [1, 1]]))  # 3점


# ---------- 4) 실사진 척도 상식 범위 (1080px 실전 조건 fixture) ----------

@needs_aruco_photo
def test_real_photo_scale_in_expected_range():
    """1080px 실전 fixture: 마커 ≈60px, 1px ≈ 1.17mm (여유 범위로 검사)."""
    img = cv2.imread(str(ARUCO_PHOTO))
    scale = compute_scale(detect_aruco(img))
    t = scale["trace"]
    assert 45 <= t["widthPx"] <= 80, f"마커 너비 {t['widthPx']:.1f}px"
    assert 0.9 <= scale["mmPerPx"] <= 1.5, f"mmPerPx {scale['mmPerPx']:.4f}"
    # 정면 촬영 사진이므로 가로/세로 척도가 크게 벌어지면 안 됨
    ratio = t["mmPerPxWidth"] / t["mmPerPxHeight"]
    assert 0.9 <= ratio <= 1.1, f"가로/세로 척도 비 {ratio:.3f}"


# ---------- 5) distance_mm ----------

def test_distance_mm_axis_aligned():
    """1px=0.5mm 조건에서 200px 거리 = 100mm."""
    scale = compute_scale(_aruco_ref([[10, 10], [150, 10], [150, 150], [10, 150]]))
    assert distance_mm(scale, (300, 400), (500, 400)) == pytest.approx(100.0, abs=1e-6)


def test_points_px_to_plane_mm_maps_corners_to_real_size():
    """기준물 꼭짓점을 평면 mm로 보내면 정확히 (0,0)~(70,70)."""
    corners = [[10, 10], [150, 10], [150, 150], [10, 150]]
    scale = compute_scale(_aruco_ref(corners))
    mm = points_px_to_plane_mm(scale, corners)
    expected = np.array([[0, 0], [70, 0], [70, 70], [0, 70]], dtype=np.float64)
    assert np.allclose(mm, expected, atol=1e-4)


# ---------- 6) trace 역추적 정보 ----------

def test_trace_contains_traceability_fields():
    corners = [[10, 10], [150, 10], [150, 150], [10, 150]]
    scale = compute_scale(_aruco_ref(corners))
    t = scale["trace"]
    assert t["refType"] == "aruco"
    assert t["realWidthMm"] == 70.0 and t["realHeightMm"] == 70.0
    assert t["cornersPx"] == [[10.0, 10.0], [150.0, 10.0], [150.0, 150.0], [10.0, 150.0]]
    assert set(t["sidesPx"].keys()) == {"top", "right", "bottom", "left"}
    assert t["widthPx"] == pytest.approx(140.0)
    assert t["heightPx"] == pytest.approx(140.0)
    assert t["mmPerPxWidth"] == pytest.approx(0.5)
    assert t["mmPerPxHeight"] == pytest.approx(0.5)
    # 호모그래피도 함께 반환되는지 (3x3)
    h = np.asarray(scale["homographyPx2Mm"])
    assert h.shape == (3, 3)
