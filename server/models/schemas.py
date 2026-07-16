"""FITME Pydantic 모델 — src/types/index.ts 와 1:1 대응 (Contract-First).

타입 변경 시 CLAUDE.md 6장 → src/types/index.ts → 이 파일 순으로 함께 갱신한다.
JSON 필드명은 프론트 계약과의 일치를 위해 TS 쪽 표기(camelCase 혼용)를 그대로 따른다.
"""

from typing import Literal, Optional

from pydantic import BaseModel

# ===== 측정 모드 & 기준물 =====
MeasurementMode = Literal["simple", "precise"]
ReferenceObject = Literal["card", "aruco"]

Confidence = Literal["high", "medium", "low"]


class ReferenceInfo(BaseModel):
    type: ReferenceObject
    realWidthMm: float   # card: 85.6, aruco: 출력 크기(예: 50)
    realHeightMm: float  # card: 53.98, aruco: 정사각형이면 width와 동일
    detected: bool       # 사진에서 검출 성공 여부
    cornersPx: Optional[list[tuple[float, float]]] = None  # 검출된 네 꼭짓점 픽셀 좌표


# ===== 캡처 이미지 (Phase 1 → 2, 1 → 5 공통 규격) =====
class CapturedImage(BaseModel):
    base64: str          # 이미지 데이터 (data: 프리픽스 제외)
    width: int           # 리사이즈 후 너비 (항상 1080 기준)
    height: int
    mimeType: str        # "image/jpeg"
    rotation: int        # EXIF 보정 후 항상 0
    frames: Optional[list[str]] = None  # 다중 프레임(전략 3)용 base64 배열


# ===== 신체 치수 (Phase 2 산출물) =====
class BodyMeasurements(BaseModel):
    height: float                # 키 (cm)
    shoulder_width: float        # 어깨 너비
    chest_circumference: float   # 가슴 둘레
    waist_circumference: float   # 허리 둘레
    hip_circumference: float     # 엉덩이 둘레
    arm_length: float            # 팔 길이
    inseam: float                # 다리 안쪽 길이
    torso_length: float          # 상체 길이
    confidence: dict[str, Confidence]
    mode: MeasurementMode        # 어떤 모드로 측정했는지
    reference: ReferenceInfo     # 사용한 기준물 정보


# ===== 의류 스펙 (Phase 3 산출물) =====
class ClothingSize(BaseModel):
    label: str       # 원본 표기: "M", "95", "L", "Free"
    chest_cm: float  # 정규화된 실측 (cm)
    waist_cm: float
    hip_cm: float


class ClothingSpec(BaseModel):
    brand: str
    url: str
    category: Literal["top", "bottom", "dress", "outer"]
    fabric: Optional[str] = None
    stretch: Optional[Literal["none", "low", "high"]] = None
    sizes: list[ClothingSize]  # 정규화된 사이즈 목록


# ===== 핏 스코어 (Phase 4 산출물) =====
class FitScore(BaseModel):
    part: str                                   # chest/waist/hip 등
    status: Literal["tight", "good", "loose"]
    diff_cm: float                              # 여유(+)/부족(-) cm


# ===== 최종 결과 (Phase 4~5 통합) =====
class FitResult(BaseModel):
    measurements: BodyMeasurements
    clothing: ClothingSpec
    recommendedSize: str
    scores: list[FitScore]
    recommendation: str          # 자연어 추천 (한국어)
    imageUrl: Optional[str] = None  # Phase 5 합성 이미지


# ===== 촬영 품질 판정 (촬영 가이드 층위 3 — 2-7c 산출물) =====
class PhotoCheckResult(BaseModel):
    ready: bool                # 모든 조건 충족 → 자동 촬영 가능
    reference: ReferenceInfo   # 검출 결과 (미검출이면 detected:false)
    markerSizeOk: bool         # 마커 크기 충분
    markerCentered: bool       # 마커가 화면 중앙 영역에 위치
    tiltOk: bool               # 가로세로 척도 비율이 정면 범위(≈1)
    reasons: list[str]         # 불충족 사유 (한국어, 사용자 안내용)


# ===== 사용자 프로필 (정확도 보강 입력 — 2-6 결정, 2-7b 구현) =====
class UserProfile(BaseModel):
    heightCm: float            # 키(cm) — 스케일 캘리브레이션 기준값 (필수)
    weightKg: Optional[float] = None  # 몸무게(kg) — 둘레 깊이 계수(BMI) 보정용 (선택)


# ===== /analyze 요청 (Phase 2) =====
class AnalyzeRequest(BaseModel):
    image: CapturedImage
    mode: MeasurementMode
    # 2-8에서 프론트 입력 UI가 연결되기 전까지는 선택 필드 (기존 호출 규격 불파손)
    profile: Optional[UserProfile] = None


# ===== /check-photo 요청 (2-7c) =====
class CheckPhotoRequest(BaseModel):
    image: CapturedImage
    mode: MeasurementMode
