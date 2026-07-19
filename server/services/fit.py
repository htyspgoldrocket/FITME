# -*- coding: utf-8 -*-
"""핏 계산 (Phase 4-1) — 신체 치수 × 의류 한 사이즈 → 부위별 FitScore.

비교 원칙 (규칙 1 — 정의가 다른 값을 추정으로 잇지 않는다):
- **같은 정의끼리만 비교한다.** 둘레↔둘레 3쌍(가슴/허리/엉덩이 — 옷 값은
  3-3 정규화에서 단면×2 환산된 둘레라 몸 둘레와 동일 기준) + 직선↔직선
  1쌍(어깨너비). 나머지 옷 부위는 몸 8항목과 정의가 1:1로 맞지 않아 판정에서
  제외한다: 소매길이(옷 어깨선~끝단, 반팔이면 의도적으로 짧음)↔팔길이(어깨점~
  손목), 총장(outseam)↔다리안쪽(inseam), 밑위/밑단/허벅지(몸 측정 항목 없음).
  이들의 활용(예: 총장 표시용 참고)은 4-2 이후 별도 결정.
- **옷에 없는 부위는 결과에서 제외** — 0이나 추정치로 채우지 않는다.
- diff_cm = 옷 − 몸 = 여유(+)/부족(−) cm (FitScore 계약 정의).
- 측정 신뢰도(confidence)를 부위별로 전파 — low면 판정 자체가 불확실함을
  Phase 4 결과 화면·자연어 피드백이 표시할 수 있게 한다 (12장 둘레 3종 한계).
"""
from __future__ import annotations

from models.schemas import BodyMeasurements, ClothingSize, FitScore

# (부위명, BodyMeasurements 필드, ClothingSize 필드) — 같은 기준 쌍만
PART_PAIRS: list[tuple[str, str, str]] = [
    ("chest", "chest_circumference", "chest_cm"),
    ("waist", "waist_circumference", "waist_cm"),
    ("hip", "hip_circumference", "hip_cm"),
    ("shoulder", "shoulder_width", "shoulder_cm"),
]

# tight/good/loose 경계 (cm, ease = 옷−몸): ease < 최소 → tight,
# 최소 ≤ ease ≤ 최대 → good, ease > 최대 → loose.
# ⚠️ 전부 추정값 — "일반 성인 의류의 통상 여유량" 상식 기준이며 실측·문헌
# 근거 없음 (13-2 문헌 인용 배제 정책 — 어정쩡한 인용으로 "검증된 척"하지
# 않는다). Phase 4 수동 검증(본인이 핏을 아는 옷 대조)에서 교정하고,
# 신축성·카테고리(상의/하의)별 세분화는 4-2에서 수행한다.
EASE_RANGES: dict[str, tuple[float, float]] = {
    "chest": (4.0, 18.0),    # 둘레 — 상의 기준: 딱 붙는 핏도 몸+4cm는 필요 (추정)
    "waist": (2.0, 12.0),    # 둘레 — 하의 허리는 여유 폭이 좁은 편 (추정)
    "hip": (2.0, 14.0),      # 둘레 (추정)
    "shoulder": (-1.0, 3.0), # 직선 — 둘레보다 민감: ±1cm 체감이 큼 (추정)
}


def score_parts(measurements: BodyMeasurements, size: ClothingSize) -> list[FitScore]:
    """한 사이즈에 대한 부위별 핏 판정.

    반환 목록에는 "옷이 그 부위 실측을 제공하는" 쌍만 들어간다 —
    상의는 보통 chest·shoulder 2개, 하의는 waist·hip 2개.
    """
    scores: list[FitScore] = []
    for part, body_field, garment_field in PART_PAIRS:
        garment = getattr(size, garment_field)
        if garment is None:
            continue  # 옷에 없는 부위 — 추정하지 않고 제외 (규칙 1)
        body = getattr(measurements, body_field)
        diff = round(garment - body, 1)
        lo, hi = EASE_RANGES[part]
        status = "tight" if diff < lo else ("loose" if diff > hi else "good")
        scores.append(
            FitScore(
                part=part,
                status=status,
                diff_cm=diff,
                confidence=measurements.confidence.get(body_field),
            )
        )
    return scores


# ============================================================
# 4-2 — 사이즈 추천 (설계 2026-07-18, 하의 허리는 A안 — 사용자 확정 2026-07-19)
# ============================================================

# 부위별 "이상적 여유" = EASE_RANGES(good 구간)의 중앙값 — 별도 추정을 더하지 않음
IDEAL_EASE: dict[str, float] = {p: (lo + hi) / 2 for p, (lo, hi) in EASE_RANGES.items()}

# ---- 의류 특성 감지 (Phase 4 수동 검증 1차 불일치 교정, 2026-07-19) ----
# 무신사가 핏 유형·신축성 필드를 주지 않으므로 상품명 키워드로 감지한다.
# ⚠️ 키워드 목록·보정량 전부 추정값. 방침(사용자 결정 2026-07-19): 지금은 앱
# 완성 우선 — 다수 실측 데이터가 확보되면 그때 검증·정교화한다. 완벽 목표 아님.
OVERSIZED_KEYWORDS = [
    "오버핏", "오버 핏", "오버사이즈", "루즈", "릴렉스", "와이드",
    "OVERSIZE", "OVER FIT", "LOOSE", "RELAXED",
]
ELASTIC_WAIST_KEYWORDS = [
    "트랙팬츠", "트랙 팬츠", "조거", "스웨트", "츄리닝", "밴딩", "이지팬츠",
    "이지 팬츠", "JOGGER", "TRACK PANT", "SWEAT",
]
# 오버핏 감지 시 이상 여유 상향 (검증 근거: 오버핏 티셔츠 실착 L — M(+16)/L(+18)
# 중 L이 맞으려면 chest 이상 여유 ≥ +19 필요. 표본 1벌 역산 수준의 추정)
OVERSIZED_IDEAL_BONUS = {"chest": 8.0, "shoulder": 5.0, "waist": 6.0, "hip": 6.0}
# 밴딩 하의(트랙팬츠·조거류)는 스포티/릴렉스 핏 — 엉덩이도 넉넉하게 입는 게
# 정상이라 이상 여유 상향 (검증 근거: 트랙팬츠 실착 L(hip +12) 역산 → 이상
# 여유 ≈ +13 = 기본 8 + 5. 표본 1벌 역산 수준의 추정)
ELASTIC_HIP_IDEAL_BONUS = 5.0


def detect_garment_traits(spec) -> dict[str, bool]:
    """상품명 키워드 → {oversized, elastic_waist}. 감지 실패는 보정 없음(안전)."""
    name = (spec.productName or "").upper()
    return {
        "oversized": any(k.upper() in name for k in OVERSIZED_KEYWORDS),
        # 신축 허리는 하의에서만 의미 (트랙팬츠·조거의 고무줄 밴드 —
        # 이완 상태 실측이 몸 허리보다 작은 것이 정상이라 직접 비교가 무의미)
        "elastic_waist": spec.category == "bottom"
        and any(k.upper() in name for k in ELASTIC_WAIST_KEYWORDS),
    }

# 카테고리별 부위 가중치. ⚠️ 추정값 — 사이즈 선택에서 부위가 갖는 통상적 중요도
# 기준이며 실측 근거 없음. Phase 4 수동 검증(아는 옷 대조)에서 교정한다.
# 목록에 없는 부위가 잡히면 참고 수준(0.1)로만 반영.
PART_WEIGHTS: dict[str, dict[str, float]] = {
    "top": {"chest": 0.6, "shoulder": 0.3, "waist": 0.1},
    "outer": {"chest": 0.6, "shoulder": 0.3, "waist": 0.1},
    "bottom": {"hip": 0.6, "waist": 0.3},
    "dress": {"chest": 0.5, "waist": 0.25, "hip": 0.25},
}
DEFAULT_WEIGHT = 0.1

# 신축성에 따른 필터 하한 완화 (둘레 부위만 — 직물이 늘어나는 방향). ⚠️ 추정값.
# 무신사는 신축성 미제공 → stretch 없으면 완화 0 (안전 기본값).
# 완화는 추천 필터에만 적용 — FitScore.status는 4-1 원 기준 유지 (표시 일관성).
STRETCH_RELAX_CM: dict[str, float] = {"none": 0.0, "low": 2.0, "high": 4.0}
CIRCUMFERENCE_PARTS = {"chest", "waist", "hip"}


class SizeFit(dict):
    """사이즈별 상세 (per_size 항목) — label/scores/candidate/penalty/violation."""


class Recommendation(dict):
    """recommend_size 반환 — recommendedSize(str|None)/insufficient/warnings/perSize.

    dict 기반(추가 계약 불필요) — FitResult 조립·API 배선은 4-4의 몫.
    """


def recommend_size(measurements: BodyMeasurements, spec) -> Recommendation:
    """ClothingSpec의 사이즈 목록에서 추천 사이즈 산출 (설계: 2단계).

    ① 하한 필터 — 비교 부위 중 (신축성 완화 후에도) 하한 미달인 사이즈는
       후보 탈락. loose는 탈락 사유가 아님 (관찰 1 — 드롭숄더 옷 배제 방지)
    ② 후보 중 이상 여유(IDEAL_EASE)에 가중 거리 최소인 사이즈 추천.
       동점이면 작은(목록 앞) 사이즈
    A안 (관찰 2): 후보가 0이면 가중 부족량(violation)이 최소인 사이즈를
       추천하되 insufficient=True + 한국어 경고 — 근거 없는 보정 없이
       불확실성을 드러낸다 (규칙 1)
    """
    relax = STRETCH_RELAX_CM.get(spec.stretch or "none", 0.0)
    weights = PART_WEIGHTS.get(spec.category, PART_WEIGHTS["top"])
    traits = detect_garment_traits(spec)
    ideal = dict(IDEAL_EASE)
    warnings: list[str] = []
    if traits["oversized"]:
        for part, bonus in OVERSIZED_IDEAL_BONUS.items():
            ideal[part] = ideal[part] + bonus
        warnings.append("오버핏 상품으로 보여 여유 기준을 높여 추천했어요")
    excluded: set[str] = set()
    if traits["elastic_waist"]:
        excluded.add("waist")
        ideal["hip"] = ideal["hip"] + ELASTIC_HIP_IDEAL_BONUS
        warnings.append(
            "허리가 밴딩(고무줄)으로 보여 표기 실측 비교에서 제외했어요 — "
            "밴딩 하의는 추천 정확도가 낮을 수 있어요"
        )
    per_size: list[SizeFit] = []
    # (정렬 키, 목록 순번, label) — 순번 포함으로 동점 시 작은 사이즈 우선
    candidates: list[tuple[float, int, str]] = []
    fallbacks: list[tuple[float, float, int, str]] = []

    for i, size in enumerate(spec.sizes):
        scores = [
            s for s in score_parts(measurements, size) if s.part not in excluded
        ]
        if not scores:
            per_size.append(SizeFit(label=size.label, scores=[], candidate=False,
                                    penalty=None, violation=None))
            continue  # 비교 가능한 부위가 없는 사이즈 — 추천 근거 없음 (규칙 1)
        penalty = 0.0
        violation = 0.0
        for s in scores:
            w = weights.get(s.part, DEFAULT_WEIGHT)
            penalty += w * abs(s.diff_cm - ideal[s.part])
            lo = EASE_RANGES[s.part][0]
            if s.part in CIRCUMFERENCE_PARTS:
                lo -= relax
            if s.diff_cm < lo:
                violation += w * (lo - s.diff_cm)
        is_candidate = violation == 0.0
        per_size.append(SizeFit(label=size.label, scores=scores, candidate=is_candidate,
                                penalty=round(penalty, 2), violation=round(violation, 2)))
        if is_candidate:
            candidates.append((penalty, i, size.label))
        else:
            fallbacks.append((violation, penalty, i, size.label))

    insufficient = False
    if candidates:
        _, idx, label = min(candidates)
    elif fallbacks:
        # A안 — 전 사이즈가 하한 미달: 가장 덜 부족한 사이즈 + 경고
        _, _, idx, label = min(fallbacks)
        insufficient = True
        tight_parts = [s.part for s in per_size[idx]["scores"] if s.status == "tight"]
        part_ko = {"chest": "가슴", "waist": "허리", "hip": "엉덩이", "shoulder": "어깨"}
        names = "·".join(part_ko.get(p, p) for p in tight_parts)
        warnings.append(
            f"모든 사이즈가 {names} 기준으로 작을 수 있어요 — 가장 여유 있는 "
            f"'{label}'을(를) 추천하지만, 해당 부위 실측 확인을 권장해요"
        )
    else:
        warnings.append("사이즈표에 비교 가능한 부위 실측이 없어 사이즈 추천이 어려워요")
        return Recommendation(recommendedSize=None, insufficient=False,
                              warnings=warnings, perSize=per_size)

    if getattr(spec.sizes[idx], "estimated", None):
        warnings.append(
            f"추천 사이즈 '{label}'의 치수는 실측이 아닌 호칭 기반 근사예요"
        )
    return Recommendation(recommendedSize=label, insufficient=insufficient,
                          warnings=warnings, perSize=per_size)
