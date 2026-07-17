# -*- coding: utf-8 -*-
"""POST /clothing — 의류 URL → ClothingSpec (Phase 3-4).

파이프라인: SQLite 캐시 조회 → (미스 시) 스크래핑(3-2) → 정규화(3-3) → 캐시 저장.
실패는 HTTP 오류가 아니라 ClothingResponse.ok=False + error(한국어) + code로
전달한다 (AnalyzeResponse와 같은 방식 — 프론트가 사용자 안내문을 그대로 표시).

⚠️ Playwright sync API 사용(clothing_scrape)이므로 반드시 `def` 엔드포인트여야
한다 — FastAPI가 threadpool에서 실행. async로 바꾸면 이벤트 루프 충돌
(PROGRESS.md Phase 3 배운 것 4번).
"""

from fastapi import APIRouter

from models.schemas import ClothingRequest, ClothingResponse, ClothingSpec
from services import clothing_store
from services.clothing_normalize import normalize_scraped
from services.clothing_scrape import (
    ClothingScrapeError,
    parse_musinsa_url,
    scrape_musinsa,
)

router = APIRouter()


@router.post("/clothing", response_model=ClothingResponse, response_model_exclude_none=True)
def clothing_endpoint(req: ClothingRequest) -> ClothingResponse:
    goods_no = parse_musinsa_url(req.url)
    key = f"musinsa:{goods_no}" if goods_no is not None else None

    if key is not None:
        cached = clothing_store.get_cached(key)
        if cached is not None:
            return ClothingResponse(ok=True, spec=ClothingSpec(**cached), cached=True)

    try:
        # 무신사 URL이 아니면 scrape_musinsa가 unsupported로 안내 (Playwright 미기동)
        spec_dict = normalize_scraped(scrape_musinsa(req.url))
    except ClothingScrapeError as e:
        return ClothingResponse(ok=False, error=str(e), code=e.code)

    spec = ClothingSpec(**spec_dict)  # 계약 검증 후에만 캐시에 저장
    if key is not None:
        clothing_store.put(key, spec_dict)
    return ClothingResponse(ok=True, spec=spec, cached=False)
