"""척도 계산 (Step 2-4) — 왜곡 극복 전략 2: 호모그래피로 원근 제거 + px→mm 환산.

원리 (CLAUDE.md 2장): 크기를 아는 직사각형(카드 85.6×53.98mm / ArUco 70×70mm)이
사진에서 찌그러진 정도로 카메라 원근을 역산한다. 기준물 4꼭짓점 ↔ 실측 mm 좌표의
대응으로 호모그래피 H(이미지 px → 기준물 평면 mm)를 구하면, 같은 평면 위 임의의
두 점 사이 실제 거리를 mm로 잴 수 있다.

⚠️ 전제 1 — 꼭짓점 순서 계약: cornersPx는 반드시 **좌상→우상→우하→좌하** 순서다.
   (2-2 detect_card / 2-3 detect_aruco가 이 순서로 반환하며 테스트로 고정되어 있음.
    순서가 어긋나면 호모그래피가 뒤틀려 척도가 완전히 틀어진다.)

⚠️ 전제 2 — 평면 한정: H는 "기준물이 놓인 평면"에서만 정확하다. 깊이가 다른
   점(카메라에 더 가깝거나 먼 신체 부위)은 오차가 생긴다. 그래서 촬영 가이드가
   기준물을 측정 부위와 같은 평면에 대도록 유도한다(전략 1). 깊이 차이가 큰
   둘레 추정은 2-6의 타원 근사가 보완한다.

신체 부위 좌표 추출(2-5)과 부위별 cm 산출·둘레 근사(2-6)는 아직 미구현.
"""

from __future__ import annotations

import numpy as np
import cv2


def compute_scale(reference: dict) -> dict:
    """ReferenceInfo(detect_card/detect_aruco 반환값)로 척도 정보를 계산한다.

    카드/ArUco 공통 인터페이스: reference["realWidthMm"/"realHeightMm"]만 다르고
    처리 방식은 동일하다.

    반환 dict (추적 가능성 우선 — 어떤 입력으로 어떻게 계산됐는지 전부 포함):
      homographyPx2Mm: 3x3 리스트 — 이미지 px → 기준물 평면 mm 변환 행렬
      mmPerPx:         평균 척도 (기준물 위치 기준 참고값. 정밀 계산은 H를 쓸 것)
      trace: {
        refType, realWidthMm, realHeightMm, cornersPx,
        sidesPx: {top, right, bottom, left},   # 검출된 사각형 변 길이
        widthPx, heightPx,                     # 마주보는 변 평균
        mmPerPxWidth, mmPerPxHeight,           # 가로/세로 각각의 척도
      }

    Raises:
      ValueError: 기준물 미검출이거나 cornersPx가 유효한 4점이 아닐 때
    """
    if not reference.get("detected") or not reference.get("cornersPx"):
        raise ValueError("기준물이 검출되지 않아 척도를 계산할 수 없습니다")

    src = np.asarray(reference["cornersPx"], dtype=np.float32)
    if src.shape != (4, 2):
        raise ValueError(f"cornersPx는 4개의 (x,y)여야 합니다: shape={src.shape}")

    real_w = float(reference["realWidthMm"])
    real_h = float(reference["realHeightMm"])
    if real_w <= 0 or real_h <= 0:
        raise ValueError("기준물 실측 크기(mm)가 유효하지 않습니다")

    # 순서 계약(좌상→우상→우하→좌하)에 맞춘 목적 좌표 (기준물 평면, 단위 mm)
    dst = np.array(
        [[0.0, 0.0], [real_w, 0.0], [real_w, real_h], [0.0, real_h]],
        dtype=np.float32,
    )
    homography = cv2.getPerspectiveTransform(src, dst)

    # 참고용 평균 척도 + 추적 정보
    sides_px = {
        "top": float(np.linalg.norm(src[1] - src[0])),
        "right": float(np.linalg.norm(src[2] - src[1])),
        "bottom": float(np.linalg.norm(src[2] - src[3])),
        "left": float(np.linalg.norm(src[3] - src[0])),
    }
    width_px = (sides_px["top"] + sides_px["bottom"]) / 2.0
    height_px = (sides_px["left"] + sides_px["right"]) / 2.0
    mm_per_px_w = real_w / width_px
    mm_per_px_h = real_h / height_px

    return {
        "homographyPx2Mm": homography.tolist(),
        "mmPerPx": (mm_per_px_w + mm_per_px_h) / 2.0,
        "trace": {
            "refType": reference.get("type"),
            "realWidthMm": real_w,
            "realHeightMm": real_h,
            "cornersPx": src.tolist(),
            "sidesPx": sides_px,
            "widthPx": width_px,
            "heightPx": height_px,
            "mmPerPxWidth": mm_per_px_w,
            "mmPerPxHeight": mm_per_px_h,
        },
    }


# ==================== Step 2-6: 랜드마크 → 8개 치수(cm) ====================

# ----- 둘레 타원 근사 계수 (전략 2) -----
# 원리: 정면 사진에는 몸통의 "너비"만 보이므로, 단면을 타원으로 가정하고
#   깊이(전후) = 너비 × 계수,  둘레 ≈ π × (너비 + 깊이) / 2   (CLAUDE.md 3장)
# 계수 정책 (2026-07-16, CLAUDE.md 13-2 방침 전환): person01 1명 실측
#   역산값으로 캘리브레이션한다 (2-7b에서 수행 예정). 문헌 인용은 배제 —
#   우리 조건(마커 기반·옷 위 측정·정면 너비→둘레)에 맞는 연구가 없어
#   어정쩡한 인용은 "검증된 척" 착각을 만든다 (규칙 1). 아래 값은 역산 전
#   임시값이며, 절대 정확도는 미검증 상태다 (알려진 한계 — CLAUDE.md 12장).
#   표본(3명+) 확보 시 절대 정확도 재검증은 향후 과제.
DEPTH_RATIOS = {
    "chest": 0.72,
    "waist": 0.78,
    "hip": 0.70,
}

# ----- 상식 범위 (cm) — 벗어나면 경고 + 해당 항목 신뢰도 low -----
PLAUSIBLE_RANGES_CM = {
    "height": (140.0, 210.0),
    "shoulder_width": (30.0, 55.0),
    "chest_circumference": (70.0, 140.0),
    "waist_circumference": (55.0, 140.0),
    "hip_circumference": (70.0, 140.0),
    "arm_length": (40.0, 75.0),
    "inseam": (55.0, 95.0),
    "torso_length": (40.0, 75.0),
}

# 단일 프레임 기준 초기 신뢰도. 길이는 직접 측정이라 medium,
# 둘레는 타원 "근사"라 low. 다중 프레임·해부학 비율 검증(2-7)에서 재조정된다.
_BASE_CONFIDENCE = {
    "height": "medium",
    "shoulder_width": "medium",
    "arm_length": "medium",
    "inseam": "medium",
    "torso_length": "medium",
    "chest_circumference": "low",
    "waist_circumference": "low",
    "hip_circumference": "low",
}


def ellipse_circumference_mm(width_mm: float, depth_ratio: float) -> float:
    """정면 너비(mm) → 타원 근사 둘레(mm). 둘레 ≈ π × (너비 + 깊이) / 2."""
    depth_mm = width_mm * depth_ratio
    return float(np.pi * (width_mm + depth_mm) / 2.0)


def landmarks_to_measurements(
    landmarks: dict, scale: dict, mode: str, reference: dict
) -> tuple[dict, list[str]]:
    """15개 랜드마크(2-5) × 척도(2-4) → BodyMeasurements 형태의 dict.

    매핑 (claude_vision.py의 랜드마크 정의와 1:1):
      키:        head_top ↔ 발뒤꿈치 중점        (직접 거리)
      어깨너비:  left_shoulder ↔ right_shoulder  (직접 거리)
      팔길이:    left_shoulder ↔ left_wrist      (직접 거리)
      다리안쪽:  crotch ↔ left_ankle             (직접 거리)
      상체길이:  neck_base ↔ crotch              (직접 거리)
      가슴/허리/엉덩이 둘레: 좌우 실루엣 너비 → 타원 근사

    반환: (measurements dict, warnings 리스트).
    상식 범위를 벗어난 항목은 warnings에 기록되고 confidence가 low로 강등된다.
    """
    missing = [k for k in (
        "head_top", "neck_base", "left_shoulder", "right_shoulder",
        "chest_left", "chest_right", "waist_left", "waist_right",
        "hip_left", "hip_right", "left_wrist", "crotch",
        "left_ankle", "left_heel", "right_heel",
    ) if k not in landmarks]
    if missing:
        raise ValueError(f"랜드마크 누락: {missing}")

    heel_mid = [
        (landmarks["left_heel"][0] + landmarks["right_heel"][0]) / 2.0,
        (landmarks["left_heel"][1] + landmarks["right_heel"][1]) / 2.0,
    ]

    def dist_cm(p1, p2) -> float:
        return distance_mm(scale, p1, p2) / 10.0

    values = {
        "height": dist_cm(landmarks["head_top"], heel_mid),
        "shoulder_width": dist_cm(landmarks["left_shoulder"], landmarks["right_shoulder"]),
        "arm_length": dist_cm(landmarks["left_shoulder"], landmarks["left_wrist"]),
        "inseam": dist_cm(landmarks["crotch"], landmarks["left_ankle"]),
        "torso_length": dist_cm(landmarks["neck_base"], landmarks["crotch"]),
        "chest_circumference": ellipse_circumference_mm(
            distance_mm(scale, landmarks["chest_left"], landmarks["chest_right"]),
            DEPTH_RATIOS["chest"]) / 10.0,
        "waist_circumference": ellipse_circumference_mm(
            distance_mm(scale, landmarks["waist_left"], landmarks["waist_right"]),
            DEPTH_RATIOS["waist"]) / 10.0,
        "hip_circumference": ellipse_circumference_mm(
            distance_mm(scale, landmarks["hip_left"], landmarks["hip_right"]),
            DEPTH_RATIOS["hip"]) / 10.0,
    }

    confidence = dict(_BASE_CONFIDENCE)
    warnings: list[str] = []
    for key, value in values.items():
        lo, hi = PLAUSIBLE_RANGES_CM[key]
        if not (lo <= value <= hi):
            warnings.append(f"{key}={value:.1f}cm 이(가) 상식 범위({lo}~{hi}cm)를 벗어남")
            confidence[key] = "low"

    measurements = {
        **{k: round(v, 1) for k, v in values.items()},
        "confidence": confidence,
        "mode": mode,
        "reference": reference,
    }
    return measurements, warnings


def points_px_to_plane_mm(scale: dict, points_px: list | np.ndarray) -> np.ndarray:
    """이미지 px 좌표들을 기준물 평면 mm 좌표로 변환한다 (원근 제거).

    ⚠️ 기준물과 같은 평면에 있는 점에서만 정확 (모듈 docstring 전제 2).
    """
    homography = np.asarray(scale["homographyPx2Mm"], dtype=np.float64)
    pts = np.asarray(points_px, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, homography).reshape(-1, 2)


def distance_mm(scale: dict, p1_px, p2_px) -> float:
    """이미지 위 두 점(px) 사이의 실제 거리(mm) — 기준물 평면 기준."""
    mm = points_px_to_plane_mm(scale, [p1_px, p2_px])
    return float(np.linalg.norm(mm[1] - mm[0]))
