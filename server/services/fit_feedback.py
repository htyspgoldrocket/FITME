# -*- coding: utf-8 -*-
"""자연어 핏 피드백 생성 (Phase 4-3) — FitScore·추천 결과 → 한국어 추천문.

원칙 (규칙 1 — 수치와 모순 금지):
- 프롬프트에 **계산된 사실만** JSON으로 넘기고, 그 숫자·판정을 벗어난 주장
  (원단·유행·체형 추측 등)을 금지한다. 생성문 검증: 추천 라벨이 본문에
  포함되어야 통과 (라벨 누락 = 수치와 동떨어진 응답으로 간주).
- API 실패·파싱 실패 시 **사실 기반 템플릿 문장으로 폴백** — 같은 facts에서
  기계적으로 조립하므로 가짜 정보가 아니다. source 필드("claude"/"template")로
  어느 경로였는지 호출부(4-4)가 알 수 있게 한다.
- JSON 방어는 2-5 패턴 재사용: 코드펜스 제거 → {} 추출 → 검증 → 1회만 재요청.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import anthropic

from models.schemas import BodyMeasurements, ClothingSpec
from services.claude_vision import _load_api_key

# 피드백 문장용 모델 (환경변수 FITME_FEEDBACK_MODEL로 교체 가능)
MODEL = os.environ.get("FITME_FEEDBACK_MODEL", "claude-opus-4-8")
MAX_TOKENS = 500

PART_KO = {"chest": "가슴", "waist": "허리", "hip": "엉덩이", "shoulder": "어깨"}

_PROMPT_TEMPLATE = """\
당신은 의류 사이즈 추천 앱의 문구 작성자입니다. 아래 JSON은 앱이 계산한
핏 분석 사실입니다. 이 사실만 사용해 사용자에게 보여줄 한국어 추천문을
2~4문장으로 작성하세요.

규칙:
- 아래 JSON에 없는 정보(원단, 유행, 체형 추측, 다른 사이즈 값)를 지어내지 마세요.
- 부위별 판정(good/tight/loose)과 여유 cm 수치와 모순되는 표현을 쓰지 마세요.
- 추천 사이즈 라벨을 본문에 반드시 포함하세요.
- insufficient가 true면 "모든 사이즈가 작을 수 있다"는 주의를 반드시 담으세요.
- confidence가 "low"인 부위가 있으면 해당 부위 수치는 참고용임을 언급하세요.
- warnings의 내용을 자연스럽게 녹이세요 (그대로 복사하지 않아도 됨).
- 존댓말(해요체)을 쓰고, 반환은 JSON 한 개만: {{"recommendation": "..."}}
  (설명문·코드펜스 금지)

핏 분석 사실:
{facts_json}
"""

_RETRY_SUFFIX = (
    "\n이전 응답을 파싱하지 못했습니다. 이번에는 '{'로 시작해 '}'로 끝나는 "
    "JSON 오브젝트 하나만 반환하세요."
)


def build_fit_facts(
    measurements: BodyMeasurements, spec: ClothingSpec, recommendation: dict[str, Any]
) -> dict[str, Any]:
    """프롬프트와 폴백 템플릿이 공유하는 '사실 묶음' — 단일 출처."""
    label = recommendation.get("recommendedSize")
    scores = []
    for entry in recommendation.get("perSize", []):
        if entry["label"] == label:
            scores = [
                {
                    "part": s.part,
                    "part_ko": PART_KO.get(s.part, s.part),
                    "status": s.status,
                    "diff_cm": s.diff_cm,   # 여유(+)/부족(-)
                    "confidence": s.confidence,
                }
                for s in entry["scores"]
            ]
            break
    return {
        "productName": spec.productName,
        "category": spec.category,
        "recommendedSize": label,
        "insufficient": bool(recommendation.get("insufficient")),
        "warnings": list(recommendation.get("warnings", [])),
        "scores": scores,
    }


def template_feedback(facts: dict[str, Any]) -> str:
    """사실 기반 기계 조립 문장 — API 폴백용 (지어낸 정보 없음)."""
    label = facts["recommendedSize"]
    if label is None:
        return " ".join(["사이즈 추천이 어려워요."] + facts["warnings"])
    parts = []
    for s in facts["scores"]:
        if s["status"] == "good":
            parts.append(f"{s['part_ko']}은(는) 여유 {s['diff_cm']:+.1f}cm로 알맞아요")
        elif s["status"] == "tight":
            parts.append(f"{s['part_ko']}은(는) {abs(s['diff_cm']):.1f}cm 부족해 낄 수 있어요")
        else:
            parts.append(f"{s['part_ko']}은(는) 여유 {s['diff_cm']:+.1f}cm로 넉넉한 편이에요")
    low = [s["part_ko"] for s in facts["scores"] if s["confidence"] == "low"]
    sentences = [f"'{label}' 사이즈를 추천해요.", ". ".join(parts) + "." if parts else ""]
    if low:
        sentences.append(f"{'·'.join(low)} 측정값은 신뢰도가 낮아 참고용이에요.")
    sentences.extend(facts["warnings"])
    return " ".join(s for s in sentences if s)


def generate_feedback(
    measurements: BodyMeasurements,
    spec: ClothingSpec,
    recommendation: dict[str, Any],
    use_api: bool = True,
) -> dict[str, str]:
    """추천문 생성. 반환: {"text": 한국어 추천문, "source": "claude"|"template"}.

    추천 불가(None)면 API를 쓰지 않고 템플릿으로 사유만 전달한다.
    """
    facts = build_fit_facts(measurements, spec, recommendation)
    if not use_api or facts["recommendedSize"] is None:
        return {"text": template_feedback(facts), "source": "template"}

    prompt = _PROMPT_TEMPLATE.format(
        facts_json=json.dumps(facts, ensure_ascii=False, indent=1)
    )
    try:
        client = _make_client()
        for attempt in range(2):  # 최초 1회 + 재요청 1회 (무한루프 금지 — B-5)
            text = _call_api(
                client, prompt if attempt == 0 else prompt + _RETRY_SUFFIX
            )
            parsed = _parse_feedback(text, facts["recommendedSize"])
            if parsed is not None:
                return {"text": parsed, "source": "claude"}
    except Exception:
        # 네트워크·키·API 오류 — 사용자 흐름을 끊지 않고 사실 기반 폴백.
        # (키 등 민감 정보가 예외 문구에 실릴 수 있어 로그로 올리지 않는다)
        pass
    return {"text": template_feedback(facts), "source": "template"}


def _make_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=_load_api_key())


def _call_api(client: anthropic.Anthropic, prompt: str) -> str:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _parse_feedback(text: str, label: str) -> str | None:
    """응답 → 추천문. 방어(2-5 패턴) + 라벨 포함 검증. 실패 시 None."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    value = data.get("recommendation")
    if not isinstance(value, str) or not value.strip():
        return None
    if label not in value:
        return None  # 추천 라벨 누락 — 수치와 동떨어진 응답으로 간주
    return value.strip()
