# -*- coding: utf-8 -*-
"""Phase 6-1 자동 검증 — 베타 접근 코드 + 사용량 상한 (services/access_guard).

전부 오프라인 (API 호출 0회): enforce()는 임시 SQLite로 단위 검증,
라우트 배선은 TestClient — 코드가 틀리면 무거운 파이프라인 진입 전에
403이 나야 하므로 mock조차 불필요하다.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from services.access_guard import enforce

client = TestClient(app)


def _db(tmp_path):
    return tmp_path / "usage.sqlite"


# ---------- enforce() 단위 ----------


def test_inactive_without_env(tmp_path, monkeypatch):
    """FITME_BETA_CODE 미설정 = 방어 전체 비활성 (로컬 개발·테스트 동작 보존)."""
    monkeypatch.delenv("FITME_BETA_CODE", raising=False)
    enforce("1.2.3.4", None, db_path=_db(tmp_path))  # 예외 없으면 통과


def test_wrong_or_missing_code_403(tmp_path, monkeypatch):
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    for bad in [None, "", "wrong"]:
        with pytest.raises(HTTPException) as e:
            enforce("1.2.3.4", bad, db_path=_db(tmp_path))
        assert e.value.status_code == 403
        assert "베타 코드" in e.value.detail


def test_correct_code_passes_and_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    monkeypatch.setenv("FITME_DAILY_LIMIT_PER_IP", "3")
    db = _db(tmp_path)
    for _ in range(3):
        enforce("1.2.3.4", "fitme2026", db_path=db, day="2026-07-21")
    with pytest.raises(HTTPException) as e:
        enforce("1.2.3.4", "fitme2026", db_path=db, day="2026-07-21")
    assert e.value.status_code == 429
    assert "일일 제한" in e.value.detail


def test_per_ip_limit_is_per_ip(tmp_path, monkeypatch):
    """한 IP가 상한에 걸려도 다른 IP는 계속 사용 가능."""
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    monkeypatch.setenv("FITME_DAILY_LIMIT_PER_IP", "1")
    db = _db(tmp_path)
    enforce("1.1.1.1", "fitme2026", db_path=db, day="2026-07-21")
    with pytest.raises(HTTPException):
        enforce("1.1.1.1", "fitme2026", db_path=db, day="2026-07-21")
    enforce("2.2.2.2", "fitme2026", db_path=db, day="2026-07-21")  # 통과해야 함


def test_global_limit_429(tmp_path, monkeypatch):
    """IP를 바꿔가며 우회해도 서버 전체 일일 상한이 최종 방어선."""
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    monkeypatch.setenv("FITME_DAILY_LIMIT_PER_IP", "100")
    monkeypatch.setenv("FITME_DAILY_LIMIT_GLOBAL", "2")
    db = _db(tmp_path)
    enforce("1.1.1.1", "fitme2026", db_path=db, day="2026-07-21")
    enforce("2.2.2.2", "fitme2026", db_path=db, day="2026-07-21")
    with pytest.raises(HTTPException) as e:
        enforce("3.3.3.3", "fitme2026", db_path=db, day="2026-07-21")
    assert e.value.status_code == 429
    assert "전체 사용량" in e.value.detail


def test_day_rollover_resets(tmp_path, monkeypatch):
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    monkeypatch.setenv("FITME_DAILY_LIMIT_PER_IP", "1")
    db = _db(tmp_path)
    enforce("1.2.3.4", "fitme2026", db_path=db, day="2026-07-21")
    with pytest.raises(HTTPException):
        enforce("1.2.3.4", "fitme2026", db_path=db, day="2026-07-21")
    enforce("1.2.3.4", "fitme2026", db_path=db, day="2026-07-22")  # 다음 날 리셋


def test_rejected_requests_not_counted(tmp_path, monkeypatch):
    """틀린 코드 연타가 상한을 잠식하지 않는다."""
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    monkeypatch.setenv("FITME_DAILY_LIMIT_PER_IP", "1")
    db = _db(tmp_path)
    for _ in range(5):
        with pytest.raises(HTTPException):
            enforce("1.2.3.4", "wrong", db_path=db, day="2026-07-21")
    enforce("1.2.3.4", "fitme2026", db_path=db, day="2026-07-21")  # 여전히 1회 남음


# ---------- 라우트 배선 (/analyze·/synthesize) ----------

_ANALYZE_BODY = {
    "image": {
        "base64": "aGVsbG8=",  # 구조만 유효하면 됨 — 가드가 먼저 거부해야 함
        "width": 100,
        "height": 100,
        "mimeType": "image/jpeg",
        "rotation": 0,
    },
    "mode": "precise",
}

_SYNTH_BODY = {
    "humanImage": _ANALYZE_BODY["image"],
    "clothing": {
        "brand": "b",
        "url": "https://example.com",
        "category": "top",
        "sizes": [],
    },
}


@pytest.mark.parametrize(
    ("path", "body"), [("/analyze", _ANALYZE_BODY), ("/synthesize", _SYNTH_BODY)]
)
def test_routes_reject_wrong_code(path, body, monkeypatch):
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    res = client.post(path, json=body, headers={"X-Beta-Code": "wrong"})
    assert res.status_code == 403
    assert "베타 코드" in res.json()["detail"]


def test_health_not_guarded(monkeypatch):
    """비용 없는 라우트(/health)는 코드 없이도 열려 있다."""
    monkeypatch.setenv("FITME_BETA_CODE", "fitme2026")
    assert client.get("/health").status_code == 200
