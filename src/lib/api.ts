// ============================================================
// 백엔드 API 호출 레이어
// Phase 1에서는 전부 stub(더미 반환)이다. — CLAUDE.md 규칙 4 (Stub-First)
// 각 Phase에서 실제 백엔드 호출로 교체한다:
//   analyzeBody       → Phase 2-8
//   fetchClothingSpec → Phase 3-4
//   calculateFit      → Phase 4-4
// ============================================================

import type {
  BodyMeasurements,
  CapturedImage,
  ClothingSpec,
  FitResult,
  MeasurementMode,
  PhotoCheckResult,
} from '../types';

/** 백엔드 베이스 경로 — dev는 Vite 프록시(/api → localhost:8000)가 중계 */
export const API_BASE = '/api';

/**
 * 촬영 품질 판정 (층위 3, 2-8d) — POST /check-photo 실시간 폴링용.
 * AI 호출이 없는 엔드포인트라 1초 간격 폴링에 사용 가능 (2-7c).
 * @throws 서버 미응답·HTTP 오류·타임아웃 시 Error (호출부가 폴링을 계속할지 판단)
 */
export async function checkPhoto(
  image: CapturedImage,
  mode: MeasurementMode,
  timeoutMs = 5000,
): Promise<PhotoCheckResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/check-photo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image, mode }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`check-photo 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as PhotoCheckResult;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * [STUB] 신체 치수 분석 — Phase 2에서 백엔드 `/analyze` 호출로 교체.
 * 지금은 타입 규격만 맞춘 더미 데이터를 반환한다 (실제 측정 아님).
 */
// TODO(Phase 2-8): 백엔드 POST /analyze 실제 연동으로 교체
export async function analyzeBody(
  image: CapturedImage,
  mode: MeasurementMode,
): Promise<BodyMeasurements> {
  void image; // stub에서는 사용하지 않음
  return {
    height: 175,
    shoulder_width: 45,
    chest_circumference: 96,
    waist_circumference: 80,
    hip_circumference: 95,
    arm_length: 58,
    inseam: 78,
    torso_length: 62,
    confidence: {
      height: 'high',
      shoulder_width: 'high',
      chest_circumference: 'medium',
      waist_circumference: 'medium',
      hip_circumference: 'medium',
      arm_length: 'high',
      inseam: 'medium',
      torso_length: 'medium',
    },
    mode,
    reference: {
      type: mode === 'simple' ? 'card' : 'aruco',
      realWidthMm: mode === 'simple' ? 85.6 : 50,
      realHeightMm: mode === 'simple' ? 53.98 : 50,
      detected: true, // stub이므로 항상 true (실제 검출 아님)
    },
  };
}

/**
 * [STUB] 의류 스펙 추출 — Phase 3에서 백엔드 `/clothing` 호출로 교체.
 */
// TODO(Phase 3-4): 백엔드 스크래핑 + 사이즈 정규화 실제 연동으로 교체
export async function fetchClothingSpec(url: string): Promise<ClothingSpec> {
  return {
    brand: 'STUB_BRAND',
    url,
    category: 'top',
    fabric: 'cotton',
    stretch: 'low',
    sizes: [
      { label: 'S', chest_cm: 92, waist_cm: 78, hip_cm: 92 },
      { label: 'M', chest_cm: 97, waist_cm: 83, hip_cm: 97 },
      { label: 'L', chest_cm: 102, waist_cm: 88, hip_cm: 102 },
    ],
  };
}

/**
 * [STUB] 핏 계산 — Phase 4에서 백엔드 `/fit` 호출로 교체.
 */
// TODO(Phase 4-4): 치수 비교 + 사이즈 추천 실제 연동으로 교체
export async function calculateFit(
  measurements: BodyMeasurements,
  clothing: ClothingSpec,
): Promise<FitResult> {
  return {
    measurements,
    clothing,
    recommendedSize: 'M',
    scores: [
      { part: 'chest', status: 'good', diff_cm: 1 },
      { part: 'waist', status: 'good', diff_cm: 3 },
      { part: 'hip', status: 'good', diff_cm: 2 },
    ],
    recommendation:
      '[STUB] 더미 추천 문구입니다. Phase 4에서 실제 핏 분석으로 교체됩니다.',
  };
}
