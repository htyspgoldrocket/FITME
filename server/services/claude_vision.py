"""신체 부위 좌표 추출 (Step 2-5) — Claude Vision.

역할 분담 (CLAUDE.md 4-4 vision 원칙):
  - OpenCV  = 척도·왜곡 (기준물 검출 reference_detect.py, 호모그래피 measure.py)
  - Claude  = 신체 부위 인식 (이 모듈) — 픽셀 좌표만 뽑는다

출력은 15개 랜드마크의 픽셀 좌표 dict. 각 좌표는 measure.py의 distance_mm()에
바로 넣을 수 있는 [x, y] 형태다. 랜드마크 → 8개 치수(BodyMeasurements) 계산은
Step 2-6 담당 (여기서 하지 않음).

방어 장치 (CLAUDE.md 그룹 B):
  - B-6(측정값 편차 최소화): 원래 계획은 temperature=0이었으나, 현행 Claude 모델
    (Opus 4.7+ / Sonnet 5)은 temperature 파라미터가 제거되어 보내면 400이 난다.
    대응은 ① 좌표만 반환하는 결정적 프롬프트, ② 2-7의 다중 프레임 중앙값(전략 3).
    → CLAUDE.md B-6 문구 갱신 필요 (2026-07-15 확인)
  - B-5: JSON 파싱 방어 — 코드펜스 제거 → 정규식 {} 추출 → 실패 시 1회만 재요청
  - 보안: API 키는 server/.env에서만 로드, 로그·예외 메시지에 노출 금지
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import anthropic

# 신체 좌표 추출용 모델. 부위 인식 품질이 측정 정확도의 절반을 결정하므로
# 최신 고성능 모델을 기본값으로 쓴다 (환경변수 FITME_VISION_MODEL로 교체 가능).
MODEL = os.environ.get("FITME_VISION_MODEL", "claude-opus-4-8")
MAX_TOKENS = 1024

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# 8개 치수(BodyMeasurements) 계산에 필요한 15개 랜드마크.
# 어떤 치수가 어떤 랜드마크를 쓰는지는 2-6에서 정의한다.
#   키(신장): head_top ↔ heel / 어깨너비: left_shoulder ↔ right_shoulder
#   가슴: chest_* / 허리: waist_* / 엉덩이: hip_* (실루엣 좌우 가장자리)
#   팔길이: left_shoulder ↔ left_wrist / 다리안쪽: crotch ↔ left_ankle
#   상체길이: neck_base ↔ crotch
LANDMARK_KEYS = [
    "head_top",
    "neck_base",
    "left_shoulder",
    "right_shoulder",
    "chest_left",
    "chest_right",
    "waist_left",
    "waist_right",
    "hip_left",
    "hip_right",
    "left_wrist",
    "crotch",
    "left_ankle",
    "left_heel",
    "right_heel",
]

# ⚠️ 허리 정의 (옵션 A, 2026-07-16 사용자 확정): "natural waist(배꼽 높이)"의 위치
# 모호가 v1/v2/v3 전부에서 반복 편차 >2cm를 유발함이 실증되어(교란 변수 제거 완료,
# PROGRESS 배운 것 29번), 가슴 높이와 엉덩이 높이의 **기하학적 세로 중간 지점**으로
# 고정했다. 트레이드오프: 기하학적 중간점은 줄자의 "가장 잘록한 곳"과 다를 수 있음.
# **일관성(반복 편차)을 위해 의도적으로 선택** — 절대값 차이는 허리 깊이 계수
# 재역산으로 흡수한다 (measure.py DEPTH_RATIOS 주석 참조).
# 이 정의를 바꾸면 기존 랜드마크 캐시가 무효화된다 (재추출 = 사진당 API 13회).
_PROMPT_TEMPLATE = """\
This is a full-body front photo of one person. Image size: {width}x{height} pixels.
Locate these body landmarks and return ONLY a single JSON object. No explanation,
no markdown, no code fences.

Keys (all required) and their meanings — "left"/"right" are from the VIEWER's
perspective (left = smaller x):
- "head_top": topmost point of the head (including hair)
- "neck_base": center of the neck base, on the shoulder line
- "left_shoulder" / "right_shoulder": outermost point of each shoulder (acromion)
- "chest_left" / "chest_right": body silhouette edges at chest (nipple) height
- "waist_left" / "waist_right": body silhouette edges at the FIXED vertical midpoint \
between the chest (nipple) level and the widest hip level — i.e. y = (chest y + hip y) / 2. \
This is a geometric level, NOT the narrowest point and NOT the navel
- "hip_left" / "hip_right": body silhouette edges at the widest hip level
- "left_wrist": center of the left wrist
- "crotch": crotch point where the legs meet
- "left_ankle": center of the left ankle joint
- "left_heel" / "right_heel": bottom point of each heel (floor contact)

Every value must be [x, y] integer pixel coordinates within the image.
Example format: {{"head_top": [540, 32], "neck_base": [538, 210], ...}}
"""

_RETRY_SUFFIX = (
    "\nYour previous reply could not be parsed as JSON. "
    "Return ONLY the raw JSON object this time — it must start with '{' and end with '}'."
)


def _load_api_key() -> str:
    """server/.env에서 키 로드. UTF-8 BOM(메모장 저장) 대응: utf-8-sig."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    raise RuntimeError(
        "ANTHROPIC_API_KEY를 찾을 수 없습니다 (server/.env 또는 환경변수)"
    )


def extract_body_landmarks(
    image_base64: str,
    width: int,
    height: int,
    mime_type: str = "image/jpeg",
) -> dict[str, list[float]]:
    """사진에서 15개 신체 랜드마크의 픽셀 좌표를 추출한다.

    입력은 CapturedImage 규격과 동일 (base64: data: 프리픽스 없는 원본 데이터).
    반환: {랜드마크: [x, y]} — measure.distance_mm()에 바로 사용 가능.

    Raises:
      ValueError: 재시도 후에도 유효한 좌표 JSON을 얻지 못한 경우
    """
    client = anthropic.Anthropic(api_key=_load_api_key())
    prompt = _PROMPT_TEMPLATE.format(width=width, height=height)

    last_error = ""
    for attempt in range(2):  # 최초 1회 + 재요청 1회 (무한루프 금지 — B-5)
        text = _call_vision(
            client, image_base64, mime_type,
            prompt if attempt == 0 else prompt + _RETRY_SUFFIX,
        )
        try:
            return _parse_landmarks(text, width, height)
        except ValueError as e:
            last_error = str(e)
    raise ValueError(f"신체 좌표 파싱 실패 (재시도 포함 2회): {last_error}")


def _call_vision(
    client: anthropic.Anthropic, image_base64: str, mime_type: str, prompt: str
) -> str:
    # temperature 파라미터 없음 — 현행 모델에서 제거됨(400). B-6 대응은 모듈 docstring 참조.
    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _parse_landmarks(text: str, width: int, height: int) -> dict[str, list[float]]:
    """응답 텍스트 → 좌표 dict. 코드펜스/설명문 오염 방어 (그룹 B-5)."""
    # 1) 코드펜스 제거
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    # 2) 첫 '{'부터 마지막 '}'까지만 추출 (앞뒤 설명문 무시)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("응답에 JSON 오브젝트가 없음")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}") from e

    # 3) 스키마 검증: 키 전부 + [x,y] 숫자 + 이미지 범위 내
    result: dict[str, list[float]] = {}
    for key in LANDMARK_KEYS:
        if key not in data:
            raise ValueError(f"랜드마크 누락: {key}")
        value = data[key]
        if (
            not isinstance(value, (list, tuple))
            or len(value) != 2
            or not all(isinstance(v, (int, float)) for v in value)
        ):
            raise ValueError(f"{key} 좌표 형식 오류: {value!r}")
        x, y = float(value[0]), float(value[1])
        if not (0 <= x <= width and 0 <= y <= height):
            raise ValueError(f"{key} 좌표가 이미지 밖: ({x}, {y})")
        result[key] = [x, y]
    return result


def draw_landmarks(image_bgr, landmarks: dict[str, list[float]]):
    """좌표를 원본 위에 그린 확인용 이미지 (육안 검증용)."""
    import cv2

    vis = image_bgr.copy()
    for i, (name, (x, y)) in enumerate(landmarks.items()):
        pt = (int(x), int(y))
        cv2.circle(vis, pt, 6, (0, 0, 255), -1)
        cv2.putText(vis, name, (pt[0] + 8, pt[1] - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
    return vis


if __name__ == "__main__":
    # 개발 확인용 CLI (API 호출 절약: 결과를 <이미지>.landmarks.json에 캐시)
    # 사용: python services/claude_vision.py <이미지경로> [--fresh]
    import base64 as b64
    import sys

    import cv2

    src = Path(sys.argv[1])
    fresh = "--fresh" in sys.argv
    cache = src.with_suffix(".landmarks.json")

    img = cv2.imread(str(src))
    h, w = img.shape[:2]

    if cache.exists() and not fresh:
        landmarks = json.loads(cache.read_text(encoding="utf-8"))
        print(f"(캐시 사용: {cache.name} — 새 호출 없음)")
    else:
        data = b64.b64encode(src.read_bytes()).decode()
        landmarks = extract_body_landmarks(data, w, h)
        cache.write_text(json.dumps(landmarks, indent=2), encoding="utf-8")
        print(f"(API 호출 1회 완료, 캐시 저장: {cache.name})")

    for name, (x, y) in landmarks.items():
        print(f"  {name:15s}: ({x:7.1f}, {y:7.1f})")
    out = src.with_name(f"debug_landmarks_{src.stem}.jpg")
    cv2.imwrite(str(out), draw_landmarks(img, landmarks))
    print("확인용 이미지:", out)
