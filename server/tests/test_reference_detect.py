"""Phase 2-2 자동 검증 — 신용카드 검출 (간편 모드).

fixtures의 실사진(person01_card.jpg)은 .gitignore로 로컬 전용이므로,
사진이 없는 환경(새 클론 등)에서는 해당 테스트를 skip한다 (실패 아님).
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from services.reference_detect import CARD_RATIO, detect_card

FIXTURES = Path(__file__).parent / "fixtures"
CARD_PHOTO = FIXTURES / "person01_card.jpg"

needs_photo = pytest.mark.skipif(
    not CARD_PHOTO.exists(),
    reason="로컬 전용 픽스처 사진 없음 (fixtures/README.md 참조)",
)


# ---------- 1) 카드 포함 사진 → detected:true + 꼭짓점 4개 ----------

@needs_photo
def test_card_photo_detected():
    img = cv2.imread(str(CARD_PHOTO))
    assert img is not None, "픽스처 사진을 열 수 없음"
    result = detect_card(img)

    assert result["type"] == "card"
    assert result["realWidthMm"] == 85.6
    assert result["realHeightMm"] == 53.98
    assert result["detected"] is True
    corners = result["cornersPx"]
    assert corners is not None and len(corners) == 4
    for pt in corners:
        assert len(pt) == 2
        x, y = pt
        # 좌표가 이미지 안에 있어야 함
        assert 0 <= x <= img.shape[1] and 0 <= y <= img.shape[0]


@needs_photo
def test_card_corners_ordered():
    """꼭짓점 순서 계약: 좌상 → 우상 → 우하 → 좌하."""
    img = cv2.imread(str(CARD_PHOTO))
    tl, tr, br, bl = detect_card(img)["cornersPx"]
    assert tl[0] < tr[0] and bl[0] < br[0], "좌측 꼭짓점이 우측보다 왼쪽이어야 함"
    assert tl[1] < bl[1] and tr[1] < br[1], "상단 꼭짓점이 하단보다 위여야 함"


# ---------- 2) 카드 없는 이미지 → detected:false ----------

def test_no_card_noise_image():
    noise = np.random.default_rng(42).integers(0, 255, (1440, 1080, 3), dtype=np.uint8)
    result = detect_card(noise)
    assert result["detected"] is False
    assert result["cornersPx"] is None


def test_no_card_flat_image():
    flat = np.full((1440, 1080, 3), 128, dtype=np.uint8)
    result = detect_card(flat)
    assert result["detected"] is False
    assert result["cornersPx"] is None


# ---------- 3) 검출된 사각형의 비율 ≈ 카드 비율(1.586) ----------

@needs_photo
def test_detected_ratio_close_to_card():
    img = cv2.imread(str(CARD_PHOTO))
    corners = np.array(detect_card(img)["cornersPx"], dtype=np.float32)
    sides = [float(np.linalg.norm(corners[i] - corners[(i + 1) % 4])) for i in range(4)]
    a = (sides[0] + sides[2]) / 2.0  # 위/아래 변 평균
    b = (sides[1] + sides[3]) / 2.0  # 좌/우 변 평균
    ratio = max(a, b) / min(a, b)
    # 손가락 가림 보간·약한 원근을 감안한 허용 오차 ±0.15
    assert abs(ratio - CARD_RATIO) <= 0.15, f"비율 {ratio:.3f} (기대 {CARD_RATIO:.3f})"
