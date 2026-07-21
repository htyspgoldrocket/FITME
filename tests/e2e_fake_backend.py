# -*- coding: utf-8 -*-
"""E2E fake backend (2-8e).

Real FastAPI app with ONLY the Claude Vision call replaced by synthetic
landmarks -- detection, scale, statistics and calibration all run for real,
with zero AI cost. Production code is untouched (patched at import time).

Run from repo root:
  server\\venv\\Scripts\\python.exe -m uvicorn tests.e2e_fake_backend:app --port 8000

Landmarks match server/tests/test_analyze.py (head-heel 1400px), so with
profile heightCm=172 the pipeline returns height exactly 172.0.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import routes.analyze as analyze_route  # noqa: E402
import routes.clothing as clothing_route  # noqa: E402
import routes.fit as fit_route  # noqa: E402
from services import clothing_store  # noqa: E402
from services.fit_feedback import generate_feedback  # noqa: E402

FAKE_LANDMARKS = {
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


# FITME_E2E_ASYM=1: shift left shoulder inward -> >25% asymmetry on all pairs
# (tests the layer-4 retake recommendation, 2-8f)
if os.environ.get("FITME_E2E_ASYM") == "1":
    FAKE_LANDMARKS["left_shoulder"] = [430.0, 300.0]


def _fake_extract(image_base64, width, height, mime_type="image/jpeg"):
    return {k: list(v) for k, v in FAKE_LANDMARKS.items()}


analyze_route.extract_body_landmarks = _fake_extract


# FITME_E2E_NOBODY=1: every frame's landmark extraction fails -> /analyze
# returns ok:false with the reference still detected for real (tests the B-4
# failure view WITH the green detection overlay + body-stage causes).
if os.environ.get("FITME_E2E_NOBODY") == "1":
    def _fail_extract(image_base64, width, height, mime_type="image/jpeg"):
        raise ValueError("E2E: forced landmark failure")

    analyze_route.extract_body_landmarks = _fail_extract


# FITME_E2E_NODETECT=1: reference detection misses -> /analyze returns
# ok:false, detected:false (B-4 failure view WITHOUT overlay + reference-stage
# causes). Only /analyze is patched -- /check-photo keeps the real detector,
# so the layer-3 auto-shoot still fires during the E2E run.
if os.environ.get("FITME_E2E_NODETECT") == "1":
    def _miss_detect(image):
        return {
            "type": "aruco",
            "realWidthMm": 70.0,
            "realHeightMm": 70.0,
            "detected": False,
            "cornersPx": None,
        }

    analyze_route.detect_aruco = _miss_detect
    analyze_route.detect_card = _miss_detect


# --- clothing (3-4b): replace only the Musinsa scrape -- normalization (3-3),
# route logic and the SQLite cache (3-4a) all run for real, offline.
# Cache DB goes to a per-process temp file so the real DB is never touched
# and every E2E run starts cold.
FAKE_RAW_CLOTHING = {
    "source": "musinsa",
    "url": "https://www.musinsa.com/products/1234567",
    "brand": "E2E BRAND",
    "productName": "E2E test jacket",
    "categoryPath": ["아우터", "기타 점퍼/재킷"],
    "imageUrl": "https://example.com/fake-garment.jpg",
    "typeName": "점퍼",
    "sizes": [
        {"label": "S", "measurements": {
            "총장": 65.0, "어깨너비": 45.0, "가슴단면": 52.5, "소매길이": 63.0}},
        {"label": "M", "measurements": {
            "총장": 67.0, "어깨너비": 47.0, "가슴단면": 55.5, "소매길이": 64.5}},
    ],
}


def _fake_scrape(url, timeout_ms=15000):
    # Faithful to the real scrape_musinsa contract: non-Musinsa URLs raise
    # "unsupported" before any network access (same check, same error code).
    from services.clothing_scrape import ClothingScrapeError, parse_musinsa_url

    if parse_musinsa_url(url) is None:
        raise ClothingScrapeError(
            "unsupported",
            "무신사 상품 주소(musinsa.com/products/…)만 지원해요 — 다른 쇼핑몰은 순차 확대 예정",
        )
    return FAKE_RAW_CLOTHING


clothing_route.scrape_musinsa = _fake_scrape


# --- fit (4-4b): force the template path of the real feedback generator
# (use_api=False) -- recommendation logic (4-1/4-2) runs for real, zero AI cost.
fit_route.generate_feedback = (
    lambda m, s, r: generate_feedback(m, s, r, use_api=False)
)


# --- synthesize (5-2c/5-3c): replace only the VTON call -- route logic
# (imageUrl 검증, base64 디코딩) runs for real, zero Replicate cost.
import base64  # noqa: E402
import io  # noqa: E402

import routes.synthesize as synthesize_route  # noqa: E402

# 5-3d: 히트맵 밴드 위치를 실제로 검증하려면 1x1이 아닌, 원본과 종횡비가 같은
# (0.75 = 1080/1440, 5-3b에서 확인한 VTON 실측과 동일 비율) 단색 이미지가 필요하다
# (E2E가 스케일된 좌표에 밴드가 그려졌는지 픽셀로 확인, tests/e2e-synthesize.mjs).
try:
    from PIL import Image

    _buf = io.BytesIO()
    Image.new("RGB", (270, 360), color=(128, 128, 128)).save(_buf, format="JPEG")
    _FAKE_SYNTH_JPEG = _buf.getvalue()
except ImportError:
    # Pillow 없으면 1x1 최소 JPEG로 폴백 (렌더 여부만 확인 가능)
    _FAKE_SYNTH_JPEG = base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgK"
        "CgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkL"
        "EBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAAR"
        "CAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAA"
        "AAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oA"
        "DAMBAAIRAxEAPwCdABmX/9k="
    )


def _fake_synthesize(human_image, garment_image_url, clothing_category, garment_des=""):
    return _FAKE_SYNTH_JPEG


synthesize_route.synthesize = _fake_synthesize


import tempfile  # noqa: E402

_db_fd, _db_path = tempfile.mkstemp(suffix=".sqlite")
os.close(_db_fd)  # sqlite opens by path; a 0-byte existing file is a valid new DB
clothing_store.DB_PATH = Path(_db_path)

from main import app  # noqa: E402, F401
