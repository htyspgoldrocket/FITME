"""Phase 2-1 자동 검증 — /analyze(더미 stub)와 /health.

CLAUDE.md 13-4: 검증 스크립트는 Phase마다 누적한다 (지우지 않음).
Step 2-6에서 /analyze가 실제 측정으로 교체되면 "stub" 필드 관련 단언만 갱신한다.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

VALID_IMAGE = {
    "base64": "dGVzdA==",
    "width": 1080,
    "height": 1440,
    "mimeType": "image/jpeg",
    "rotation": 0,
}

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


def _assert_body_measurements_shape(data: dict, expected_mode: str) -> None:
    """응답이 BodyMeasurements 규격(src/types/index.ts)을 모두 갖췄는지 검사."""
    # 1) 8개 측정 항목 — 전부 숫자
    for field in MEASUREMENT_FIELDS:
        assert field in data, f"측정 항목 누락: {field}"
        assert isinstance(data[field], (int, float)), f"{field}가 숫자가 아님"

    # 2) confidence — 항목별 high/medium/low
    assert "confidence" in data
    assert isinstance(data["confidence"], dict) and data["confidence"]
    for part, level in data["confidence"].items():
        assert level in ("high", "medium", "low"), f"confidence[{part}]={level}"

    # 3) mode — 요청과 일치
    assert data["mode"] == expected_mode

    # 4) reference — 구조 + 모드-기준물 대응
    ref = data["reference"]
    assert ref["type"] in ("card", "aruco")
    assert (expected_mode == "simple") == (ref["type"] == "card")
    assert isinstance(ref["realWidthMm"], (int, float))
    assert isinstance(ref["realHeightMm"], (int, float))
    assert isinstance(ref["detected"], bool)


def test_analyze_simple_returns_body_measurements():
    res = client.post("/analyze", json={"image": VALID_IMAGE, "mode": "simple"})
    assert res.status_code == 200
    data = res.json()
    _assert_body_measurements_shape(data, "simple")
    # 카드 실측 규격 (ISO/IEC 7810)
    assert data["reference"]["realWidthMm"] == 85.6
    assert data["reference"]["realHeightMm"] == 53.98
    # Phase 2-1 한정: 의도된 stub임이 응답에 표시되어야 함 (규칙 1)
    assert "stub" in data


def test_analyze_precise_returns_body_measurements():
    res = client.post("/analyze", json={"image": VALID_IMAGE, "mode": "precise"})
    assert res.status_code == 200
    data = res.json()
    _assert_body_measurements_shape(data, "precise")
    assert "stub" in data


def test_analyze_missing_image_returns_422():
    res = client.post("/analyze", json={"mode": "simple"})
    assert res.status_code == 422


def test_analyze_invalid_mode_returns_422():
    res = client.post("/analyze", json={"image": VALID_IMAGE, "mode": "wrong"})
    assert res.status_code == 422


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
