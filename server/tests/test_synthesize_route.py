# -*- coding: utf-8 -*-
"""5-2c POST /synthesize 라우트 테스트 — 전부 오프라인 (services.vton.synthesize mock, API 0회).

Gate 대응: 합성용 이미지 없음/사진 데이터 손상/VTON 실패를 크래시 없이
ok=False + 한국어 error + code로 전달 (규칙 1).
"""
import base64

import pytest
from fastapi.testclient import TestClient

import routes.synthesize as synthesize_route
from main import app
from services.vton import VtonError

client = TestClient(app)

HUMAN_IMAGE = {
    "base64": base64.b64encode(b"fake-jpeg-bytes").decode("ascii"),
    "width": 1080,
    "height": 1440,
    "mimeType": "image/jpeg",
    "rotation": 0,
}


def make_clothing(**overrides):
    base = {
        "brand": "테스트", "url": "https://example.com/1", "category": "top",
        "productName": "테스트 티셔츠", "sizes": [{"label": "M", "chest_cm": 111.0}],
        "imageUrl": "https://image.msscdn.net/x.jpg",
    }
    base.update(overrides)
    return base


def test_success_returns_base64_image(monkeypatch):
    captured = {}

    def fake_synthesize(human_image, garment_image_url, clothing_category, garment_des=""):
        captured["garment_image_url"] = garment_image_url
        captured["category"] = clothing_category
        captured["garment_des"] = garment_des
        return b"synthesized-bytes"

    monkeypatch.setattr(synthesize_route, "synthesize", fake_synthesize)

    res = client.post(
        "/synthesize", json={"humanImage": HUMAN_IMAGE, "clothing": make_clothing()}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert base64.b64decode(data["imageBase64"]) == b"synthesized-bytes"
    assert captured["garment_image_url"] == "https://image.msscdn.net/x.jpg"
    assert captured["category"] == "top"
    assert captured["garment_des"] == "테스트 티셔츠"


def test_no_garment_image_short_circuits(monkeypatch):
    called = []
    monkeypatch.setattr(synthesize_route, "synthesize", lambda *a, **k: called.append(1))

    clothing = make_clothing()
    del clothing["imageUrl"]
    res = client.post("/synthesize", json={"humanImage": HUMAN_IMAGE, "clothing": clothing})

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["code"] == "no-garment-image"
    assert called == []  # VTON 호출 전에 걸러짐 (비용 0)


def test_bad_base64_human_image(monkeypatch):
    called = []
    monkeypatch.setattr(synthesize_route, "synthesize", lambda *a, **k: called.append(1))

    bad_image = {**HUMAN_IMAGE, "base64": "!!!not-base64!!!"}
    res = client.post(
        "/synthesize", json={"humanImage": bad_image, "clothing": make_clothing()}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["code"] == "synthesis-failed"
    assert called == []


def test_vton_error_propagates(monkeypatch):
    def fake_synthesize(*a, **k):
        raise VtonError("unsupported-category", "지원하지 않는 의류 종류예요: shoes")

    monkeypatch.setattr(synthesize_route, "synthesize", fake_synthesize)

    res = client.post(
        "/synthesize", json={"humanImage": HUMAN_IMAGE, "clothing": make_clothing()}
    )
    data = res.json()
    assert data["ok"] is False
    assert data["code"] == "unsupported-category"
    assert "shoes" in data["error"]


def test_missing_fields_422():
    res = client.post("/synthesize", json={"humanImage": HUMAN_IMAGE})
    assert res.status_code == 422
