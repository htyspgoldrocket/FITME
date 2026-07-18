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
