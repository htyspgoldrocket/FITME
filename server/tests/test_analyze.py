"""Phase 2 자동 검증 — /analyze (2-8a: 실제 측정 파이프라인 배선) + /health.

CLAUDE.md 13-4: 검증 스크립트는 Phase마다 누적한다 (지우지 않음).
2-1의 stub 규격 검사는 실제 파이프라인 검사로 교체됨 (BodyMeasurements 형태
단언은 그대로 유지 — 프론트 계약).

전부 API 호출 0회: 랜드마크 추출(extract_body_landmarks)은 monkeypatch,
기준물 검출·척도·통계는 합성 마커 이미지로 실제 코드가 돈다.
"""

import base64

import cv2
import numpy as np
from fastapi.testclient import TestClient

import routes.analyze as analyze_route
from main import app
from services.reference_detect import ARUCO_DICT_ID, MARKER_ID

client = TestClient(app)

# ---------- 합성 입력 ----------

PAGE_SIZE = 800  # 합성 이미지 한 변 (px)


def _marker_page_b64(marker_side: int = 200) -> str:
    """흰 배경 중앙에 ArUco 마커가 놓인 합성 이미지 (PNG, 무손실)."""
    marker = cv2.aruco.generateImageMarker(
        cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID), MARKER_ID, marker_side
    )
    page = np.full((PAGE_SIZE, PAGE_SIZE), 255, dtype=np.uint8)
    off = (PAGE_SIZE - marker_side) // 2
    page[off : off + marker_side, off : off + marker_side] = marker
    ok, buf = cv2.imencode(".png", page)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


def _blank_page_b64() -> str:
    """기준물이 전혀 없는 흰 이미지 — 미검출 경로 검증용."""
    page = np.full((PAGE_SIZE, PAGE_SIZE, 3), 255, dtype=np.uint8)
    ok, buf = cv2.imencode(".png", page)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


def _image(b64: str, frames: list[str] | None = None) -> dict:
    img = {
        "base64": b64,
        "width": PAGE_SIZE,
        "height": PAGE_SIZE,
        "mimeType": "image/jpeg",
        "rotation": 0,
    }
    if frames is not None:
        img["frames"] = frames
    return img


# 해부학 비율·대칭성을 만족하는 합성 랜드마크 (test_measure_27b와 동일 좌표계.
# head_top↔heel_mid = 1400px — heightCm 172 입력 시 척도 ≈ 1.2286 mm/px).
LANDMARKS = {
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

PROFILE = {"heightCm": 172.0}

MEASUREMENT_FIELDS = [
    "height",
    "shoulder_width",
    "chest_circumference",
    "waist_circumference",
    "hip_circumference",
    "arm_length",
    "inseam",
    "torso_length",
]


def _mock_extract(monkeypatch, side_effects: list):
    """extract_body_landmarks를 호출 순서대로 side_effects로 대체 (API 호출 0).

    side_effect가 Exception이면 raise, dict면 반환. 호출 횟수를 기록해 돌려준다.
    """
    calls = {"n": 0}

    def fake(image_base64, width, height, mime_type="image/jpeg"):
        effect = side_effects[min(calls["n"], len(side_effects) - 1)]
        calls["n"] += 1
        if isinstance(effect, Exception):
            raise effect
        return effect

    monkeypatch.setattr(analyze_route, "extract_body_landmarks", fake)
    return calls


def _assert_body_measurements_shape(data: dict, expected_mode: str) -> None:
    """응답이 BodyMeasurements 규격(src/types/index.ts)을 모두 갖췄는지 검사."""
    for field in MEASUREMENT_FIELDS:
        assert field in data, f"측정 항목 누락: {field}"
        assert isinstance(data[field], (int, float)), f"{field}가 숫자가 아님"

    assert "confidence" in data
    assert isinstance(data["confidence"], dict) and data["confidence"]
    for part, level in data["confidence"].items():
        assert level in ("high", "medium", "low"), f"confidence[{part}]={level}"

    assert data["mode"] == expected_mode

    ref = data["reference"]
    assert ref["type"] in ("card", "aruco")
    assert (expected_mode == "simple") == (ref["type"] == "card")
    assert isinstance(ref["realWidthMm"], (int, float))
    assert isinstance(ref["realHeightMm"], (int, float))
    assert isinstance(ref["detected"], bool)


# ---------- 1) 성공 경로: 검출→척도→랜드마크(mock)→통계 전 구간 배선 ----------

def test_analyze_precise_full_pipeline(monkeypatch):
    calls = _mock_extract(monkeypatch, [LANDMARKS])
    frames = [_marker_page_b64()] * 3
    res = client.post("/analyze", json={
        "image": _image(_marker_page_b64(), frames=frames),
        "mode": "precise",
        "profile": PROFILE,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "stub" not in data  # 2-1 stub 완전 제거 확인
    assert calls["n"] == 3     # 프레임 수만큼 추출

    _assert_body_measurements_shape(data["measurements"], "precise")
    assert data["reference"]["detected"] is True
    # 키 캘리브레이션: head↔heel 1400px에 heightCm=172 입력 → 키는 정확히 172
    assert abs(data["measurements"]["height"] - 172.0) < 0.11

    stats = data["stats"]
    assert stats["runs"] == 3
    assert stats["scale"]["source"] == "height"
    assert set(stats["spreadCm"]) == set(MEASUREMENT_FIELDS)
    assert isinstance(data["warnings"], list)


def test_analyze_without_profile_uses_marker_scale(monkeypatch):
    """profile 없으면 마커 스칼라 폴백 (2-8 UI 연결 전 규격 불파손)."""
    _mock_extract(monkeypatch, [LANDMARKS])
    res = client.post("/analyze", json={
        "image": _image(_marker_page_b64()),  # frames 없음 → 대표 이미지 1장
        "mode": "precise",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["stats"]["runs"] == 1
    assert data["stats"]["scale"]["source"] == "marker"


# ---------- 2) 미검출: detected:false 정상 반환 (Gate 자동 검증 항목) ----------

def test_analyze_reference_not_detected(monkeypatch):
    calls = _mock_extract(monkeypatch, [LANDMARKS])
    res = client.post("/analyze", json={
        "image": _image(_blank_page_b64()),
        "mode": "simple",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["reference"]["detected"] is False
    assert "measurements" not in data  # 가짜 숫자 없음 (규칙 1)
    assert "카드" in data["error"]
    assert calls["n"] == 0  # 미검출이면 AI 호출 자체가 없어야 함 (비용 보호)


# ---------- 3) 프레임 부분 실패·전체 실패 ----------

def test_analyze_partial_frame_failure(monkeypatch):
    _mock_extract(monkeypatch, [LANDMARKS, ValueError("파싱 실패"), LANDMARKS])
    frames = [_marker_page_b64()] * 3
    res = client.post("/analyze", json={
        "image": _image(_marker_page_b64(), frames=frames),
        "mode": "precise",
        "profile": PROFILE,
    })
    data = res.json()
    assert data["ok"] is True
    assert data["stats"]["runs"] == 2
    assert any("추출 실패" in w for w in data["warnings"])


def test_analyze_all_frames_failed(monkeypatch):
    _mock_extract(monkeypatch, [ValueError("파싱 실패")])
    res = client.post("/analyze", json={
        "image": _image(_marker_page_b64()),
        "mode": "precise",
    })
    data = res.json()
    assert data["ok"] is False
    assert data["reference"]["detected"] is True  # 검출은 됐지만 좌표 실패
    assert "measurements" not in data
    assert "좌표" in data["error"]


def test_analyze_frames_capped(monkeypatch):
    """MAX_FRAMES 초과분은 버림 — API 비용 보호."""
    calls = _mock_extract(monkeypatch, [LANDMARKS])
    frames = [_marker_page_b64()] * (analyze_route.MAX_FRAMES + 3)
    res = client.post("/analyze", json={
        "image": _image(_marker_page_b64(), frames=frames),
        "mode": "precise",
        "profile": PROFILE,
    })
    assert res.json()["stats"]["runs"] == analyze_route.MAX_FRAMES
    assert calls["n"] == analyze_route.MAX_FRAMES


# ---------- 4) 입력 검증 (2-1에서 누적) ----------

def test_analyze_missing_image_returns_422():
    res = client.post("/analyze", json={"mode": "simple"})
    assert res.status_code == 422


def test_analyze_invalid_mode_returns_422():
    res = client.post("/analyze", json={
        "image": _image(_blank_page_b64()), "mode": "wrong",
    })
    assert res.status_code == 422


def test_analyze_invalid_base64_returns_422():
    res = client.post("/analyze", json={
        "image": _image("!!!not-base64!!!"), "mode": "simple",
    })
    assert res.status_code == 422


def test_analyze_undecodable_image_returns_422():
    res = client.post("/analyze", json={
        "image": _image(base64.b64encode(b"not an image").decode()),
        "mode": "simple",
    })
    assert res.status_code == 422


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
