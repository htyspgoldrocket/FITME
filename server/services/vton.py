# -*- coding: utf-8 -*-
"""VTON 합성 (Phase 5-2b) — Replicate cuuupid/idm-vton 호출을 재사용 가능한 서비스로 정리.

⚠️ 개발/테스트 전용 모델(CC BY-NC-SA 4.0, 상업 사용 금지) — 출시 전 FASHN API 등
상업 허용 모델로 교체 필요 (CLAUDE.md 12장 참조). 5-1 단독 테스트
(scripts/test_vton_standalone.py)로 최초 검증됨.

CLI (수동 확인용):
  .\\venv\\Scripts\\python.exe services\\vton.py <사람사진경로> <의류이미지URL> <category>
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any, BinaryIO

import replicate

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# 5-1에서 확인한 latest_version 고정 — 버전 미지정 "cuuupid/idm-vton" 호출은
# 404 (2026-07-21 실증). Replicate가 모델을 갱신하면 이 값도 갱신 필요 —
# 실패 시 https://replicate.com/cuuupid/idm-vton 에서 최신 버전 ID 확인 후 교체.
MODEL_VERSION = (
    "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"
)

# ClothingSpec.category('top'/'bottom'/'dress'/'outer') -> IDM-VTON category
CATEGORY_MAP = {
    "top": "upper_body",
    "outer": "upper_body",
    "bottom": "lower_body",
    "dress": "dresses",
}


class VtonError(Exception):
    """합성 실패 — message는 사용자 안내용 한국어, code는 분기용."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _load_token() -> str:
    if os.environ.get("REPLICATE_API_TOKEN"):
        return os.environ["REPLICATE_API_TOKEN"]
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("REPLICATE_API_TOKEN=") and not line.startswith("#"):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                if token:
                    return token
    raise VtonError("no-token", "REPLICATE_API_TOKEN이 설정되지 않았어요 (server/.env 확인)")


def resolve_category(clothing_category: str) -> str:
    """ClothingSpec.category -> IDM-VTON category (순수 함수 — 테스트 대상)."""
    mapped = CATEGORY_MAP.get(clothing_category)
    if mapped is None:
        raise VtonError(
            "unsupported-category", f"지원하지 않는 의류 종류예요: {clothing_category}"
        )
    return mapped


def _extract_bytes(output: Any) -> bytes | None:
    """replicate.run() 반환값(FileOutput/URL 문자열/list)에서 이미지 바이트 추출."""
    if hasattr(output, "read"):
        return output.read()
    if isinstance(output, str):
        with urllib.request.urlopen(output, timeout=60) as resp:
            return resp.read()
    if isinstance(output, list) and output:
        return _extract_bytes(output[0])
    return None


def synthesize(
    human_image: BinaryIO,
    garment_image_url: str,
    clothing_category: str,
    garment_des: str = "",
) -> bytes:
    """사람 사진 + 의류 이미지 URL -> 합성 이미지 바이트.

    human_image: 열린 파일(바이너리 모드) 또는 파일과 동등한 스트림.
    garment_image_url: 의류 대표 이미지 URL (ClothingSpec.imageUrl — 없으면
        호출측에서 이 함수를 부르지 않고 합성 불가로 안내할 것, 5-2c 몫).
    clothing_category: ClothingSpec.category 값('top'/'bottom'/'dress'/'outer').
    실패: VtonError (message는 한국어 사용자 안내)
    """
    os.environ["REPLICATE_API_TOKEN"] = _load_token()
    category = resolve_category(clothing_category)

    try:
        output = replicate.run(
            MODEL_VERSION,
            input={
                "human_img": human_image,
                "garm_img": garment_image_url,
                "garment_des": garment_des or "clothing item",
                "category": category,
            },
        )
    except replicate.exceptions.ReplicateError as e:
        raise VtonError(
            "synthesis-failed", "이미지 합성에 실패했어요 — 잠시 후 다시 시도해 주세요"
        ) from e

    data = _extract_bytes(output)
    if data is None:
        raise VtonError("synthesis-failed", "합성 결과를 읽지 못했어요")
    return data


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    human_path, garment_url, category = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        with open(human_path, "rb") as f:
            data = synthesize(f, garment_url, category)
    except VtonError as e:
        print(f"실패 [{e.code}] {e}")
        sys.exit(1)
    out_path = Path("vton_cli_output.jpg")
    out_path.write_bytes(data)
    print(f"저장: {out_path} ({len(data)} bytes)")
