// ============================================================
// FITME 공유 타입 정의 (Contract-First)
// 이 파일은 CLAUDE.md 6장과 1:1로 동기화한다.
// 타입 변경 시 CLAUDE.md를 먼저 업데이트한 뒤 이 파일에 반영한다.
// ============================================================

// ===== 측정 모드 & 기준물 =====
export type MeasurementMode = 'simple' | 'precise';
export type ReferenceObject = 'card' | 'aruco';

export interface ReferenceInfo {
  type: ReferenceObject;
  realWidthMm: number;   // card: 85.6, aruco: 출력 크기(예: 50)
  realHeightMm: number;  // card: 53.98, aruco: 정사각형이면 width와 동일
  detected: boolean;     // 사진에서 검출 성공 여부
  cornersPx?: [number, number][]; // 검출된 네 꼭짓점 픽셀 좌표
}

// ===== 촬영 품질 판정 (촬영 가이드 층위 3 — 2-7c 산출물) =====
export interface PhotoCheckResult {
  ready: boolean;           // 모든 조건 충족 → 자동 촬영 가능
  reference: ReferenceInfo; // 검출 결과 (미검출이면 detected:false)
  markerSizeOk: boolean;    // 마커 크기 충분 (원거리·저해상도 방지)
  markerCentered: boolean;  // 마커가 화면 중앙 영역에 위치
  tiltOk: boolean;          // 가로세로 척도 비율이 정면 범위(≈1)
  reasons: string[];        // 불충족 사유 (한국어, 사용자 안내용)
}

// ===== 사용자 프로필 (정확도 보강 입력 — 2-6 결정, 구현은 2-7b) =====
export interface UserProfile {
  heightCm: number;   // 키(cm) — 스케일 캘리브레이션 기준값 (필수)
  weightKg?: number;  // 몸무게(kg) — 둘레 깊이 계수(BMI) 보정용 (선택)
}

// ===== 캡처 이미지 (Phase 1 → 2, 1 → 5 공통 규격) =====
export interface CapturedImage {
  base64: string;        // 이미지 데이터 (data: 프리픽스 제외)
  width: number;         // 리사이즈 후 너비 (항상 1080 기준)
  height: number;
  mimeType: string;      // "image/jpeg"
  rotation: number;      // EXIF 보정 후 항상 0
  frames?: string[];     // 다중 프레임(전략 3)용 base64 배열
}

// ===== 신체 치수 (Phase 2 산출물) =====
export interface BodyMeasurements {
  height: number;              // 키 (cm)
  shoulder_width: number;      // 어깨 너비
  chest_circumference: number; // 가슴 둘레
  waist_circumference: number; // 허리 둘레
  hip_circumference: number;   // 엉덩이 둘레
  arm_length: number;          // 팔 길이
  inseam: number;              // 다리 안쪽 길이
  torso_length: number;        // 상체 길이
  confidence: Record<string, 'high' | 'medium' | 'low'>;
  mode: MeasurementMode;       // 어떤 모드로 측정했는지
  reference: ReferenceInfo;    // 사용한 기준물 정보
}

// ===== /analyze 응답 (Phase 2-8a — 미검출·실패를 가짜 숫자 없이 전달) =====
export interface AnalyzeStats {
  runs: number;                            // 랜드마크 추출에 성공한 프레임 수
  spreadCm: Record<string, number>;        // 항목별 반복 편차 (cm)
  scale: Record<string, number | string>;  // 사용 척도 요약 (역추적용)
}

export interface AnalyzeResponse {
  ok: boolean;                     // 측정 성공 여부
  reference: ReferenceInfo;        // 기준물 검출 결과 (미검출이면 detected:false)
  measurements?: BodyMeasurements; // ok=true일 때만 존재
  warnings: string[];              // 범위·해부학·척도·대칭 경고 (한국어)
  stats?: AnalyzeStats;            // ok=true일 때만 존재
  error?: string;                  // ok=false 사유 (한국어, 재촬영 안내용)
}

// ===== 의류 스펙 (Phase 3 산출물) =====
// 부위 필드는 전부 선택 — 의류 종류마다 제공 부위가 다르다 (무신사 실증:
// 상의 = 가슴·어깨·소매·총장, 하의 = 허리·엉덩이·허벅지·밑위·총장·밑단).
// 없는 부위를 0 등 가짜 숫자로 채우지 않는다 (규칙 1). 단면(flat) 표기는
// ×2로 둘레 환산해 저장한다 (3-3 결정, 2026-07-17).
export interface ClothingSize {
  label: string;         // 원본 표기: "M", "95", "L", "Free"
  chest_cm?: number;     // 가슴둘레 (단면×2 환산)
  waist_cm?: number;     // 허리둘레 (단면×2)
  hip_cm?: number;       // 엉덩이둘레 (단면×2)
  shoulder_cm?: number;  // 어깨너비 (직선)
  sleeve_cm?: number;    // 소매길이
  length_cm?: number;    // 총장
  thigh_cm?: number;     // 허벅지둘레 (단면×2)
  rise_cm?: number;      // 밑위
  hem_cm?: number;       // 밑단둘레 (단면×2)
  estimated?: boolean;   // true = 실측이 아닌 호칭 기반 근사 (label 변환표 산출)
}

export interface ClothingSpec {
  brand: string;
  url: string;
  category: 'top' | 'bottom' | 'dress' | 'outer';
  productName?: string;        // 표시용 상품명
  fabric?: string;
  stretch?: 'none' | 'low' | 'high';
  sizes: ClothingSize[];       // 정규화된 사이즈 목록
  needsUserInput?: boolean;    // 정규화 불가 표기 존재 → 사용자 실측 입력 요청
  warnings?: string[];         // 정규화 과정 경고 (한국어)
}

// ===== /clothing 응답 (Phase 3-4 — 스크래핑 실패를 크래시 없이 전달) =====
export interface ClothingResponse {
  ok: boolean;
  spec?: ClothingSpec;   // ok=true일 때만 존재
  cached?: boolean;      // 서버 SQLite 캐시 적중 여부 (재조회는 무신사 접속 없음)
  error?: string;        // ok=false 사유 (한국어, 사용자 안내용)
  code?: 'unsupported' | 'not-found' | 'no-size' | 'network'; // 분기용
}

// ===== 핏 스코어 (Phase 4 산출물) =====
export interface FitScore {
  part: string;                       // chest/waist/hip 등
  status: 'tight' | 'good' | 'loose';
  diff_cm: number;                    // 여유(+)/부족(-) cm
  confidence?: 'high' | 'medium' | 'low'; // 해당 부위 측정 신뢰도 전파 (4-1) —
                                          // low면 판정 자체가 불확실 (둘레 3종 등 12장 한계)
}

// ===== 최종 결과 (Phase 4~5 통합) =====
export interface FitResult {
  measurements: BodyMeasurements;
  clothing: ClothingSpec;
  recommendedSize: string;
  scores: FitScore[];          // 추천 사이즈의 부위별 판정
  recommendation: string;      // 자연어 추천 (한국어)
  imageUrl?: string;           // Phase 5 합성 이미지
}

// ===== /fit 응답 (Phase 4-4 — 추천 불가를 가짜 사이즈 없이 전달) =====
export interface FitResponse {
  ok: boolean;
  result?: FitResult;   // ok=true일 때만 존재
  warnings: string[];   // insufficient(A안)·estimated·신뢰도 등 경고 (한국어)
  error?: string;       // ok=false 사유 (한국어 — 예: 비교 가능한 부위 실측 없음)
}
