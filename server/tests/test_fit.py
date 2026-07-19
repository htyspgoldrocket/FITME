# -*- coding: utf-8 -*-
"""4-1 핏 계산 테스트 — 전부 오프라인.

Gate 자동 검증 대응: 핏 판정 논리(몸<옷 → loose, 반대 → tight — 논리 역전
0건), 부위별 여유/부족 cm 숫자, 신뢰도 low 전파, 없는 부위 제외(규칙 1).
"""
import pytest

from models.schemas import BodyMeasurements, ClothingSize, ClothingSpec, ReferenceInfo
from services.fit import EASE_RANGES, recommend_size, score_parts


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

# ============================================================
# 4-2 — recommend_size (A안: 후보 전멸 시 덜 tight + insufficient)
# ============================================================

def make_spec(sizes, category="top", stretch=None):
    return ClothingSpec(
        brand="t", url="https://example.com/1", category=category,
        stretch=stretch, sizes=sizes,
    )


# 몸: 어깨 46 / 가슴·허리·엉덩이 100 (make_body 기본값)

def test_recommend_picks_closest_to_ideal():
    """가슴 이상 여유 +11 → 111이 정확히 이상값인 M 추천."""
    spec = make_spec([
        ClothingSize(label="S", chest_cm=106.0, shoulder_cm=47.0),
        ClothingSize(label="M", chest_cm=111.0, shoulder_cm=47.0),
        ClothingSize(label="L", chest_cm=116.0, shoulder_cm=47.0),
    ])
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] == "M"
    assert rec["insufficient"] is False
    assert rec["warnings"] == []


def test_tie_prefers_smaller_size():
    """이상값 ±같은 거리(109 vs 113) → 목록 앞(작은) 사이즈."""
    spec = make_spec([
        ClothingSize(label="S", chest_cm=109.0),
        ClothingSize(label="M", chest_cm=113.0),
    ])
    assert recommend_size(make_body(), spec)["recommendedSize"] == "S"


def test_tight_size_filtered_even_if_closest():
    """S가 거리상 가까워도 어깨 tight면 후보 탈락 → M 추천."""
    spec = make_spec([
        ClothingSize(label="S", chest_cm=111.0, shoulder_cm=44.5),  # 어깨 -1.5 tight
        ClothingSize(label="M", chest_cm=116.0, shoulder_cm=47.0),
    ])
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] == "M"
    assert rec["perSize"][0]["candidate"] is False


def test_loose_is_not_disqualifying():
    """관찰 1: 전 사이즈 어깨 loose(드롭숄더)여도 후보 유지 — 가슴 기준 선택."""
    spec = make_spec([
        ClothingSize(label="S", chest_cm=106.0, shoulder_cm=50.0),
        ClothingSize(label="M", chest_cm=111.0, shoulder_cm=52.0),
    ])
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] == "M"
    assert all(p["candidate"] for p in rec["perSize"])


def test_all_tight_returns_least_tight_with_flag():
    """A안: 전 사이즈 허리 tight → 가장 덜 부족한 XL + insufficient + 경고."""
    spec = make_spec([
        ClothingSize(label="L", waist_cm=80.0, hip_cm=110.0),
        ClothingSize(label="XL", waist_cm=86.0, hip_cm=114.0),
    ], category="bottom")
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] == "XL"
    assert rec["insufficient"] is True
    assert any("허리" in w and "실측 확인" in w for w in rec["warnings"])


def test_stretch_high_relaxes_circumference_bound():
    """가슴 여유 +1은 원래 tight(하한 +4)지만 stretch high(−4)면 후보."""
    sizes = [ClothingSize(label="S", chest_cm=101.0)]
    tight = recommend_size(make_body(), make_spec(sizes))
    assert tight["insufficient"] is True
    stretchy = recommend_size(make_body(), make_spec(sizes, stretch="high"))
    assert stretchy["recommendedSize"] == "S"
    assert stretchy["insufficient"] is False


def test_stretch_does_not_relax_shoulder():
    """완화는 둘레만 — 직선(어깨) tight는 stretch high여도 그대로."""
    sizes = [ClothingSize(label="S", chest_cm=111.0, shoulder_cm=44.0)]  # 어깨 -2
    rec = recommend_size(make_body(), make_spec(sizes, stretch="high"))
    assert rec["insufficient"] is True


def test_no_comparable_sizes_returns_none():
    spec = make_spec([ClothingSize(label="Free", length_cm=100.0)])
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] is None
    assert any("추천이 어려워요" in w for w in rec["warnings"])


def test_incomparable_size_skipped_but_others_used():
    spec = make_spec([
        ClothingSize(label="Free", length_cm=100.0),
        ClothingSize(label="M", chest_cm=111.0),
    ])
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] == "M"
    assert rec["perSize"][0]["candidate"] is False


def test_estimated_size_flagged_in_warnings():
    spec = make_spec([ClothingSize(label="95", chest_cm=111.0, estimated=True)])
    rec = recommend_size(make_body(), spec)
    assert rec["recommendedSize"] == "95"
    assert any("호칭 기반 근사" in w for w in rec["warnings"])


def test_bottom_category_is_hip_weighted():
    """하의: 허리 동일할 때 hip이 이상 여유(+8)에 가까운 사이즈 선택."""
    spec = make_spec([
        ClothingSize(label="M", waist_cm=104.0, hip_cm=108.0),  # hip +8 = 이상
        ClothingSize(label="L", waist_cm=104.0, hip_cm=114.0),  # hip +14
    ], category="bottom")
    assert recommend_size(make_body(), spec)["recommendedSize"] == "M"
