# -*- coding: utf-8 -*-
"""5-2b VTON 서비스 테스트 — 전부 오프라인 (replicate.run은 monkeypatch로 대체, API 0회).

실 네트워크 검증은 CLI(services/vton.py <사진> <이미지URL> <category>) 또는
scripts/test_vton_standalone.py로 수동 수행 (5-1에서 완료).
"""
import io

import pytest
import replicate.exceptions

import services.vton as vton
from services.vton import VtonError, resolve_category, synthesize


# ---------- category 매핑 ----------

@pytest.mark.parametrize(
    "clothing_category,expected",
    [
        ("top", "upper_body"),
        ("outer", "upper_body"),
        ("bottom", "lower_body"),
        ("dress", "dresses"),
    ],
)
def test_resolve_category(clothing_category, expected):
    assert resolve_category(clothing_category) == expected


def test_resolve_category_unsupported():
    with pytest.raises(VtonError) as exc:
        resolve_category("unknown")
    assert exc.value.code == "unsupported-category"


# ---------- synthesize() ----------

class _FakeFileOutput:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


@pytest.fixture(autouse=True)
def _fake_token(monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_fake_token_for_tests")


def test_synthesize_success_extracts_bytes(monkeypatch):
    captured = {}

    def fake_run(model_ref, input):
        captured["model_ref"] = model_ref
        captured["input"] = input
        return _FakeFileOutput(b"fake-image-bytes")

    monkeypatch.setattr(vton.replicate, "run", fake_run)

    data = synthesize(io.BytesIO(b"human"), "https://example.com/garment.jpg", "top")

    assert data == b"fake-image-bytes"
    assert captured["model_ref"] == vton.MODEL_VERSION
    assert captured["input"]["garm_img"] == "https://example.com/garment.jpg"
    assert captured["input"]["category"] == "upper_body"
    assert captured["input"]["garment_des"] == "clothing item"  # 기본값


def test_synthesize_passes_garment_des(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        vton.replicate, "run",
        lambda model_ref, input: captured.update(input) or _FakeFileOutput(b"x"),
    )
    synthesize(io.BytesIO(b"h"), "https://x/g.jpg", "bottom", garment_des="청바지")
    assert captured["garment_des"] == "청바지"
    assert captured["category"] == "lower_body"


def test_synthesize_unsupported_category_skips_api_call(monkeypatch):
    called = []
    monkeypatch.setattr(vton.replicate, "run", lambda *a, **k: called.append(1))

    with pytest.raises(VtonError) as exc:
        synthesize(io.BytesIO(b"h"), "https://x/g.jpg", "shoes")

    assert exc.value.code == "unsupported-category"
    assert called == []  # API 호출 전에 걸러짐


def test_synthesize_replicate_error_wrapped(monkeypatch):
    def fake_run(model_ref, input):
        raise replicate.exceptions.ReplicateError(detail="boom")

    monkeypatch.setattr(vton.replicate, "run", fake_run)

    with pytest.raises(VtonError) as exc:
        synthesize(io.BytesIO(b"h"), "https://x/g.jpg", "top")
    assert exc.value.code == "synthesis-failed"


def test_synthesize_missing_output_bytes_raises(monkeypatch):
    monkeypatch.setattr(vton.replicate, "run", lambda model_ref, input: None)
    with pytest.raises(VtonError) as exc:
        synthesize(io.BytesIO(b"h"), "https://x/g.jpg", "top")
    assert exc.value.code == "synthesis-failed"


def test_synthesize_no_token_raises(monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.setattr(vton, "ENV_PATH", vton.ENV_PATH.parent / "does_not_exist.env")

    with pytest.raises(VtonError) as exc:
        synthesize(io.BytesIO(b"h"), "https://x/g.jpg", "top")
    assert exc.value.code == "no-token"


# ---------- _extract_bytes() ----------

def test_extract_bytes_from_list():
    assert vton._extract_bytes([_FakeFileOutput(b"y")]) == b"y"


def test_extract_bytes_none_for_unknown_type():
    assert vton._extract_bytes(12345) is None
