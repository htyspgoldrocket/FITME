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

from main import app  # noqa: E402, F401
