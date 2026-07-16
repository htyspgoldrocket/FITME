"""Phase 2-7b 자동 검증 — 키 캘리브레이션·스칼라 척도·BMI 보정 (measure.py).

전부 합성 데이터 (API 호출 0). 실사진 3장(v1/v2/v3) 종합 검증은
scripts/verify_27b.py (로컬 전용 fixture 필요) 참조.
"""

import pytest

from services import measure
from services.measure import (
    bmi_depth_ratios,
    check_scale_agreement,
    compute_scale,
    height_scale_from_runs,
    landmarks_to_measurements,
    measure_with_statistics,
    scalar_distance_mm,
)

# 해부학 비율·상식 범위·대칭성을 모두 만족하는 합성 전신 랜드마크.
# head_top↔heel_mid = 1400px — 키 172cm 입력 시 척도 1720/1400 ≈ 1.2286 mm/px.
BASE_LANDMARKS = {
    "head_top": [500.0, 100.0],
    "neck_base": [500.0, 290.0],
    "left_shoulder": [350.0, 300.0],
    "right_shoulder": [650.0, 300.0],
    "chest_left": [390.0, 400.0],
    "chest_right": [610.0, 400.0],
    "waist_left": [400.0, 600.0],
    "waist_right": [600.0, 600.0],
    "hip_left": [395.0, 750.0],
    "hip_right": [605.0, 750.0],
    "left_wrist": [330.0, 800.0],
    "crotch": [500.0, 850.0],
    "left_ankle": [470.0, 1450.0],
    "left_heel": [480.0, 1500.0],
    "right_heel": [520.0, 1500.0],
}

HEIGHT_CM = 172.0
HEIGHT_MM_PER_PX = HEIGHT_CM * 10.0 / 1400.0  # ≈ 1.22857


def _marker_ref(width_px: float = 60.0, real_mm: float | None = None) -> dict:
    """정면(기울기 없음) 정사각 마커 ref. real_mm 기본값은 키 척도와 일치하도록
    설정 — 두 척도 agreement가 ok가 되는 조건 (마커 60px ≥ MIN_MARKER_WIDTH_PX)."""
    if real_mm is None:
        real_mm = HEIGHT_MM_PER_PX * width_px  # mmPerPx == 키 척도
    x0, y0 = 500.0, 700.0
    return {
        "type": "aruco",
        "realWidthMm": real_mm,
        "realHeightMm": real_mm,
        "detected": True,
        "cornersPx": [
            [x0, y0], [x0 + width_px, y0],
            [x0 + width_px, y0 + width_px], [x0, y0 + width_px],
        ],
    }


# ---------- 1) 스칼라 거리 ----------

def test_scalar_distance_mm_basic():
    """0.5mm/px × 200px = 100mm — 호모그래피 없이 유클리드 거리."""
    assert scalar_distance_mm(0.5, (300, 400), (500, 400)) == pytest.approx(100.0)


# ---------- 2) 키 캘리브레이션 척도 ----------

def test_height_scale_from_runs_uses_median():
    """head-heel 1400/1400/1410px 런 → 중앙값 1400px 기준 척도."""
    tall = dict(BASE_LANDMARKS, head_top=[500.0, 90.0])  # 1410px
    hs = height_scale_from_runs([BASE_LANDMARKS, BASE_LANDMARKS, tall], HEIGHT_CM)
    assert hs["mmPerPx"] == pytest.approx(HEIGHT_MM_PER_PX)
    assert hs["trace"]["headHeelPx"] == pytest.approx(1400.0)
    assert hs["trace"]["runs"] == 3


def test_height_scale_invalid_inputs():
    with pytest.raises(ValueError):
        height_scale_from_runs([BASE_LANDMARKS], 0.0)  # 키 0
    with pytest.raises(ValueError):
        height_scale_from_runs([], HEIGHT_CM)  # 빈 런


# ---------- 3) 두 척도 불일치 판정 ----------

def test_check_scale_agreement_three_levels():
    assert check_scale_agreement(1.04, 1.0)["level"] == "ok"
    mid = check_scale_agreement(1.10, 1.0)
    assert mid["level"] == "depth_bias" and mid["warnings"]
    bad = check_scale_agreement(1.30, 1.0)
    assert bad["level"] == "suspect" and bad["warnings"]
    # 반대 방향(마커가 더 큰 척도)도 대칭으로 판정
    assert check_scale_agreement(0.75, 1.0)["level"] == "suspect"


# ---------- 4) BMI 깊이 계수 ----------

def test_bmi_depth_ratios_bands():
    # 몸무게 없음 → 기본 계수 그대로
    assert bmi_depth_ratios(HEIGHT_CM, None) == measure.DEPTH_RATIOS
    # person01: 78.7kg, 172cm → BMI 26.6 → +0.05 구간
    adj = bmi_depth_ratios(HEIGHT_CM, 78.7)
    for k in measure.DEPTH_RATIOS:
        assert adj[k] == pytest.approx(measure.DEPTH_RATIOS[k] + 0.05)
    # 저체중 구간 → -0.05
    lean = bmi_depth_ratios(HEIGHT_CM, 50.0)  # BMI 16.9
    for k in measure.DEPTH_RATIOS:
        assert lean[k] == pytest.approx(measure.DEPTH_RATIOS[k] - 0.05)
    with pytest.raises(ValueError):
        bmi_depth_ratios(HEIGHT_CM, -1.0)


# ---------- 5) 키 앵커: 스칼라 경로로 입력 키 복원 ----------

def test_height_anchor_recovers_input_height():
    """키 척도를 주입하면 height가 정확히 입력 키로 복원된다 (캘리브레이션 자명성)."""
    scale = compute_scale(_marker_ref())
    m, warnings = landmarks_to_measurements(
        BASE_LANDMARKS, scale, "precise", _marker_ref(),
        length_mm_per_px=HEIGHT_MM_PER_PX, width_mm_per_px=HEIGHT_MM_PER_PX,
    )
    assert m["height"] == pytest.approx(HEIGHT_CM, abs=0.05)
    assert warnings == []  # 합성 체형은 상식 범위·비율 전부 통과해야 함


# ---------- 6) 통계 파이프라인: profile 유무 · suspect 강등 ----------

def _run_stats(ref, profile):
    scale = compute_scale(ref)
    runs = [BASE_LANDMARKS] * 3
    return measure_with_statistics(runs, scale, "precise", ref, profile=profile)


def test_statistics_with_profile_ok():
    """마커·키 척도 일치(ok): 강등 없음 — 길이 항목은 high 유지."""
    result = _run_stats(_marker_ref(), {"heightCm": HEIGHT_CM, "weightKg": None})
    assert result["stats"]["scale"]["source"] == "height"
    assert result["stats"]["scale"]["agreementLevel"] == "ok"
    assert result["measurements"]["height"] == pytest.approx(HEIGHT_CM, abs=0.05)
    assert result["measurements"]["confidence"]["height"] == "high"


def test_statistics_suspect_downgrades_all():
    """마커 척도가 키 척도와 20% 이상 어긋나면(suspect) 전 항목 1단계 강등."""
    ref = _marker_ref(real_mm=50.0)  # mmPerPx 0.833 vs 키 1.229 → r≈1.47
    result = _run_stats(ref, {"heightCm": HEIGHT_CM, "weightKg": None})
    assert result["stats"]["scale"]["agreementLevel"] == "suspect"
    assert any("척도 불일치" in w for w in result["warnings"])
    # ok 케이스에서 high였던 길이 항목이 medium으로 내려간다
    assert result["measurements"]["confidence"]["height"] == "medium"
    assert all(v != "high" for v in result["measurements"]["confidence"].values())


def test_statistics_without_profile_uses_marker_scalar():
    """profile 없음 → 마커 스칼라 폴백 (호모그래피 아님), agreement 없음."""
    result = _run_stats(_marker_ref(), None)
    s = result["stats"]["scale"]
    assert s["source"] == "marker"
    assert "agreementLevel" not in s
    assert s["bodyMmPerPx"] == pytest.approx(s["markerMmPerPx"])
    # 마커 real_mm이 키 척도와 일치하도록 만든 합성이므로 키도 172 근처
    assert result["measurements"]["height"] == pytest.approx(HEIGHT_CM, abs=0.1)


def test_statistics_bmi_increases_circumference():
    """몸무게(BMI 26.6, +0.05 구간) 입력 시 둘레가 미입력보다 커진다."""
    with_w = _run_stats(_marker_ref(), {"heightCm": HEIGHT_CM, "weightKg": 78.7})
    without = _run_stats(_marker_ref(), {"heightCm": HEIGHT_CM, "weightKg": None})
    for k in ("chest_circumference", "waist_circumference", "hip_circumference"):
        assert with_w["measurements"][k] > without["measurements"][k]
