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
#
# 계수 출처 (2-7b 역산, 2026-07-16): person01 v2(밀착 의류·기하학적 최적 기준
#   사진)의 A척도(키 캘리브레이션) 폭 원자료 × truth_v2 실측 둘레에서 역산.
#   d = 2×실측둘레/(π×폭) − 1, 여기서 person01의 BMI 26.6 구간 가감(+0.05,
#   BMI_DEPTH_ADJUST)을 제외한 base 값. 역산 스크립트: scripts/verify_27b.py.
# ⚠️ 표본 1명(person01) 역산값 — 일반화 미검증. 절대 정확도는 알려진 한계
#   (CLAUDE.md 12장). 문헌 인용 배제 정책(13-2) 유지. 편향 일정성 가정의 실질
#   검증은 Phase 4 수동 검증(아는 옷 대조)이 담당.
# ⚠️ waist는 옵션 A(허리 정의 → 가슴·엉덩이의 기하 중간점, 2026-07-16 확정) 후
#   신정의 캐시로 재역산한 값. 구정의 시절의 이상치(0.9740 — natural waist 폭
#   과소의 흡수값)가 정상 범위로 해소됨. chest/hip/어깨 계수는 구정의 배치
#   역산값 유지 — 신정의 배치로 재역산하면 chest 0.7591/hip 0.7780/어깨 1.1843
#   으로 약간 다른데(배치 간 드리프트, PROGRESS 배운 것 31번), 이 차이 자체가
#   표본 1명 계수의 불확실성 규모다. 둘레 3종의 반복 일관성은 알려진 한계
#   (CLAUDE.md 12장 — 옵션 B, 2026-07-16 사용자 결정).
DEPTH_RATIOS = {
    "chest": 0.7681,
    "waist": 0.7273,
    "hip": 0.8331,
}

# ----- 정의 보정 계수 (전략 2 — 줄자 곡면 vs 카메라 직선 투영) -----
# 어깨: 줄자는 어깨 곡면을 따라 재지만 카메라는 직선 투영 폭만 본다.
# person01 v2 A척도 역산: 46.0cm(실측) / 38.907cm(측정) = 1.1823.
# ⚠️ 표본 1명 역산값 — 일반화 미검증 (위 DEPTH_RATIOS 주석과 동일 정책).
SHOULDER_CURVE_COEF = 1.1823

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
    landmarks: dict, scale: dict, mode: str, reference: dict,
    *,
    length_mm_per_px: float | None = None,
    width_mm_per_px: float | None = None,
    depth_ratios: dict | None = None,
) -> tuple[dict, list[str]]:
    """15개 랜드마크(2-5) × 척도(2-4) → BodyMeasurements 형태의 dict.

    매핑 (claude_vision.py의 랜드마크 정의와 1:1):
      키:        head_top ↔ 발뒤꿈치 중점        (직접 거리)
      어깨너비:  left_shoulder ↔ right_shoulder  (직접 거리)
      팔길이:    left_shoulder ↔ left_wrist      (직접 거리)
      다리안쪽:  crotch ↔ left_ankle             (직접 거리)
      상체길이:  neck_base ↔ crotch              (직접 거리)
      가슴/허리/엉덩이 둘레: 좌우 실루엣 너비 → 타원 근사

    척도 선택 (2-7b): length_mm_per_px / width_mm_per_px 를 주면 해당 그룹
    (길이 = 키·팔·다리안쪽·상체 / 폭 = 어깨·둘레 3종)을 **스칼라 척도**로 잰다.
    None이면 기존 호모그래피 경로(2-4) — 단 v3 실증(원거리 외삽 폭주)에 따라
    신규 코드는 스칼라 척도 사용을 권장. depth_ratios 로 타원 깊이 계수를
    교체할 수 있다 (BMI 보정 — bmi_depth_ratios() 반환값. None이면 기본값).

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

    ratios = depth_ratios if depth_ratios is not None else DEPTH_RATIOS

    def length_mm(p1, p2) -> float:
        if length_mm_per_px is not None:
            return scalar_distance_mm(length_mm_per_px, p1, p2)
        return distance_mm(scale, p1, p2)

    def width_mm(p1, p2) -> float:
        if width_mm_per_px is not None:
            return scalar_distance_mm(width_mm_per_px, p1, p2)
        return distance_mm(scale, p1, p2)

    values = {
        "height": length_mm(landmarks["head_top"], heel_mid) / 10.0,
        "shoulder_width": width_mm(
            landmarks["left_shoulder"], landmarks["right_shoulder"])
            / 10.0 * SHOULDER_CURVE_COEF,
        "arm_length": length_mm(landmarks["left_shoulder"], landmarks["left_wrist"]) / 10.0,
        "inseam": length_mm(landmarks["crotch"], landmarks["left_ankle"]) / 10.0,
        "torso_length": length_mm(landmarks["neck_base"], landmarks["crotch"]) / 10.0,
        "chest_circumference": ellipse_circumference_mm(
            width_mm(landmarks["chest_left"], landmarks["chest_right"]),
            ratios["chest"]) / 10.0,
        "waist_circumference": ellipse_circumference_mm(
            width_mm(landmarks["waist_left"], landmarks["waist_right"]),
            ratios["waist"]) / 10.0,
        "hip_circumference": ellipse_circumference_mm(
            width_mm(landmarks["hip_left"], landmarks["hip_right"]),
            ratios["hip"]) / 10.0,
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
# 마커 크기 임계 — 40→60 상향 (2026-07-16 실증: v1 59.9px는 Gate 7/8,
# v2 42px는 4/8 — 마커 크기가 반복 편차의 지배 변수. 60px ≈ 1.2mm/px 이하 확보)
MIN_MARKER_WIDTH_PX = 60.0  # 마커가 이보다 작으면 척도 노이즈 증폭 → 한 단계 강등
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


# ----- 좌우 대칭성 검사 (촬영 가이드 층위 4, 2-7c — 해부학 검증의 확장) -----
# 정면 촬영이면 좌우 랜드마크 쌍이 몸 중심선에서 비슷한 거리에 있어야 한다.
# 비대칭 = 몸이 돌아섰거나 광각 가장자리 왜곡 → 좌우 폭 기반 항목을 불신.
# ⚠️ 허용치 근거: 추정 — 자연스러운 자세 편차를 감안한 넉넉한 값.
# 몸통 4쌍만 검사한다. 발뒤꿈치 쌍은 제외 — 정면으로 서 있어도 발 벌림·체중
# 이동으로 자연스럽게 비대칭이며(실측 36%), 몸통 회전 지표가 아니고 좌우 폭
# 측정에도 쓰이지 않는다 (2-7c 검증에서 실증).
SYMMETRY_PAIRS = [
    ("left_shoulder", "right_shoulder"),
    ("chest_left", "chest_right"),
    ("waist_left", "waist_right"),
    ("hip_left", "hip_right"),
]
SYMMETRY_TOLERANCE = 0.25  # |좌거리-우거리| / max(...) 가 25% 초과면 경고 — 추정
# 비대칭 시 신뢰도를 강등할 "좌우 폭 기반" 항목
_SYMMETRY_AFFECTED_KEYS = ("shoulder_width",) + _CIRCUMFERENCE_KEYS


def check_symmetry(landmarks: dict) -> list[str]:
    """좌우 대칭성 검사 — 비대칭 쌍을 경고 문자열로 반환."""
    # 몸 중심선 x: 어깨 쌍과 엉덩이 쌍의 평균 (기울어진 카메라에도 안정적)
    mid_x = (
        landmarks["left_shoulder"][0] + landmarks["right_shoulder"][0]
        + landmarks["hip_left"][0] + landmarks["hip_right"][0]
    ) / 4.0
    warnings = []
    for left_key, right_key in SYMMETRY_PAIRS:
        d_left = mid_x - landmarks[left_key][0]
        d_right = landmarks[right_key][0] - mid_x
        if d_left <= 0 or d_right <= 0:
            warnings.append(f"좌우 교차 이상: {left_key}/{right_key}가 중심선 기준 뒤바뀜")
            continue
        asym = abs(d_left - d_right) / max(d_left, d_right)
        if asym > SYMMETRY_TOLERANCE:
            warnings.append(
                f"좌우 비대칭: {left_key}/{right_key} 편차 {asym:.0%} "
                f"(허용 {SYMMETRY_TOLERANCE:.0%} — 몸이 돌아섰거나 화면 가장자리 왜곡 의심)"
            )
    return warnings


# 히트맵 오버레이 위치용 (5-3b) — FitScore.part 이름과 1:1 대응
_PART_LANDMARK_PAIRS = {
    "chest": ("chest_left", "chest_right"),
    "waist": ("waist_left", "waist_right"),
    "hip": ("hip_left", "hip_right"),
    "shoulder": ("left_shoulder", "right_shoulder"),
}


def landmarks_by_part(median_landmarks: dict) -> dict:
    """부위별 대표 랜드마크(왼쪽 x·오른쪽 x·평균 y) — 히트맵 오버레이 위치용 (5-3b).

    좌표는 median_landmarks와 동일 좌표계(촬영 사진 픽셀) 그대로 반환한다.
    """
    result: dict[str, dict[str, float]] = {}
    for part, (left_key, right_key) in _PART_LANDMARK_PAIRS.items():
        if left_key not in median_landmarks or right_key not in median_landmarks:
            continue
        lx, ly = median_landmarks[left_key]
        rx, ry = median_landmarks[right_key]
        result[part] = {
            "leftX": round(lx, 1),
            "rightX": round(rx, 1),
            "y": round((ly + ry) / 2.0, 1),
        }
    return result


def median_and_stable_spread(runs_values: list[dict]) -> tuple[dict, dict]:
    """반복 측정값 → (항목별 중앙값, 신뢰도용 편차).

    신뢰도용 편차는 "보고되는 값(중앙값)"의 안정성이어야 한다.
    N≥5이면 연속 3개 묶음의 중앙값들 산포(중앙값 추정치의 반복 편차)를 쓰고,
    표본이 적으면 원시 산포(max-min)를 그대로 쓴다 (보수적).
    """
    median, raw_spread = aggregate_runs(runs_values)
    if len(runs_values) >= 5:
        groups = [runs_values[i:i + 3] for i in range(len(runs_values) - 2)]
        group_medians = [aggregate_runs(g)[0] for g in groups]
        spread = {
            k: float(max(gm[k] for gm in group_medians) - min(gm[k] for gm in group_medians))
            for k in PLAUSIBLE_RANGES_CM
        }
    else:
        spread = raw_spread
    return median, spread


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
    landmark_runs: list[dict], scale: dict, mode: str, reference: dict,
    profile: dict | None = None,
) -> dict:
    """여러 번 추출한 랜드마크(2-5)로 측정을 반복하고 통계로 합친다 (전략 3).

    landmark_runs: extract_body_landmarks() 결과 N개 (프레임별 또는 반복 호출분).
    profile: UserProfile dict {"heightCm": float, "weightKg": float|None} (2-7b).

    척도 선택 (2-7b A안 확정 — v1/v2/v3 검증으로 결정, verify_27b.py):
      몸 측정은 항상 **스칼라 척도** (호모그래피 원거리 외삽은 v3 폭주 실증으로 폐기).
      - profile 있음 → 키 캘리브레이션 척도(주 경로) + 마커와 교차 검증(r 판정)
        + BMI 둘레 깊이 보정. r이 suspect(>20%)면 전 항목 신뢰도 1단계 강등.
      - profile 없음 → 마커 스칼라 (2-8에서 키 입력 UI 연결 전의 폴백)

    반환: {
      "measurements": BodyMeasurements 형태 (중앙값 + 통계 기반 confidence),
      "warnings":     상식 범위 + 해부학 비율 + 척도 불일치 경고,
      "stats":        {"runs": N, "spreadCm": 항목별 반복 편차,
                       "scale": 사용 척도 요약 (역추적용)}
    }
    """
    marker_mpp = scale["mmPerPx"]
    scale_warnings: list[str] = []
    agreement = None
    if profile is not None:
        height_cm = float(profile["heightCm"])
        height_scale = height_scale_from_runs(landmark_runs, height_cm)
        body_mpp = height_scale["mmPerPx"]
        agreement = check_scale_agreement(body_mpp, marker_mpp)
        scale_warnings.extend(agreement["warnings"])
        ratios = bmi_depth_ratios(height_cm, profile.get("weightKg"))
    else:
        body_mpp = marker_mpp
        ratios = None

    runs_values = []
    for lm in landmark_runs:
        m, _ = landmarks_to_measurements(
            lm, scale, mode, reference,
            length_mm_per_px=body_mpp, width_mm_per_px=body_mpp,
            depth_ratios=ratios,
        )
        runs_values.append({k: m[k] for k in PLAUSIBLE_RANGES_CM})

    median, spread = median_and_stable_spread(runs_values)

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

    # 좌우 대칭성 검사 (층위 4) — 중앙값 랜드마크로 1회 판정.
    # 비대칭이면 좌우 폭 기반 항목(어깨·둘레)의 신뢰도를 한 단계 강등.
    median_landmarks = {
        k: [
            float(np.median([lm[k][0] for lm in landmark_runs])),
            float(np.median([lm[k][1] for lm in landmark_runs])),
        ]
        for k in landmark_runs[0]
    }
    symmetry_warnings = check_symmetry(median_landmarks)
    if symmetry_warnings:
        warnings.extend(symmetry_warnings)
        for key in _SYMMETRY_AFFECTED_KEYS:
            confidence[key] = _LEVEL_DOWN[confidence[key]]

    # 척도 불일치 (2-7b): suspect(키 입력 오류·마커 배율 오류 의심)면
    # 척도 자체를 못 믿으므로 전 항목 신뢰도를 1단계 강등한다.
    warnings.extend(scale_warnings)
    if agreement is not None and agreement["level"] == "suspect":
        for key in confidence:
            confidence[key] = _LEVEL_DOWN[confidence[key]]

    measurements = {
        **{k: round(v, 1) for k, v in median.items()},
        "confidence": confidence,
        "mode": mode,
        "reference": reference,
    }
    stats_scale = {
        "markerMmPerPx": round(marker_mpp, 4),
        "bodyMmPerPx": round(body_mpp, 4),
        "source": "height" if profile is not None else "marker",
    }
    if agreement is not None:
        stats_scale["agreementRatio"] = round(agreement["ratio"], 3)
        stats_scale["agreementLevel"] = agreement["level"]
    return {
        "measurements": measurements,
        "warnings": warnings,
        "stats": {
            "runs": len(runs_values),
            "spreadCm": {k: round(v, 2) for k, v in spread.items()},
            "scale": stats_scale,
        },
        "landmarks": landmarks_by_part(median_landmarks),
    }


# ========== Step 2-7b: 키 캘리브레이션 · 스칼라 척도 · BMI 둘레 보정 ==========
#
# v3 실증 (2026-07-16, PROGRESS 배운 것 29번): 마커 코너의 서브픽셀 노이즈가
# 호모그래피 원근 성분으로 흡수되면 원거리 외삽에서 폭주한다 (v3 키 +70.8cm).
# → 몸 측정은 스칼라 척도만 사용한다. 호모그래피는 마커 근방(기울기 판정,
#   /check-photo) 전용으로 남긴다.
#
# 두 척도의 역할 분담 (2-7b 설계, 사용자 승인):
#   마커 스칼라(mmPerPx)  = 검출·위치·기울기 판정 + 키 척도의 교차 검증
#                           (+ 폭 측정 후보 — 마커와 같은 깊이 평면)
#   키 척도               = 전신 길이 측정의 주 척도 (사용자 입력 heightCm 기준)

SCALE_AGREE_OK = 0.05    # |r-1| ≤ 5%: 두 척도 일치(정상) — 근거: 추정
SCALE_AGREE_WARN = 0.20  # ≤20%: 깊이 편향(정보성 경고) / 초과: 입력·마커 의심 — 추정


def scalar_distance_mm(mm_per_px: float, p1_px, p2_px) -> float:
    """스칼라 척도 거리: 픽셀 유클리드 거리 × mm/px (호모그래피 미사용)."""
    d = np.asarray(p1_px, dtype=np.float64) - np.asarray(p2_px, dtype=np.float64)
    return float(np.linalg.norm(d) * mm_per_px)


def height_scale_from_runs(landmark_runs: list[dict], height_cm: float) -> dict:
    """키 캘리브레이션 척도 — 사용자 입력 키(cm)로 전신 스케일을 확정한다.

    head_top ↔ 발뒤꿈치 중점의 픽셀 거리(런별 계산 후 **중앙값**)를 키와 대응.
    사진당 척도 1개로 고정한다 — 런별로 따로 캘리브레이션하면 head/heel 좌표
    노이즈가 전 항목에 전파되므로 중앙값 고정이 안정적 (2-7b 설계).
    """
    if height_cm <= 0:
        raise ValueError(f"키 입력이 유효하지 않습니다: {height_cm}cm")
    if not landmark_runs:
        raise ValueError("랜드마크 런이 비어 있습니다")
    px_list = []
    for lm in landmark_runs:
        heel_mid = [
            (lm["left_heel"][0] + lm["right_heel"][0]) / 2.0,
            (lm["left_heel"][1] + lm["right_heel"][1]) / 2.0,
        ]
        d = np.asarray(lm["head_top"], dtype=np.float64) - np.asarray(heel_mid)
        px_list.append(float(np.linalg.norm(d)))
    head_heel_px = float(np.median(px_list))
    if head_heel_px <= 0:
        raise ValueError("head_top↔heel 픽셀 거리가 0입니다")
    return {
        "mmPerPx": height_cm * 10.0 / head_heel_px,
        "trace": {
            "heightCm": height_cm,
            "headHeelPx": head_heel_px,
            "runs": len(landmark_runs),
        },
    }


def check_scale_agreement(height_mm_per_px: float, marker_mm_per_px: float) -> dict:
    """두 척도 불일치 판정. r = 키 척도 ÷ 마커 스칼라.

    반환: {"ratio", "level": ok|depth_bias|suspect, "warnings": [...]}
      ok         |r-1| ≤ 5%  — 정상
      depth_bias ≤ 20%       — 마커 평면(가슴)과 머리·발의 깊이 차 (정보성.
                               측정은 유효 — 항목별 척도가 각자 올바른 평면 기준)
      suspect    > 20%       — 키 입력 오류 또는 마커 출력 크기 오류 의심
                               → 호출측은 전 항목 신뢰도 1단계 강등할 것
    임계는 전부 추정 (13-2 문헌 배제 정책 — v1 r≈1.12, v2 r≈1.01 실측이 참고 근거).
    """
    r = height_mm_per_px / marker_mm_per_px
    dev = abs(r - 1.0)
    if dev <= SCALE_AGREE_OK:
        return {"ratio": r, "level": "ok", "warnings": []}
    if dev <= SCALE_AGREE_WARN:
        return {"ratio": r, "level": "depth_bias", "warnings": [
            f"척도 불일치 {dev:.0%} (키 척도/마커 척도={r:.3f}) — 마커 평면과 "
            "머리·발의 깊이 차이로 추정. 더 멀리서 촬영하면 줄어듭니다"
        ]}
    return {"ratio": r, "level": "suspect", "warnings": [
        f"척도 불일치 {dev:.0%} (키 척도/마커 척도={r:.3f}) — 키 입력 오류 또는 "
        "마커 출력 크기 오류 의심. 키 입력값과 마커 100% 배율 출력을 확인하세요"
    ]}


# BMI 구간별 타원 깊이 계수 가감 — 근거: 추정 (13-2 문헌 배제. 마른 체형은
# 단면이 납작하고 BMI가 높을수록 전후로 깊어진다는 상식 수준의 방향성만 반영).
# (BMI 상한, 깊이 계수 가감) — weightKg 없으면 적용하지 않는다.
BMI_DEPTH_ADJUST = [
    (18.5, -0.05),
    (25.0, 0.0),
    (30.0, +0.05),
    (float("inf"), +0.10),
]


def bmi_depth_ratios(height_cm: float, weight_kg: float | None) -> dict:
    """BMI로 타원 깊이 계수를 조정한 사본을 반환. weight_kg가 None이면 기본값."""
    if weight_kg is None:
        return dict(DEPTH_RATIOS)
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError(f"키/몸무게 입력이 유효하지 않습니다: {height_cm}cm, {weight_kg}kg")
    bmi = weight_kg / (height_cm / 100.0) ** 2
    adjust = next(adj for upper, adj in BMI_DEPTH_ADJUST if bmi < upper)
    return {k: v + adjust for k, v in DEPTH_RATIOS.items()}


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
