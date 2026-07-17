# -*- coding: utf-8 -*-
"""무신사 상품 사이즈 테이블 추출 (Phase 3-2).

무신사 상품 페이지가 스스로 호출하는 공개 JSON API 2개를 Playwright request
컨텍스트로 호출한다 (DOM 파싱보다 견고 — 페이지 UI 리뉴얼에도 API는 유지되는 편.
2026-07-17 실상품 탐사로 확인, 상세는 PROGRESS.md 3-2):
  - GET goods-detail.musinsa.com/api2/goods/{goodsNo}              -> 브랜드·상품명·카테고리
  - GET goods-detail.musinsa.com/api2/goods/{goodsNo}/actual-size  -> 사이즈별 실측(cm)

여기서는 **원자료 추출만** 한다 — '가슴단면' 등 단면(flat) 값을 둘레로 환산하고
ClothingSpec(cm 정규화)으로 바꾸는 것은 3-3(size_conversion)의 몫.

CLI (수동 확인용):
  .\\venv\\Scripts\\python.exe services\\clothing_scrape.py https://www.musinsa.com/products/6516683
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

GOODS_API = "https://goods-detail.musinsa.com/api2/goods/{goods_no}"
SIZE_API = "https://goods-detail.musinsa.com/api2/goods/{goods_no}/actual-size"

# 일반 브라우저 UA — 기본 UA(HeadlessChrome/python-requests류)는 차단 대상이 되기 쉽다
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_PRODUCT_PATH = re.compile(r"^/products/(\d+)")


class ClothingScrapeError(Exception):
    """스크래핑 실패 — message는 사용자 안내용 한국어, code는 분기용."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def parse_musinsa_url(url: str) -> int | None:
    """무신사 상품 URL에서 상품 번호 추출. 무신사 상품 URL이 아니면 None."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    host = parsed.hostname or ""
    if host != "musinsa.com" and not host.endswith(".musinsa.com"):
        return None
    m = _PRODUCT_PATH.match(parsed.path)
    return int(m.group(1)) if m else None


def _check_meta(payload: dict[str, Any], what: str) -> dict[str, Any]:
    """무신사 API 공통 봉투(meta/data) 검사 후 data 반환."""
    meta = payload.get("meta") or {}
    data = payload.get("data")
    if meta.get("result") != "SUCCESS" or data is None:
        raise ClothingScrapeError(
            "not-found", f"무신사에서 {what} 정보를 찾지 못했어요 — 상품 주소를 확인해 주세요"
        )
    return data


def parse_goods(data: dict[str, Any]) -> dict[str, Any]:
    """상품 API data → 브랜드·상품명·카테고리 (순수 함수 — 테스트 대상)."""
    category = data.get("category") or {}
    path = [
        category.get(k)
        for k in ("categoryDepth1Name", "categoryDepth2Name", "categoryDepth3Name")
        if category.get(k)
    ]
    brand_info = data.get("brandInfo") or {}
    return {
        "goodsNo": data.get("goodsNo"),
        "brand": brand_info.get("brandName") or data.get("brand") or "",
        "brandEnglishName": brand_info.get("brandEnglishName") or "",
        "productName": data.get("goodsNm") or "",
        "categoryPath": path,
    }


def parse_sizes(data: dict[str, Any]) -> dict[str, Any]:
    """실측 사이즈 API data → 사이즈별 {부위명: cm} (순수 함수 — 테스트 대상).

    부위명('총장'·'가슴단면' 등)과 값(cm)을 원문 그대로 보존한다.
    """
    sizes: list[dict[str, Any]] = []
    for entry in data.get("sizes") or []:
        label = str(entry.get("name") or "").strip()
        measurements: dict[str, float] = {}
        for item in entry.get("items") or []:
            name = str(item.get("name") or "").strip()
            value = item.get("value")
            if name and isinstance(value, (int, float)):
                measurements[name] = float(value)
        if label and measurements:
            sizes.append({"label": label, "measurements": measurements})
    if not sizes:
        raise ClothingScrapeError(
            "no-size",
            "이 상품에는 실측 사이즈 정보가 없어요 — 사이즈표가 있는 상품 주소를 입력해 주세요",
        )
    return {"typeName": str(data.get("typeName") or ""), "sizes": sizes}


def scrape_musinsa(url: str, timeout_ms: int = 15000) -> dict[str, Any]:
    """무신사 상품 URL → 원자료 사이즈 테이블.

    반환: {source, url, goodsNo, brand, brandEnglishName, productName,
           categoryPath, typeName, sizes:[{label, measurements:{부위명: cm}}]}
    실패: ClothingScrapeError (message는 한국어 사용자 안내)
    """
    goods_no = parse_musinsa_url(url)
    if goods_no is None:
        raise ClothingScrapeError(
            "unsupported",
            "무신사 상품 주소(musinsa.com/products/…)만 지원해요 — 다른 쇼핑몰은 순차 확대 예정",
        )

    # Playwright는 지연 import — 이 모듈을 import만 하는 테스트가 브라우저 의존 없이 돌게
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(user_agent=USER_AGENT)
                goods_res = ctx.request.get(
                    GOODS_API.format(goods_no=goods_no), timeout=timeout_ms
                )
                if not goods_res.ok:
                    raise ClothingScrapeError(
                        "not-found",
                        f"상품을 찾지 못했어요 (HTTP {goods_res.status}) — 상품 주소를 확인해 주세요",
                    )
                goods = parse_goods(_check_meta(goods_res.json(), "상품"))

                size_res = ctx.request.get(
                    SIZE_API.format(goods_no=goods_no), timeout=timeout_ms
                )
                if not size_res.ok:
                    raise ClothingScrapeError(
                        "no-size",
                        f"사이즈 정보를 가져오지 못했어요 (HTTP {size_res.status})",
                    )
                size_info = parse_sizes(_check_meta(size_res.json(), "사이즈"))
            finally:
                browser.close()
    except PlaywrightError as e:
        raise ClothingScrapeError(
            "network", "무신사 접속에 실패했어요 — 네트워크 상태를 확인하고 다시 시도해 주세요"
        ) from e

    return {
        "source": "musinsa",
        "url": f"https://www.musinsa.com/products/{goods_no}",
        **goods,
        **size_info,
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    try:
        result = scrape_musinsa(sys.argv[1])
    except ClothingScrapeError as e:
        print(f"실패 [{e.code}] {e}")
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
