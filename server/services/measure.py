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
# 계수 정책 (2026-07-16, CLAUDE.md 13-2): 역산 캘리브레이션은 밀착 의류
#   기준 데이터 확보 후 수행한다. person01 반바지 데이터는 보정 기준이 아니라
#   파이프라인 확인 + 나쁜 조건 엣지 케이스용이다 (역할 재정의). 문헌 인용은
#   배제 — 우리 조건(마커 기반·옷 위 측정·정면 너비→둘레)에 맞는 연구가 없어
#   어정쩡한 인용은 "검증된 척" 착각을 만든다 (규칙 1). 아래 값은 역산 전
#   임시값이며, 절대 정확도는 미검증 상태다 (알려진 한계 — CLAUDE.md 12장).
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


# ========== Step 2-7: 전략 3 — 다중 측정 중앙값 · 해부학 비율 · 신뢰도 ==========

_CIRCUMFERENCE_KEYS = ("chest_circumference", "waist_circumference", "hip_circumference")

# 해부학 비율 범위 — ⚠️ 근거: "추정"이다. 일반 성인 체형에 대한 상식 수준의
# 넉넉한 범위이며 통계 문헌 인용이 아니다 (13-2 문헌 배제 정책과 일관).
# 벗어나면 "측정이 잘못됐을 가능성이 높다"는 경고이지 절대 판정이 아니다.
ANATOMY_RATIO_RANGES = {
    ("arm_length", "height"): (0.26, 0.42),          # 팔(어깨~손목)/키 — 추정
    ("shoulder_width", "height"): (0.18, 0.32),      # 어깨/키 — 추정
    ("inseam", "height"): (0.30, 0.55),              # 다리안쪽/키 — 추정
    ("torso_length", "height"): (0.26, 0.48),        # 상체(목~가랑이)/키 — 추정
    ("waist_circumference", "hip_circumference"): (0.55, 1.15),  # 허리/엉덩이 — 추정
}

# 신뢰도 산정 기준 (모두 이 상수로 관리):
SPREAD_HIGH_CM = 1.0        # 반복 편차 ≤1cm → high 후보
SPREAD_MEDIUM_CM = 2.0      # ≤2cm → medium (Gate 기준과 동일), >2cm → low
MIN_MARKER_WIDTH_PX = 40.0  # 마커가 이보다 작으면 척도 노이즈 증폭 → 한 단계 강등
TILT_RATIO_RANGE = (0.90, 1.10)  # 가로/세로 척도 비가 벗어나면 기준물 기울어짐 → 강등

_LEVEL_DOWN = {"high": "medium", "medium": "low", "low": "low"}


def check_anatomy(values: dict) -> list[str]:
    """해부학 비율 교차 검증 — 벗어난 조합을 경고 문자열로 반환."""
    warnings = []
    for (num_key, den_key), (lo, hi) in ANATOMY_RATIO_RANGES.items():
        num, den = values.get(num_key), values.get(den_key)
        if not num or not den:
            continue
        ratio = num / den
        if not (lo <= ratio <= hi):
            warnings.append(
                f"해부학 비율 이상: {num_key}/{den_key}={ratio:.2f} "
                f"(추정 정상범위 {lo}~{hi})"
            )
    return warnings


def aggregate_runs(runs_values: list[dict]) -> tuple[dict, dict]:
    """반복 측정값 목록 → (항목별 중앙값, 항목별 편차 max-min)."""
    if not runs_values:
        raise ValueError("측정 결과가 비어 있습니다")
    keys = PLAUSIBLE_RANGES_CM.keys()
    median = {
        k: float(np.median([r[k] for r in runs_values])) for k in keys
    }
    spread = {
        k: float(max(r[k] for r in runs_values) - min(r[k] for r in runs_values))
        for k in keys
    }
    return median, spread


def _confidence_level(key: str, spread_cm: float, marker_width_px: float,
                      tilt_ratio: float, in_range: bool) -> str:
    """항목별 신뢰도 산정. 기준: ① 반복 편차 ② 마커 크기 ③ 기준물 기울기 ④ 상식 범위."""
    if spread_cm <= SPREAD_HIGH_CM:
        level = "high"
    elif spread_cm <= SPREAD_MEDIUM_CM:
        level = "medium"
    else:
        level = "low"
    if marker_width_px < MIN_MARKER_WIDTH_PX:
        level = _LEVEL_DOWN[level]
    if not (TILT_RATIO_RANGE[0] <= tilt_ratio <= TILT_RATIO_RANGE[1]):
        level = _LEVEL_DOWN[level]
    # 둘레는 타원 "근사"라 단일 사진에서는 high를 주지 않는다 (2-6 정책 유지)
    if key in _CIRCUMFERENCE_KEYS and level == "high":
        level = "medium"
    if not in_range:
        level = "low"
    return level


def measure_with_statistics(
    landmark_runs: list[dict], scale: dict, mode: str, reference: dict
) -> dict:
    """여러 번 추출한 랜드마크(2-5)로 측정을 반복하고 통계로 합친다 (전략 3).

    landmark_runs: extract_body_landmarks() 결과 N개 (프레임별 또는 반복 호출분).
    반환: {
      "measurements": BodyMeasurements 형태 (중앙값 + 통계 기반 confidence),
      "warnings":     상식 범위 + 해부학 비율 경고,
      "stats":        {"runs": N, "spreadCm": 항목별 반복 편차}
    }
    """
    runs_values = []
    for lm in landmark_runs:
        m, _ = landmarks_to_measurements(lm, scale, mode, reference)
        runs_values.append({k: m[k] for k in PLAUSIBLE_RANGES_CM})

    median, raw_spread = aggregate_runs(runs_values)

    # 신뢰도용 편차는 "보고되는 값(중앙값)"의 안정성이어야 한다.
    # N≥5이면 연속 3개 묶음의 중앙값들 산포(중앙값 추정치의 반복 편차)를 쓰고,
    # 표본이 적으면 원시 산포를 그대로 쓴다 (보수적).
    if len(runs_values) >= 5:
        groups = [runs_values[i:i + 3] for i in range(len(runs_values) - 2)]
        group_medians = [aggregate_runs(g)[0] for g in groups]
        spread = {
            k: float(max(gm[k] for gm in group_medians) - min(gm[k] for gm in group_medians))
            for k in PLAUSIBLE_RANGES_CM
        }
    else:
        spread = raw_spread

    trace = scale["trace"]
    tilt_ratio = trace["mmPerPxWidth"] / trace["mmPerPxHeight"]
    marker_width_px = trace["widthPx"]

    warnings: list[str] = []
    confidence: dict[str, str] = {}
    for key, value in median.items():
        lo, hi = PLAUSIBLE_RANGES_CM[key]
        in_range = lo <= value <= hi
        if not in_range:
            warnings.append(f"{key}={value:.1f}cm 이(가) 상식 범위({lo}~{hi}cm)를 벗어남")
        confidence[key] = _confidence_level(
            key, spread[key], marker_width_px, tilt_ratio, in_range
        )
    warnings.extend(check_anatomy(median))

    measurements = {
        **{k: round(v, 1) for k, v in median.items()},
        "confidence": confidence,
        "mode": mode,
        "reference": reference,
    }
    return {
        "measurements": measurements,
        "warnings": warnings,
        "stats": {"runs": len(runs_values), "spreadCm": {k: round(v, 2) for k, v in spread.items()}},
    }


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
