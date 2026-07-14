"""기준물 검출 (Phase 2) — 간편 모드: 신용카드 사각형 (Step 2-2).

ISO/IEC 7810 ID-1 카드: 85.6 x 53.98 mm, 비율 1.586.

두 전략을 순서대로 시도한다:
  A) 에지 기반 닫힌 4각형 — 카드 테두리가 온전히 보일 때 가장 정밀
  B) 밝은 블롭 - 피부 마스크 + 회전 사각형 피팅 — 손가락이 카드 가장자리를
     쥐어 윤곽이 손으로 이어질 때(실사용 기본 상황)의 대응책.
     실사진(person01)에서 A는 손가락 때문에 실패, B가 검출함을 확인.

알려진 한계 (fixtures 추가 시 보강 예정):
  - B는 "옷보다 밝은 카드"를 가정한다. 어두운 카드 + 어두운 옷 조합은 미지원.
  - 카드는 대체로 가로로 들었다고 가정 (긴 변 기울기 ±45° 이내, 촬영 가이드와 일치).

ArUco 검출(정밀 모드)은 Step 2-3에서 추가 예정 (아직 미구현).
호모그래피·척도 계산은 Step 2-4의 measure.py 담당 — 여기서는 꼭짓점만 찾는다.
"""

from __future__ import annotations

import numpy as np
import cv2

# ISO/IEC 7810 ID-1
CARD_WIDTH_MM = 85.6
CARD_HEIGHT_MM = 53.98
CARD_RATIO = CARD_WIDTH_MM / CARD_HEIGHT_MM  # ≈ 1.586

# 비율 허용 범위 — 손가락 가림·약한 원근 감안 (정사각형 1.0, 긴 띠 >2 배제)
RATIO_MIN = 1.35
RATIO_MAX = 1.85

# 카드 면적의 이미지 대비 비율 (전신 2m 촬영 기준: 너무 작으면 노이즈, 크면 가구)
AREA_MIN_FRAC = 0.0002   # 0.02%
AREA_MAX_FRAC = 0.02     # 2%

# 긴 변의 수평 대비 최대 기울기 (촬영 가이드: 카드를 가로로 들기)
MAX_TILT_DEG = 45.0

# 블롭이 회전 사각형을 채우는 최소 비율 (손가락 가림으로 일부 빠져도 0.7은 유지)
MIN_RECT_FILL = 0.70

APPROX_EPS_FRAC = 0.02   # 윤곽 근사 정밀도 (둘레 대비)
WORK_WIDTH = 1080        # 내부 작업 해상도 (반환 좌표는 원본 픽셀로 환산)


def detect_card(image_bgr: np.ndarray) -> dict:
    """사진에서 신용카드를 찾아 ReferenceInfo 형태의 dict를 반환한다.

    반환 (src/types/index.ts ReferenceInfo와 1:1):
      { "type": "card", "realWidthMm": 85.6, "realHeightMm": 53.98,
        "detected": bool, "cornersPx": [[x,y]*4] | None }
    cornersPx 순서: 좌상 → 우상 → 우하 → 좌하 (원본 이미지 픽셀 좌표)
    """
    corners = _find_card_corners(image_bgr)
    return {
        "type": "card",
        "realWidthMm": CARD_WIDTH_MM,
        "realHeightMm": CARD_HEIGHT_MM,
        "detected": corners is not None,
        "cornersPx": corners.tolist() if corners is not None else None,
    }


def _find_card_corners(image_bgr: np.ndarray) -> np.ndarray | None:
    h0, w0 = image_bgr.shape[:2]
    scale = WORK_WIDTH / w0 if w0 > WORK_WIDTH else 1.0
    work = (
        cv2.resize(image_bgr, (int(w0 * scale), int(h0 * scale)))
        if scale != 1.0
        else image_bgr
    )

    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    # 에지 보존 스무딩: 체크무늬 등 텍스처로 인한 가짜 윤곽 억제
    smooth = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

    corners = _strategy_edge_quad(smooth)
    if corners is None:
        corners = _strategy_bright_blob(work, smooth)
    if corners is None:
        return None
    return (_order_corners(corners) / scale).astype(np.float32)


# ---------- 전략 A: 에지 기반 닫힌 4각형 ----------

def _strategy_edge_quad(smooth: np.ndarray) -> np.ndarray | None:
    img_area = float(smooth.shape[0] * smooth.shape[1])
    median = float(np.median(smooth))
    edges = cv2.Canny(smooth, int(max(0, 0.66 * median)), int(min(255, 1.33 * median)))
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best, best_score = None, float("inf")
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (AREA_MIN_FRAC * img_area <= area <= AREA_MAX_FRAC * img_area):
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, APPROX_EPS_FRAC * peri, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        quad = approx.reshape(4, 2).astype(np.float32)

        rect = cv2.minAreaRect(cnt)
        score = _score_rect(rect, area)
        if score is not None and score < best_score:
            best_score, best = score, quad
    return best


# ---------- 전략 B: 밝은 블롭 - 피부 + 회전 사각형 피팅 ----------

def _strategy_bright_blob(work_bgr: np.ndarray, smooth: np.ndarray) -> np.ndarray | None:
    img_area = float(smooth.shape[0] * smooth.shape[1])

    # 피부(손가락) 제거 — YCrCb 표준 피부 범위
    ycrcb = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2YCrCb)
    skin = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    skin = cv2.dilate(skin, np.ones((5, 5), np.uint8), iterations=2)

    _, bright = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blob = cv2.bitwise_and(bright, cv2.bitwise_not(skin))
    blob = cv2.morphologyEx(blob, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    n, labels, stats, _ = cv2.connectedComponentsWithStats(blob)
    best, best_score = None, float("inf")
    for i in range(1, n):
        area = float(stats[i, cv2.CC_STAT_AREA])
        if not (AREA_MIN_FRAC * img_area <= area <= AREA_MAX_FRAC * img_area):
            continue
        mask_i = (labels == i).astype(np.uint8)
        cnts, _ = cv2.findContours(mask_i, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        rect = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
        score = _score_rect(rect, area)
        if score is not None and score < best_score:
            best_score = score
            best = cv2.boxPoints(rect)  # 손가락으로 빈 부분을 사각형으로 보간
    return best


# ---------- 공통 판정 ----------

def _score_rect(rect: cv2.typing.RotatedRect, blob_area: float) -> float | None:
    """회전 사각형이 '가로로 든 카드'로 그럴듯한지 판정. 통과 시 점수(낮을수록 좋음)."""
    (cx, cy), (rw, rh), angle = rect
    if min(rw, rh) <= 0:
        return None
    ratio = max(rw, rh) / min(rw, rh)
    if not (RATIO_MIN <= ratio <= RATIO_MAX):
        return None
    fill = blob_area / (rw * rh)
    if fill < MIN_RECT_FILL:
        return None
    # 긴 변의 수평 대비 기울기 (OpenCV 회전각 정규화)
    tilt = angle if rw >= rh else angle - 90.0
    tilt = (tilt + 90.0) % 180.0 - 90.0
    if abs(tilt) > MAX_TILT_DEG:
        return None
    # 비율 근접도 주(主), 채움 부족 보조 감점
    return abs(ratio - CARD_RATIO) + 0.1 * (1.0 - fill)


def _order_corners(quad: np.ndarray) -> np.ndarray:
    """꼭짓점을 좌상→우상→우하→좌하 순으로 정렬."""
    quad = quad.reshape(4, 2).astype(np.float32)
    s = quad.sum(axis=1)
    d = np.diff(quad, axis=1).ravel()  # y - x
    return np.array(
        [
            quad[np.argmin(s)],
            quad[np.argmin(d)],
            quad[np.argmax(s)],
            quad[np.argmax(d)],
        ],
        dtype=np.float32,
    )


def draw_detection(image_bgr: np.ndarray, corners_px: list | None) -> np.ndarray:
    """검출 결과를 원본 위에 그린 확인용 이미지 (육안 검증용)."""
    vis = image_bgr.copy()
    if corners_px:
        pts = np.array(corners_px, dtype=np.int32)
        cv2.polylines(vis, [pts], isClosed=True, color=(0, 255, 0), thickness=4)
        for i, (x, y) in enumerate(pts):
            cv2.circle(vis, (int(x), int(y)), 10, (0, 0, 255), -1)
            cv2.putText(vis, str(i), (int(x) + 12, int(y) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    return vis


if __name__ == "__main__":
    # 개발 확인용 CLI: python services/reference_detect.py <이미지경로> [출력경로]
    import sys

    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "debug_card_detect.jpg"
    img = cv2.imread(src)
    if img is None:
        print(f"cannot open image: {src}")
        sys.exit(1)
    result = detect_card(img)
    print({k: v for k, v in result.items() if k != "cornersPx"})
    print("cornersPx:", result["cornersPx"])
    cv2.imwrite(out, draw_detection(img, result["cornersPx"]))
    print("debug image saved:", out)
