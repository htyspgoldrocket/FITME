# -*- coding: utf-8 -*-
"""4-3 자연어 핏 피드백 테스트 — 전부 오프라인 (API 호출 0, mock).

Gate 자동 검증 대응: JSON 방어(코드펜스·재요청), 수치 모순 방어(라벨 포함
검증), 실패 시 사실 기반 템플릿 폴백, 추천 불가 경로.
"""
import pytest

import services.fit_feedback as fb
from models.schemas import ClothingSize, ClothingSpec
from services.fit import recommend_size
from tests.test_fit import make_body


def make_spec(sizes, category="top"):
    return ClothingSpec(
        brand="t", url="https://example.com/1", category=category,
        productName="테스트 상품", sizes=sizes,
    )


@pytest.fixture
def top_case():
    """가슴 100 몸 + S/M/L 상의 → M 추천 (가슴 good, 어깨 loose)."""
    body = make_body()
    spec = make_spec([
        ClothingSize(label="S", chest_cm=106.0, shoulder_cm=50.0),
        ClothingSize(label="M", chest_cm=111.0, shoulder_cm=51.0),
        ClothingSize(label="L", chest_cm=116.0, shoulder_cm=53.0),
    ])
    return body, spec, recommend_size(body, spec)


def mock_api(monkeypatch, responses):
    """_call_api가 responses를 순서대로 반환하도록 mock. 호출 기록 반환."""
    calls = []
    monkeypatch.setattr(fb, "_make_client", lambda: object())

    def fake_call(client, prompt):
        calls.append(prompt)
        return responses[min(len(calls) - 1, len(responses) - 1)]

    monkeypatch.setattr(fb, "_call_api", fake_call)
    return calls


# ---------- facts / 템플릿 (사실 기반 폴백) ----------

def test_facts_extract_recommended_size_scores(top_case):
    body, spec, rec = top_case
    facts = fb.build_fit_facts(body, spec, rec)
    assert facts["recommendedSize"] == "M"
    parts = {s["part"]: s for s in facts["scores"]}
    assert parts["chest"]["diff_cm"] == 11.0
    assert parts["chest"]["status"] == "good"
    assert parts["shoulder"]["status"] == "loose"


def test_template_states_numbers_and_label(top_case):
    body, spec, rec = top_case
    text = fb.template_feedback(fb.build_fit_facts(body, spec, rec))
    assert "'M' 사이즈를 추천해요" in text
    assert "+11.0cm" in text and "알맞아요" in text     # good
    assert "넉넉한 편" in text                          # loose (어깨 +5)
    assert "신뢰도가 낮아 참고용" in text               # chest low 전파


def test_template_tight_and_insufficient_warning():
    body = make_body()
    spec = make_spec(
        [ClothingSize(label="L", waist_cm=90.0, hip_cm=110.0)], category="bottom"
    )
    rec = recommend_size(body, spec)  # 허리 -10 tight → insufficient
    text = fb.template_feedback(fb.build_fit_facts(body, spec, rec))
    assert "10.0cm 부족해 낄 수 있어요" in text
    assert "작을 수 있어요" in text  # A안 경고가 문장에 포함


def test_template_when_no_recommendation():
    body = make_body()
    spec = make_spec([ClothingSize(label="Free", length_cm=100.0)])
    rec = recommend_size(body, spec)
    text = fb.template_feedback(fb.build_fit_facts(body, spec, rec))
    assert "추천이 어려워요" in text


# ---------- generate_feedback (mock API) ----------

def test_use_api_false_is_template(top_case):
    body, spec, rec = top_case
    out = fb.generate_feedback(body, spec, rec, use_api=False)
    assert out["source"] == "template"


def test_valid_api_response_used(top_case, monkeypatch):
    body, spec, rec = top_case
    calls = mock_api(monkeypatch, ['{"recommendation": "M 사이즈가 잘 맞겠어요."}'])
    out = fb.generate_feedback(body, spec, rec)
    assert out == {"text": "M 사이즈가 잘 맞겠어요.", "source": "claude"}
    assert len(calls) == 1
    assert '"diff_cm": 11.0' in calls[0]  # 프롬프트에 실제 수치 포함


def test_codefence_response_parsed(top_case, monkeypatch):
    body, spec, rec = top_case
    mock_api(monkeypatch, ['```json\n{"recommendation": "M 추천이에요."}\n```'])
    assert fb.generate_feedback(body, spec, rec)["source"] == "claude"


def test_invalid_then_valid_retries_once(top_case, monkeypatch):
    body, spec, rec = top_case
    calls = mock_api(monkeypatch, ["설명문만 있는 응답", '{"recommendation": "M 좋아요."}'])
    out = fb.generate_feedback(body, spec, rec)
    assert out["source"] == "claude"
    assert len(calls) == 2
    assert "파싱하지 못했습니다" in calls[1]  # 재요청 프롬프트


def test_twice_invalid_falls_back_to_template(top_case, monkeypatch):
    body, spec, rec = top_case
    calls = mock_api(monkeypatch, ["invalid", "invalid"])
    out = fb.generate_feedback(body, spec, rec)
    assert out["source"] == "template"
    assert len(calls) == 2  # 무한루프 금지


def test_missing_label_rejected(top_case, monkeypatch):
    """라벨 없는 응답 = 수치와 동떨어진 문장 → 거부 → 폴백."""
    body, spec, rec = top_case
    mock_api(monkeypatch, ['{"recommendation": "이 옷은 아주 좋아요."}'] * 2)
    out = fb.generate_feedback(body, spec, rec)
    assert out["source"] == "template"
    assert "'M'" in out["text"]


def test_api_exception_falls_back(top_case, monkeypatch):
    body, spec, rec = top_case
    monkeypatch.setattr(fb, "_make_client", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    out = fb.generate_feedback(body, spec, rec)
    assert out["source"] == "template"


def test_none_recommendation_skips_api(monkeypatch):
    """추천 불가면 API를 호출하지 않는다 (비용 0)."""
    body = make_body()
    spec = make_spec([ClothingSize(label="Free", length_cm=100.0)])
    rec = recommend_size(body, spec)
    calls = mock_api(monkeypatch, ['{"recommendation": "안 쓰임"}'])
    out = fb.generate_feedback(body, spec, rec)
    assert out["source"] == "template"
    assert calls == []
