# -*- coding: utf-8 -*-
"""베타 접근 코드 + AI 비용 라우트 사용량 상한 (Phase 6-1 — 배포 남용 방어).

배포 방침(주변인 무료 베타, CLAUDE.md 12장)에 따라, AI 비용이 발생하는
라우트(/analyze ≈ $0.15/회, /synthesize ≈ $0.025/회)를 두 겹으로 방어한다:

  1) 베타 코드 — 프론트가 `X-Beta-Code` 헤더로 전달, 초대받은 주변인에게만
     공유. 코드가 틀리면 403.
  2) 사용량 상한 — IP당 일일 + 서버 전체 일일. SQLite 카운터라 재시작·
     재배포에도 유지된다. 초과 시 429 + 한국어 안내.

**FITME_BETA_CODE 환경 변수가 설정된 경우에만 활성** — 로컬 개발·pytest·E2E는
env 미설정으로 기존과 완전히 동일하게 동작한다 (배포 환경에서만 켜짐).

환경 변수:
  FITME_BETA_CODE            베타 코드 (미설정 = 방어 전체 비활성)
  FITME_DAILY_LIMIT_PER_IP   IP당 일일 허용 횟수 (기본 10 ≈ $1.5)
  FITME_DAILY_LIMIT_GLOBAL   서버 전체 일일 허용 횟수 (기본 60 ≈ $9)
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from fastapi import HTTPException, Request

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "usage.sqlite"

DEFAULT_PER_IP = 10
DEFAULT_GLOBAL = 60


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS usage_counter ("
        "  day TEXT NOT NULL,"    # "YYYY-MM-DD" (서버 로컬 기준 — 자정에 리셋)
        "  ip TEXT NOT NULL,"
        "  count INTEGER NOT NULL,"
        "  PRIMARY KEY (day, ip)"
        ")"
    )
    return conn


def enforce(
    ip: str, code: str | None, db_path: Path | None = None, day: str | None = None
) -> None:
    """베타 코드·사용량 검사 + 허용 시 카운트 1 증가. 거부는 HTTPException.

    검사 순서: 코드(403) → 전체 상한(429) → IP 상한(429). 거부된 요청은
    카운트하지 않는다 (틀린 코드 연타가 상한을 잠식하지 않게).
    """
    expected = os.environ.get("FITME_BETA_CODE")
    if not expected:
        return  # 베타 방어 비활성 (로컬 개발·테스트)

    if code != expected:
        raise HTTPException(
            status_code=403,
            detail="베타 코드가 올바르지 않아요 — 초대받은 코드를 입력해 주세요",
        )

    day = day or time.strftime("%Y-%m-%d")
    per_ip = int(os.environ.get("FITME_DAILY_LIMIT_PER_IP", DEFAULT_PER_IP))
    global_limit = int(os.environ.get("FITME_DAILY_LIMIT_GLOBAL", DEFAULT_GLOBAL))

    conn = _connect(db_path or DB_PATH)
    try:
        with conn:
            total = conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM usage_counter WHERE day = ?",
                (day,),
            ).fetchone()[0]
            if total >= global_limit:
                raise HTTPException(
                    status_code=429,
                    detail="오늘 서비스 전체 사용량이 가득 찼어요 — 내일 다시 "
                    "이용해 주세요 (무료 베타 보호 장치예요)",
                )
            row = conn.execute(
                "SELECT count FROM usage_counter WHERE day = ? AND ip = ?",
                (day, ip),
            ).fetchone()
            if (row[0] if row else 0) >= per_ip:
                raise HTTPException(
                    status_code=429,
                    detail="오늘 사용 횟수를 모두 썼어요 — 내일 다시 이용해 "
                    "주세요 (1인당 일일 제한이 있어요)",
                )
            conn.execute(
                "INSERT INTO usage_counter (day, ip, count) VALUES (?, ?, 1) "
                "ON CONFLICT(day, ip) DO UPDATE SET count = count + 1",
                (day, ip),
            )
    finally:
        conn.close()


def client_ip(request: Request) -> str:
    """프록시(클라우드·터널) 뒤 클라이언트 IP — X-Forwarded-For 첫 항목 우선.

    헤더는 위조 가능하지만(완전 인증은 베타 코드 몫) IP 상한 우회 시에도
    전체 일일 상한이 최종 방어선이라 비용 폭주는 막힌다.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def guard_ai_route(request: Request) -> None:
    """FastAPI dependency — AI 비용 라우트(/analyze·/synthesize)에만 건다."""
    enforce(client_ip(request), request.headers.get("x-beta-code"))
