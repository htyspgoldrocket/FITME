# -*- coding: utf-8 -*-
"""3-4 POST /clothing 라우트 + SQLite 캐시 테스트 — 전부 오프라인.

스크래핑은 routes.clothing.scrape_musinsa를 monkeypatch로 대체 (Playwright
미기동). 캐시 DB는 tmp_path로 격리 — 실제 DB 파일을 건드리지 않는다.
"""
import time

import pytest
from fastapi.testclient import TestClient

import routes.clothing as clothing_route
from main import app
from services import clothing_store
from services.clothing_scrape import ClothingScrapeError

client = TestClient(app)

MUSINSA_URL = "https://www.musinsa.com/products/6516683"

RAW_OUTER = {
    "source": "musinsa",
    "url": MUSINSA_URL,
    "brand": "아크테릭스",
    "productName": "세륨 SL 후디 남성",
    "categoryPath": ["스포츠/레저", "아우터", "기타 점퍼/재킷"],
    "typeName": "점퍼",
    "sizes": [
        {"label": "S", "measurements": {
            "총장": 65.0, "어깨너비": 45.0, "가슴단면": 52.5, "소매길이": 63.0}},
    ],
}


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """테스트마다 빈 SQLite 캐시로 격리."""
    db = tmp_path / "cache.sqlite"
    monkeypatch.setattr(clothing_store, "DB_PATH", db)
    return db


# ---------- 라우트 ----------

def test_missing_url_422(tmp_db):
    assert client.post("/clothing", json={}).status_code == 422


def test_unsupported_mall(tmp_db):
    """무신사가 아닌 URL → ok=False + unsupported (Playwright 미기동 경로)."""
    res = client.post("/clothing", json={"url": "https://example.com/item/1"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["code"] == "unsupported"
    assert "무신사" in body["error"]
    assert "spec" not in body  # exclude_none


def test_success_and_cache(tmp_db, monkeypatch):
    calls = []

    def fake_scrape(url, timeout_ms=15000):
        calls.append(url)
        return RAW_OUTER

    monkeypatch.setattr(clothing_route, "scrape_musinsa", fake_scrape)

    # 1회차: 스크래핑 경유
    body = client.post("/clothing", json={"url": MUSINSA_URL}).json()
    assert body["ok"] is True
    assert body["cached"] is False
    spec = body["spec"]
    assert spec["brand"] == "아크테릭스"
    assert spec["category"] == "outer"
    assert spec["sizes"][0]["chest_cm"] == 105.0  # 가슴단면 52.5 × 2 (3-3 정규화 통과)
    assert len(calls) == 1

    # 2회차: 캐시 적중 — 스크래핑 없이 동일 스펙
    body2 = client.post("/clothing", json={"url": MUSINSA_URL}).json()
    assert body2["ok"] is True
    assert body2["cached"] is True
    assert body2["spec"] == spec
    assert len(calls) == 1  # 재호출 없음


def test_scrape_error_passthrough_and_not_cached(tmp_db, monkeypatch):
    """실패는 ok=False로 전달되고 캐시에 저장되지 않는다."""
    def fail_scrape(url, timeout_ms=15000):
        raise ClothingScrapeError("not-found", "상품을 찾지 못했어요")

    monkeypatch.setattr(clothing_route, "scrape_musinsa", fail_scrape)
    body = client.post("/clothing", json={"url": MUSINSA_URL}).json()
    assert body["ok"] is False
    assert body["code"] == "not-found"
    assert "상품" in body["error"]

    # 실패 후 성공 스크래핑으로 바꾸면 캐시가 아니라 재스크래핑 경유여야 함
    monkeypatch.setattr(clothing_route, "scrape_musinsa", lambda url, timeout_ms=15000: RAW_OUTER)
    body2 = client.post("/clothing", json={"url": MUSINSA_URL}).json()
    assert body2["ok"] is True
    assert body2["cached"] is False


# ---------- 캐시 스토어 단위 ----------

def test_store_roundtrip_unicode(tmp_db):
    spec = {"brand": "아크테릭스", "sizes": [{"label": "M", "chest_cm": 111.0}]}
    clothing_store.put("musinsa:1", spec)
    assert clothing_store.get_cached("musinsa:1") == spec
    assert clothing_store.get_cached("musinsa:2") is None


def test_store_ttl_expiry(tmp_db, monkeypatch):
    clothing_store.put("musinsa:1", {"brand": "x"})
    real_time = time.time
    monkeypatch.setattr(
        clothing_store.time, "time",
        lambda: real_time() + clothing_store.TTL_SECONDS + 60,
    )
    assert clothing_store.get_cached("musinsa:1") is None
