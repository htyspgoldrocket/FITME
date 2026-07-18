# -*- coding: utf-8 -*-
"""4-1 핏 계산 테스트 — 전부 오프라인.

Gate 자동 검증 대응: 핏 판정 논리(몸<옷 → loose, 반대 → tight — 논리 역전
0건), 부위별 여유/부족 cm 숫자, 신뢰도 low 전파, 없는 부위 제외(규칙 1).
"""
import pytest

from models.schemas import BodyMeasurements, ClothingSize, ReferenceInfo
from services.fit import EASE_RANGES, score_parts


def make_body(**overrides) -> BodyMeasurements:
    """person01 v2 실측 근사 기본값 — 필요한 필드만 바꿔 쓴다."""
    values = {
        "height": 172.0,
        "shoulder_width": 46.0,
        "chest_circumference": 100.0,
        "waist_circumference": 100.0,
        "hip_circumference": 100.0,
        "arm_length": 58.0,
        "inseam": 75.0,
        "torso_length": 60.0,
        "confidence": {
            "shoulder_width": "high",
            "chest_circumference": "low",
            "waist_circumference": "low",
            "hip_circumference": "low",
        },
        "mode": "precise",
        "reference": ReferenceInfo(
            type="aruco", realWidthMm=70.0, realHeightMm=70.0, detected=True
        ),
    }
    values.update(overrides)
    return BodyMeasurements(**values)


def by_part(scores):
    return {s.part: s for s in scores}


# ---------- 판정 논리 (논리 역전 0건) ----------

def test_much_bigger_garment_is_loose():
    scores = by_part(score_parts(make_body(), ClothingSize(label="XL", chest_cm=130.0)))
    assert scores["chest"].status == "loose"
    assert scores["chest"].diff_cm == 30.0  # 여유는 양수


def test_smaller_garment_is_tight():
    scores = by_part(score_parts(make_body(), ClothingSize(label="S", chest_cm=95.0)))
    assert scores["chest"].status == "tight"
    assert scores["chest"].diff_cm == -5.0  # 부족은 음수


def test_no_logic_inversion_across_range():
    """옷 치수를 몸보다 훨씬 작게→크게 훑어도 tight→good→loose 순서 유지."""
    body = make_body()
    last_rank = 0
    rank = {"tight": 1, "good": 2, "loose": 3}
    for garment in range(80, 140, 2):
        s = by_part(score_parts(body, ClothingSize(label="t", chest_cm=float(garment))))
        assert rank[s["chest"].status] >= last_rank  # 역행 없음
        last_rank = rank[s["chest"].status]


# ---------- 경계값 (EASE_RANGES — 추정 상수의 계약 고정) ----------

@pytest.mark.parametrize(
    "part,field,body_field",
    [
        ("chest", "chest_cm", "chest_circumference"),
        ("waist", "waist_cm", "waist_circumference"),
        ("hip", "hip_cm", "hip_circumference"),
        ("shoulder", "shoulder_cm", "shoulder_width"),
    ],
)
def test_boundaries_inclusive(part, field, body_field):
    body = make_body()
    base = getattr(body, body_field)
    lo, hi = EASE_RANGES[part]
    for ease, expected in [
        (lo - 0.1, "tight"),
        (lo, "good"),       # 경계는 good에 포함
        (hi, "good"),
        (hi + 0.1, "loose"),
    ]:
        size = ClothingSize(label="t", **{field: round(base + ease, 1)})
        s = by_part(score_parts(body, size))
        assert s[part].status == expected, f"{part} ease={ease}"


def test_shoulder_negative_ease_can_be_good():
    """어깨는 직선 치수라 -1cm까지 good (추정 경계) — 둘레와 기준이 다름."""
    scores = by_part(
        score_parts(make_body(), ClothingSize(label="t", shoulder_cm=45.0))
    )
    assert scores["shoulder"].diff_cm == -1.0
    assert scores["shoulder"].status == "good"


# ---------- 없는 부위 제외 (규칙 1) ----------

def test_missing_parts_excluded_not_fabricated():
    """상의형(가슴·어깨만) → 정확히 2개. 허리·엉덩이를 0으로 채우지 않는다."""
    size = ClothingSize(
        label="M", chest_cm=111.0, shoulder_cm=51.5, sleeve_cm=25.0, length_cm=70.5
    )
    scores = score_parts(make_body(), size)
    assert {s.part for s in scores} == {"chest", "shoulder"}


def test_bottom_type_maps_waist_hip_only():
    """하의형(허리·엉덩이·허벅지·밑위 등) → waist·hip 2개 (허벅지 등은 몸 항목 없음)."""
    size = ClothingSize(
        label="M", waist_cm=78.0, hip_cm=112.0, thigh_cm=70.0, rise_cm=33.0,
        length_cm=106.0, hem_cm=46.0,
    )
    scores = score_parts(make_body(), size)
    assert {s.part for s in scores} == {"waist", "hip"}


def test_no_measurable_parts_returns_empty():
    size = ClothingSize(label="Free", length_cm=100.0)  # 총장만 있는 옷
    assert score_parts(make_body(), size) == []


# ---------- 신뢰도 전파 ----------

def test_confidence_propagates_to_scores():
    size = ClothingSize(label="M", chest_cm=111.0, shoulder_cm=51.5)
    scores = by_part(score_parts(make_body(), size))
    assert scores["chest"].confidence == "low"      # 둘레 3종 한계 (12장)
    assert scores["shoulder"].confidence == "high"  # 어깨는 안정 항목


def test_confidence_missing_key_is_none():
    body = make_body(confidence={})
    scores = by_part(score_parts(body, ClothingSize(label="M", chest_cm=111.0)))
    assert scores["chest"].confidence is None


# ---------- 계약 (Pydantic 직렬화) ----------

def test_fitscore_contract_roundtrip():
    scores = score_parts(
        make_body(), ClothingSize(label="M", chest_cm=111.0, shoulder_cm=51.5)
    )
    for s in scores:
        dumped = s.model_dump(exclude_none=True)
        assert set(dumped) <= {"part", "status", "diff_cm", "confidence"}
        assert isinstance(dumped["diff_cm"], float)
