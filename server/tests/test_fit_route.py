# -*- coding: utf-8 -*-
"""4-4a POST /fit 라우트 테스트 — 전부 오프라인 (feedback mock, API 0회).

Gate 자동 검증 대응: BodyMeasurements+ClothingSpec → FitResult 산출,
신뢰도 low가 핏 결과에 반영, 추천 불가 시 명확한 에러 (가짜 사이즈 없음).
"""
import pytest
from fastapi.testclient import TestClient

import routes.fit as fit_route
from main import app
from tests.test_fit import make_body

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_feedback(monkeypatch):
    """라우트의 generate_feedback를 템플릿 강제(use_api 경로 차단)로 대체."""
    from services.fit_feedback import generate_feedback

    monkeypatch.setattr(
        fit_route, "generate_feedback",
        lambda m, s, r: generate_feedback(m, s, r, use_api=False),
    )


def make_clothing(sizes, category="top"):
    return {
        "brand": "테스트", "url": "https://example.com/1", "category": category,
        "productName": "테스트 상품", "sizes": sizes,
    }


BODY = make_body().model_dump()


def test_success_returns_fit_result():
    clothing = make_clothing([
        {"label": "S", "chest_cm": 106.0, "shoulder_cm": 47.0},
        {"label": "M", "chest_cm": 111.0, "shoulder_cm": 47.0},
        {"label": "L", "chest_cm": 116.0, "shoulder_cm": 47.0},
    ])
    res = client.post("/fit", json={"measurements": BODY, "clothing": clothing})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    result = data["result"]
    assert result["recommendedSize"] == "M"
    # scores는 추천 사이즈(M)의 판정만 — chest good +11
    parts = {s["part"]: s for s in result["scores"]}
    assert parts["chest"]["status"] == "good"
    assert parts["chest"]["diff_cm"] == 11.0
    assert "'M'" in result["recommendation"]  # 템플릿 경로 문구
    assert data["warnings"] == []


def test_low_confidence_reflected_in_result():
    """Gate: 측정 신뢰도 low 부위 → 핏 결과 scores에도 low 표시."""
    clothing = make_clothing([{"label": "M", "chest_cm": 111.0, "shoulder_cm": 47.0}])
    res = client.post("/fit", json={"measurements": BODY, "clothing": clothing})
    parts = {s["part"]: s for s in res.json()["result"]["scores"]}
    assert parts["chest"]["confidence"] == "low"
    assert parts["shoulder"]["confidence"] == "high"


def test_insufficient_passes_warning():
    """A안: 전 사이즈 허리 tight → ok=True + XL + 경고 전달."""
    clothing = make_clothing(
        [{"label": "L", "waist_cm": 80.0, "hip_cm": 110.0},
         {"label": "XL", "waist_cm": 86.0, "hip_cm": 114.0}],
        category="bottom",
    )
    res = client.post("/fit", json={"measurements": BODY, "clothing": clothing})
    data = res.json()
    assert data["ok"] is True
    assert data["result"]["recommendedSize"] == "XL"
    assert any("작을 수 있어요" in w for w in data["warnings"])


def test_no_comparable_sizes_is_honest_error():
    """추천 불가 → ok=False + 한국어 사유, 가짜 사이즈 없음."""
    clothing = make_clothing([{"label": "Free", "length_cm": 100.0}])
    res = client.post("/fit", json={"measurements": BODY, "clothing": clothing})
    data = res.json()
    assert data["ok"] is False
    assert "result" not in data  # exclude_none
    assert "추천이 어려워요" in data["error"]


def test_missing_fields_422():
    assert client.post("/fit", json={"measurements": BODY}).status_code == 422
