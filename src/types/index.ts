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

// ===== 의류 스펙 (Phase 3 산출물) =====
export interface ClothingSize {
  label: string;         // 원본 표기: "M", "95", "L", "Free"
  chest_cm: number;      // 정규화된 실측 (cm)
  waist_cm: number;
  hip_cm: number;
}

export interface ClothingSpec {
  brand: string;
  url: string;
  category: 'top' | 'bottom' | 'dress' | 'outer';
  fabric?: string;
  stretch?: 'none' | 'low' | 'high';
  sizes: ClothingSize[];       // 정규화된 사이즈 목록
}

// ===== 핏 스코어 (Phase 4 산출물) =====
export interface FitScore {
  part: string;                       // chest/waist/hip 등
  status: 'tight' | 'good' | 'loose';
  diff_cm: number;                    // 여유(+)/부족(-) cm
}

// ===== 최종 결과 (Phase 4~5 통합) =====
export interface FitResult {
  measurements: BodyMeasurements;
  clothing: ClothingSpec;
  recommendedSize: string;
  scores: FitScore[];
  recommendation: string;      // 자연어 추천 (한국어)
  imageUrl?: string;           // Phase 5 합성 이미지
}
