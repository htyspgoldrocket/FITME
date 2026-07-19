# -*- coding: utf-8 -*-
"""3-2 무신사 스크래핑 테스트 — 전부 오프라인 (네트워크·브라우저 0회).

순수 파싱 함수(parse_goods/parse_sizes)와 URL 판정을 검증한다.
API 응답 구조는 2026-07-17 실상품(6516683) 탐사 캡처를 축약한 것.
실 네트워크 검증은 CLI(services/clothing_scrape.py <url>)로 수동 수행.
"""
import pytest

from services.clothing_scrape import (
    ClothingScrapeError,
    parse_goods,
    parse_musinsa_url,
    parse_sizes,
)

# ---------- URL 판정 ----------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.musinsa.com/products/6516683", 6516683),
        ("https://musinsa.com/products/123", 123),
        ("http://m.musinsa.com/products/42?utm=x#review", 42),
        ("https://www.musinsa.com/products/6516683/other", 6516683),
    ],
)
def test_url_valid(url, expected):
    assert parse_musinsa_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://www.mssinsa.com/products/123",       # 유사 도메인
        "https://evil.com/https://musinsa.com/products/1",
        "https://www.musinsa.com/brand/arcteryx",     # 상품 페이지 아님
        "https://www.musinsa.com/products/abc",       # 숫자 아님
        "ftp://musinsa.com/products/1",
        "완전히 URL이 아님",
    ],
)
def test_url_invalid(url):
    assert parse_musinsa_url(url) is None


# ---------- 상품 정보 파싱 ----------

GOODS_DATA = {
    "goodsNo": 6516683,
    "goodsNm": "세륨 SL 후디 남성 - FORAGE / AJQSM11036",
    "brand": "arcteryx",
    "brandInfo": {"brandName": "아크테릭스", "brandEnglishName": "ARCTERYX"},
    "category": {
        "categoryDepth1Name": "스포츠/레저",
        "categoryDepth2Name": "아우터",
        "categoryDepth3Name": "기타 점퍼/재킷",
    },
}


def test_parse_goods():
    g = parse_goods(GOODS_DATA)
    assert g["goodsNo"] == 6516683
    assert g["brand"] == "아크테릭스"
    assert g["productName"].startswith("세륨 SL 후디")
    assert g["categoryPath"] == ["스포츠/레저", "아우터", "기타 점퍼/재킷"]


def test_parse_goods_missing_fields():
    g = parse_goods({"goodsNo": 1, "brand": "nobrand"})
    assert g["brand"] == "nobrand"  # brandInfo 없으면 영문 코드로 폴백
    assert g["categoryPath"] == []
    assert g["productName"] == ""


# ---------- 사이즈 파싱 ----------

SIZE_DATA = {
    "typeName": "점퍼",
    "sizes": [
        {
            "name": "S",
            "items": [
                {"name": "총장", "value": 65.0},
                {"name": "어깨너비", "value": 45.0},
                {"name": "가슴단면", "value": 52.5},
                {"name": "소매길이", "value": 63.0},
            ],
        },
        {
            "name": "M",
            "items": [
                {"name": "총장", "value": 67.0},
                {"name": "어깨너비", "value": 47.0},
                {"name": "가슴단면", "value": 55.5},
                {"name": "소매길이", "value": 64.5},
            ],
        },
    ],
}


def test_parse_sizes():
    s = parse_sizes(SIZE_DATA)
    assert s["typeName"] == "점퍼"
    assert [e["label"] for e in s["sizes"]] == ["S", "M"]
    assert s["sizes"][0]["measurements"] == {
        "총장": 65.0, "어깨너비": 45.0, "가슴단면": 52.5, "소매길이": 63.0,
    }


def test_parse_sizes_skips_bad_values():
    """값이 None·문자열인 항목, 빈 라벨은 조용히 제외 — 남는 게 있으면 성공."""
    s = parse_sizes({
        "typeName": "팬츠",
        "sizes": [
            {"name": "L", "items": [
                {"name": "허리단면", "value": None},
                {"name": "총장", "value": "측정 불가"},
                {"name": "밑위", "value": 30.5},
            ]},
            {"name": "", "items": [{"name": "총장", "value": 100.0}]},
        ],
    })
    assert s["sizes"] == [{"label": "L", "measurements": {"밑위": 30.5}}]


def test_parse_sizes_empty_raises():
    with pytest.raises(ClothingScrapeError) as ei:
        parse_sizes({"typeName": "양말", "sizes": []})
    assert ei.value.code == "no-size"
    assert "사이즈" in str(ei.value)  # 사용자 안내는 한국어


def test_parse_sizes_all_invalid_raises():
    with pytest.raises(ClothingScrapeError):
        parse_sizes({"sizes": [{"name": "F", "items": [{"name": "x", "value": None}]}]})

# ---------- 4-4 교정: actual-size SUCCESS + data:null = 실측 미제공 상품 ----------

def test_extract_size_data_null_is_no_size():
    """노스페이스 6113011 실증 케이스 — 정확한 안내로 구분."""
    from services.clothing_scrape import ClothingScrapeError, extract_size_data
    payload = {"meta": {"result": "SUCCESS"}, "data": None}
    with pytest.raises(ClothingScrapeError) as e:
        extract_size_data(payload)
    assert e.value.code == "no-size"
    assert "실측 사이즈 미제공" in str(e.value)


def test_extract_size_data_success_passthrough():
    from services.clothing_scrape import extract_size_data
    payload = {"meta": {"result": "SUCCESS"}, "data": {"sizes": []}}
    assert extract_size_data(payload) == {"sizes": []}


def test_extract_size_data_fail_meta_is_not_found():
    from services.clothing_scrape import ClothingScrapeError, extract_size_data
    with pytest.raises(ClothingScrapeError) as e:
        extract_size_data({"meta": {"result": "FAIL"}, "data": None})
    assert e.value.code == "not-found"
