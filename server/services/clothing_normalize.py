# -*- coding: utf-8 -*-
"""사이즈 표기 정규화 (Phase 3-3) — 스크래핑 원자료 → ClothingSpec 형태.

변환 규칙은 data/size_conversion.json이 단일 출처:
  - part_map: 부위명('가슴단면' 등) → ClothingSize 필드 + 단면×2 둘레 환산
  - category_keywords: 카테고리 경로·의류종류명 → top/bottom/dress/outer
  - label_table: 실측이 전혀 없는 사이즈의 호칭("95"/"L") → 근사 cm
    (estimated:true로 표시 — 실측 아님. "Free" 등은 변환 불가 → needsUserInput)

원칙 (규칙 1): 모르는 부위는 경고로 드러내고, 없는 부위를 가짜 숫자로 채우지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "size_conversion.json"

with open(_DATA_PATH, encoding="utf-8") as f:
    _TABLE = json.load(f)

PART_MAP: dict[str, dict[str, Any]] = _TABLE["part_map"]
CATEGORY_KEYWORDS: list[dict[str, str]] = _TABLE["category_keywords"]
ALPHA_TOP: dict[str, float] = _TABLE["label_table"]["alpha_top_chest"]
ALPHA_BOTTOM: dict[str, float] = _TABLE["label_table"]["alpha_bottom_waist"]
UNSUPPORTED_LABELS: set[str] = {s.upper() for s in _TABLE["label_table"]["unsupported"]}

INCH_TO_CM = 2.54


def resolve_category(category_path: list[str], type_name: str,
                     part_names: set[str]) -> tuple[str, list[str]]:
    """카테고리 결정 — 경로 키워드 → 종류명 키워드 → 부위 휴리스틱 순.

    반환: (category, warnings). 원피스 > 아우터 > 하의 > 상의 우선순위는
    category_keywords 배열 순서가 결정한다.
    """
    texts = list(category_path) + [type_name]
    for rule in CATEGORY_KEYWORDS:
        if any(rule["contains"] in t for t in texts if t):
            return rule["category"], []
    # 휴리스틱 폴백: 측정 부위로 추정 (하의 부위가 있으면 bottom)
    if part_names & {"허리단면", "엉덩이단면", "밑위", "허벅지단면"}:
        return "bottom", ["카테고리를 확인하지 못해 측정 부위로 하의로 추정했어요"]
    if part_names & {"가슴단면", "어깨너비", "소매길이"}:
        return "top", ["카테고리를 확인하지 못해 측정 부위로 상의로 추정했어요"]
    return "top", [f"카테고리를 알 수 없어 상의로 가정했어요 (원문: {'/'.join(texts)})"]


def normalize_label(label: str, category: str) -> dict[str, float] | None:
    """실측 없는 호칭 표기 → 근사 cm. 변환 불가면 None (사용자 입력 요청 대상).

    "95"(상의)=가슴둘레 호칭, "30"(하의)=허리 인치, "76"(하의)=허리 cm 호칭,
    "L" 등 알파벳은 label_table. 전부 근사치이므로 호출부가 estimated:true를 붙인다.
    """
    key = label.strip().upper()
    if not key or key in UNSUPPORTED_LABELS:
        return None
    is_bottom = category == "bottom"
    alpha = ALPHA_BOTTOM if is_bottom else ALPHA_TOP
    if key in alpha:
        field = "waist_cm" if is_bottom else "chest_cm"
        return {field: float(alpha[key])}
    try:
        n = float(key)
    except ValueError:
        return None
    if is_bottom:
        if 24 <= n <= 44:  # 인치 표기 (예: "30", "38")
            return {"waist_cm": round(n * INCH_TO_CM, 1)}
        if 60 <= n <= 120:  # cm 호칭 (예: "76", "82")
            return {"waist_cm": n}
        return None
    if 80 <= n <= 120:  # 상의 cm 호칭 (예: "95", "100")
        return {"chest_cm": n}
    return None


def normalize_scraped(raw: dict[str, Any]) -> dict[str, Any]:
    """스크래핑 원자료(services/clothing_scrape.py 반환 형식) → ClothingSpec 형태 dict.

    실측이 있는 사이즈는 part_map으로 필드 매핑(단면×2), 실측이 없는 사이즈는
    호칭 근사(estimated:true). 둘 다 불가한 사이즈는 목록에 남기되 값 없이
    needsUserInput을 켠다 — 가짜 숫자로 채우지 않는다 (규칙 1).
    """
    warnings: list[str] = []
    needs_user_input = False

    part_names = {
        name for entry in raw.get("sizes", []) for name in entry.get("measurements", {})
    }
    category, cat_warnings = resolve_category(
        raw.get("categoryPath", []), raw.get("typeName", ""), part_names
    )
    warnings.extend(cat_warnings)

    unknown_parts: set[str] = set()
    sizes: list[dict[str, Any]] = []
    for entry in raw.get("sizes", []):
        fields: dict[str, Any] = {}
        for name, value in entry.get("measurements", {}).items():
            rule = PART_MAP.get(name)
            if rule is None:
                unknown_parts.add(name)
                continue
            fields[rule["field"]] = round(value * rule["factor"], 1)
        if not fields:
            approx = normalize_label(entry.get("label", ""), category)
            if approx is not None:
                fields = {**approx, "estimated": True}
                warnings.append(
                    f"'{entry['label']}' 사이즈는 실측이 없어 호칭 기반 근사치예요"
                )
            else:
                needs_user_input = True
                warnings.append(
                    f"'{entry['label']}' 사이즈는 치수를 알 수 없어요 — 실측값을 직접 입력해 주세요"
                )
        sizes.append({"label": entry.get("label", ""), **fields})

    if unknown_parts:
        warnings.append(
            f"알 수 없는 측정 부위는 제외했어요: {', '.join(sorted(unknown_parts))}"
        )

    spec: dict[str, Any] = {
        "brand": raw.get("brand", ""),
        "url": raw.get("url", ""),
        "category": category,
        "productName": raw.get("productName") or None,
        "sizes": sizes,
    }
    if needs_user_input:
        spec["needsUserInput"] = True
    if warnings:
        spec["warnings"] = warnings
    return spec


if __name__ == "__main__":
    # 수동 확인용: 무신사 URL → 스크래핑 → 정규화 결과 출력
    import sys

    from services.clothing_scrape import ClothingScrapeError, scrape_musinsa

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    try:
        normalized = normalize_scraped(scrape_musinsa(sys.argv[1]))
    except ClothingScrapeError as e:
        print(f"실패 [{e.code}] {e}")
        sys.exit(1)
    print(json.dumps(normalized, ensure_ascii=False, indent=2))
