# -*- coding: utf-8 -*-
"""3-3 사이즈 정규화 테스트 — 전부 오프라인.

Gate 자동 검증 대응: "95"/"L"/"Free"/"38" 표기 → cm 정규화 (Free는
사용자 입력 요청 플래그). 원자료 형식은 3-2 실상품 캡처 축약.
"""
import pytest

from models.schemas import ClothingSpec
from services.clothing_normalize import (
    normalize_label,
    normalize_scraped,
    resolve_category,
)

# ---------- 3-2 실상품 캡처 축약 원자료 ----------

RAW_OUTER = {
    "source": "musinsa",
    "url": "https://www.musinsa.com/products/6516683",
    "brand": "아크테릭스",
    "productName": "세륨 SL 후디 남성",
    "categoryPath": ["스포츠/레저", "아우터", "기타 점퍼/재킷"],
    "imageUrl": "https://image.msscdn.net/images/goods_img/20190327/6516683/x_500.jpg",
    "typeName": "점퍼",
    "sizes": [
        {"label": "S", "measurements": {
            "총장": 65.0, "어깨너비": 45.0, "가슴단면": 52.5, "소매길이": 63.0}},
        {"label": "M", "measurements": {
            "총장": 67.0, "어깨너비": 47.0, "가슴단면": 55.5, "소매길이": 64.5}},
    ],
}

RAW_PANTS = {
    "source": "musinsa",
    "url": "https://www.musinsa.com/products/6719352",
    "brand": "토피",
    "productName": "커브드 배럴 데님 팬츠",
    "categoryPath": ["바지", "데님 팬츠"],
    "typeName": "바지",
    "sizes": [
        {"label": "S", "measurements": {
            "총장": 104.0, "허리단면": 37.0, "엉덩이단면": 54.0,
            "허벅지단면": 34.0, "밑위": 32.0, "밑단단면": 22.0}},
    ],
}


def test_normalize_outer():
    spec = normalize_scraped(RAW_OUTER)
    assert spec["category"] == "outer"
    assert spec["brand"] == "아크테릭스"
    s = spec["sizes"][0]
    assert s == {
        "label": "S", "length_cm": 65.0, "shoulder_cm": 45.0,
        "chest_cm": 105.0, "sleeve_cm": 63.0,  # 가슴단면 52.5 × 2
    }
    assert "needsUserInput" not in spec
    assert "warnings" not in spec
    assert spec["imageUrl"] == (
        "https://image.msscdn.net/images/goods_img/20190327/6516683/x_500.jpg"
    )


def test_normalize_missing_image_url_not_faked():
    """imageUrl 없는 원자료 → spec에 키 자체가 없어야 함 (가짜 채움 금지, 규칙 1)."""
    spec = normalize_scraped(RAW_PANTS)
    assert "imageUrl" not in spec


def test_normalize_pants():
    spec = normalize_scraped(RAW_PANTS)
    assert spec["category"] == "bottom"
    s = spec["sizes"][0]
    assert s["waist_cm"] == 74.0      # 37 × 2
    assert s["hip_cm"] == 108.0       # 54 × 2
    assert s["thigh_cm"] == 68.0      # 34 × 2
    assert s["hem_cm"] == 44.0        # 22 × 2
    assert s["rise_cm"] == 32.0       # 직선값 그대로
    assert s["length_cm"] == 104.0


def test_normalized_passes_pydantic_contract():
    """정규화 출력이 ClothingSpec 계약(schemas.py)을 그대로 통과해야 한다."""
    for raw in (RAW_OUTER, RAW_PANTS):
        spec = ClothingSpec(**normalize_scraped(raw))
        assert spec.sizes[0].label == "S"


def test_unknown_part_warned_not_dropped_silently():
    raw = {**RAW_OUTER, "sizes": [
        {"label": "M", "measurements": {"가슴단면": 50.0, "신비부위": 12.3}},
    ]}
    spec = normalize_scraped(raw)
    assert spec["sizes"][0]["chest_cm"] == 100.0
    assert any("신비부위" in w for w in spec["warnings"])


# ---------- 호칭 폴백 (Gate: "95", "L", "38", "Free") ----------

def test_label_fallback_gate_cases():
    assert normalize_label("95", "top") == {"chest_cm": 95.0}
    assert normalize_label("L", "top") == {"chest_cm": 100.0}
    assert normalize_label("38", "bottom") == {"waist_cm": 96.5}   # 인치 × 2.54
    assert normalize_label("30", "bottom") == {"waist_cm": 76.2}
    assert normalize_label("76", "bottom") == {"waist_cm": 76.0}   # cm 호칭
    assert normalize_label("L", "bottom") == {"waist_cm": 81.0}
    assert normalize_label("Free", "top") is None                  # 변환 불가
    assert normalize_label("잘못된표기", "top") is None
    assert normalize_label("999", "top") is None                   # 범위 밖


def test_measurement_less_size_uses_label_fallback():
    raw = {**RAW_OUTER, "sizes": [{"label": "95", "measurements": {}}]}
    spec = normalize_scraped(raw)
    s = spec["sizes"][0]
    assert s["chest_cm"] == 95.0
    assert s["estimated"] is True
    assert any("근사치" in w for w in spec["warnings"])
    assert "needsUserInput" not in spec


def test_unconvertible_label_sets_needs_user_input():
    raw = {**RAW_OUTER, "sizes": [
        {"label": "Free", "measurements": {}},
        {"label": "M", "measurements": {"가슴단면": 55.0}},
    ]}
    spec = normalize_scraped(raw)
    assert spec["needsUserInput"] is True
    assert any("직접 입력" in w for w in spec["warnings"])
    assert spec["sizes"][0] == {"label": "Free"}       # 가짜 숫자 없음
    assert spec["sizes"][1]["chest_cm"] == 110.0       # 나머지는 정상
    ClothingSpec(**spec)  # 값 없는 사이즈도 계약 통과 (전 필드 선택)


# ---------- 카테고리 결정 ----------

@pytest.mark.parametrize(
    "path,type_name,expected",
    [
        (["스포츠/레저", "아우터"], "점퍼", "outer"),
        (["바지", "데님 팬츠"], "바지", "bottom"),
        (["원피스/스커트", "원피스"], "원피스", "dress"),
        ([], "티셔츠", "top"),
        (["상의", "긴소매 티셔츠"], "", "top"),
    ],
)
def test_resolve_category(path, type_name, expected):
    cat, warnings = resolve_category(path, type_name, set())
    assert cat == expected
    assert warnings == []


def test_resolve_category_heuristic_fallback():
    cat, warnings = resolve_category([], "", {"허리단면", "밑위"})
    assert cat == "bottom"
    assert warnings  # 추정임을 경고로 드러냄

    cat2, warnings2 = resolve_category([], "듣도보도못한종류", {"가슴단면"})
    assert cat2 == "top"
    assert warnings2


def test_dress_priority_over_top_keywords():
    """'원피스'가 '셔츠'류 키워드보다 우선 (배열 순서) — 셔츠 원피스 같은 복합명."""
    cat, _ = resolve_category(["원피스/스커트"], "셔츠 원피스", set())
    assert cat == "dress"
