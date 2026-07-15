"""Phase 2-5 자동 검증 — Claude Vision 좌표 추출 (claude_vision.py).

★ 이 파일의 모든 테스트는 실제 API를 호출하지 않는다 (비용 0):
  - 파싱·스키마 검증: 순수 함수 _parse_landmarks 직접 테스트
  - 재요청 로직: _call_vision을 monkeypatch로 대체 (호출 횟수 카운트)
  - 캐시 동작: CLI를 서브프로세스로 실행하되 ANTHROPIC_BASE_URL을 불통 주소로
    설정 — API를 시도하면 반드시 실패하므로, 성공하면 캐시만 쓴 것이 증명됨
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import services.claude_vision as cv
from services.claude_vision import LANDMARK_KEYS, _parse_landmarks, extract_body_landmarks

FIXTURES = Path(__file__).parent / "fixtures"
ARUCO_PHOTO = FIXTURES / "person01_aruco.jpg"
LANDMARK_CACHE = FIXTURES / "person01_aruco.landmarks.json"

WIDTH, HEIGHT = 1080, 1440


def _valid_landmarks() -> dict:
    """15개 키 전부, 이미지 범위 내 좌표."""
    return {key: [100 + i * 10, 200 + i * 20] for i, key in enumerate(LANDMARK_KEYS)}


# ---------- 1) JSON 방어: 코드펜스 제거 ----------

def test_parse_codefenced_response():
    text = "```json\n" + json.dumps(_valid_landmarks()) + "\n```"
    result = _parse_landmarks(text, WIDTH, HEIGHT)
    assert set(result.keys()) == set(LANDMARK_KEYS)
    assert result["head_top"] == [100.0, 200.0]


# ---------- 2) JSON 방어: 설명문 혼입 ----------

def test_parse_response_with_surrounding_prose():
    text = (
        "어깨는 여기 있습니다. 요청하신 좌표는 다음과 같습니다:\n"
        + json.dumps(_valid_landmarks())
        + "\n도움이 되었기를 바랍니다!"
    )
    result = _parse_landmarks(text, WIDTH, HEIGHT)
    assert set(result.keys()) == set(LANDMARK_KEYS)


def test_parse_no_json_at_all_rejected():
    with pytest.raises(ValueError):
        _parse_landmarks("죄송하지만 좌표를 찾을 수 없습니다.", WIDTH, HEIGHT)


# ---------- 3) 스키마 검증: 키 누락 ----------

def test_parse_missing_key_rejected():
    data = _valid_landmarks()
    del data["crotch"]
    with pytest.raises(ValueError, match="crotch"):
        _parse_landmarks(json.dumps(data), WIDTH, HEIGHT)


# ---------- 4) 스키마 검증: 타입/형식 오류 ----------

def test_parse_non_numeric_coord_rejected():
    data = _valid_landmarks()
    data["head_top"] = ["가운데", "위"]
    with pytest.raises(ValueError):
        _parse_landmarks(json.dumps(data), WIDTH, HEIGHT)


def test_parse_wrong_shape_rejected():
    data = _valid_landmarks()
    data["left_wrist"] = [123]  # [x,y]가 아님
    with pytest.raises(ValueError):
        _parse_landmarks(json.dumps(data), WIDTH, HEIGHT)


# ---------- 5) 스키마 검증: 이미지 범위 초과 ----------

def test_parse_out_of_bounds_rejected():
    data = _valid_landmarks()
    data["right_heel"] = [WIDTH + 50, 100]  # x가 이미지 밖
    with pytest.raises(ValueError):
        _parse_landmarks(json.dumps(data), WIDTH, HEIGHT)


# ---------- 6) 재요청 로직: 1회만 재시도, 무한루프 금지 ----------

@pytest.fixture
def fake_api(monkeypatch):
    """_call_vision을 가짜 응답 큐로 대체하고 호출 횟수를 센다."""
    calls = {"count": 0, "responses": []}

    def fake_call(client, image_base64, mime_type, prompt):
        calls["count"] += 1
        return calls["responses"].pop(0)

    monkeypatch.setattr(cv, "_call_vision", fake_call)
    monkeypatch.setattr(cv, "_load_api_key", lambda: "sk-ant-test-dummy")
    return calls


def test_retry_exactly_once_then_error(fake_api):
    """두 번 다 파싱 불가 → 정확히 2회 호출 후 ValueError (3회째 없음)."""
    fake_api["responses"] = ["잘못된 응답 1", "잘못된 응답 2"]
    with pytest.raises(ValueError, match="재시도 포함 2회"):
        extract_body_landmarks("dGVzdA==", WIDTH, HEIGHT)
    assert fake_api["count"] == 2


def test_retry_recovers_on_second_attempt(fake_api):
    """1회차 오염 응답 → 재요청 → 2회차 정상이면 성공 (총 2회 호출)."""
    fake_api["responses"] = ["설명만 있고 JSON 없음", json.dumps(_valid_landmarks())]
    result = extract_body_landmarks("dGVzdA==", WIDTH, HEIGHT)
    assert set(result.keys()) == set(LANDMARK_KEYS)
    assert fake_api["count"] == 2


def test_no_retry_when_first_succeeds(fake_api):
    """1회차 정상이면 재요청 없음 (총 1회 호출)."""
    fake_api["responses"] = ["```json\n" + json.dumps(_valid_landmarks()) + "\n```"]
    result = extract_body_landmarks("dGVzdA==", WIDTH, HEIGHT)
    assert set(result.keys()) == set(LANDMARK_KEYS)
    assert fake_api["count"] == 1


# ---------- 7) 캐시 동작: 캐시가 있으면 API 미호출 ----------

@pytest.mark.skipif(
    not (ARUCO_PHOTO.exists() and LANDMARK_CACHE.exists()),
    reason="로컬 전용 픽스처(사진+landmarks 캐시) 없음",
)
def test_cli_uses_cache_without_api_call():
    """CLI를 불통 API 주소로 실행 — 캐시만으로 성공하면 API 미호출이 증명됨."""
    env = dict(os.environ)
    env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:9"  # 어떤 호출도 즉시 실패
    env["PYTHONIOENCODING"] = "utf-8"
    server_dir = Path(__file__).parent.parent
    proc = subprocess.run(
        [sys.executable, "services/claude_vision.py", str(ARUCO_PHOTO)],
        cwd=server_dir,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, f"CLI 실패:\n{proc.stdout}\n{proc.stderr}"
    assert "캐시 사용" in proc.stdout
    assert "새 호출 없음" in proc.stdout
