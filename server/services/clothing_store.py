# -*- coding: utf-8 -*-
"""의류 스펙 SQLite 캐시 (Phase 3-4).

같은 상품 URL 재조회 시 무신사 재접속(Playwright 브라우저 기동 포함, 수 초)
없이 즉시 반환한다. 사이즈표는 사실상 불변이지만 상품 정보가 수정될 수 있어
TTL(24시간)을 둔다 — 만료 항목은 없는 것으로 취급하고 재스크래핑 시 덮어쓴다.

키는 쇼핑몰별 상품 식별자("musinsa:{goodsNo}") — URL 표기 변형(쿼리스트링 등)에
영향받지 않는다. DB 파일은 로컬 생성물이라 커밋하지 않는다 (.gitignore).
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "clothing_cache.sqlite"
TTL_SECONDS = 24 * 3600


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS clothing_cache ("
        "  key TEXT PRIMARY KEY,"
        "  spec TEXT NOT NULL,"        # ClothingSpec 형태 dict의 JSON
        "  fetched_at REAL NOT NULL"   # time.time()
        ")"
    )
    return conn


def get_cached(key: str, db_path: Path | None = None) -> dict[str, Any] | None:
    """캐시 조회 — 없거나 TTL 만료면 None."""
    conn = _connect(db_path or DB_PATH)
    try:
        row = conn.execute(
            "SELECT spec, fetched_at FROM clothing_cache WHERE key = ?", (key,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    spec_json, fetched_at = row
    if time.time() - fetched_at > TTL_SECONDS:
        return None
    return json.loads(spec_json)


def put(key: str, spec: dict[str, Any], db_path: Path | None = None) -> None:
    """캐시 저장 (기존 항목은 덮어씀)."""
    conn = _connect(db_path or DB_PATH)
    try:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO clothing_cache (key, spec, fetched_at) "
                "VALUES (?, ?, ?)",
                (key, json.dumps(spec, ensure_ascii=False), time.time()),
            )
    finally:
        conn.close()
