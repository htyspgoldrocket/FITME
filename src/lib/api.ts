// ============================================================
// 백엔드 API 호출 레이어
// Phase 1에서는 전부 stub(더미 반환)으로 시작했다. — CLAUDE.md 규칙 4 (Stub-First)
// 각 Phase에서 실제 백엔드 호출로 교체한다:
//   analyzeBody       → Phase 2-8 ✅ 교체 완료
//   fetchClothingSpec → Phase 3-4 ✅ 교체 완료
//   calculateFit      → Phase 4-4 (아직 stub)
// ============================================================

import type {
  AnalyzeResponse,
  BodyMeasurements,
  CapturedImage,
  ClothingResponse,
  ClothingSpec,
  FitResult,
  MeasurementMode,
  PhotoCheckResult,
  UserProfile,
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
 * 신체 치수 분석 (2-8e — stub에서 실제 연동으로 교체 완료).
 * POST /analyze: 기준물 검출 → 프레임별 랜드마크(프레임당 AI 1회, 기본 7회)
 * → 다중 프레임 중앙값 + 키 캘리브레이션. 프레임 수만큼 AI를 호출하므로
 * 오래 걸린다 (수십 초 ~ 수 분) — 타임아웃을 넉넉히 둔다.
 *
 * 미검출·추출 실패는 예외가 아니라 AnalyzeResponse.ok=false + error(한국어)로
 * 돌아온다 (재촬영 안내용). 예외는 네트워크/서버 오류일 때만 던진다.
 */
export async function analyzeBody(
  image: CapturedImage,
  mode: MeasurementMode,
  profile: UserProfile | null,
  timeoutMs = 180_000,
): Promise<AnalyzeResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image, mode, ...(profile ? { profile } : {}) }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`analyze 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as AnalyzeResponse;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 의류 스펙 추출 (3-4b — stub에서 실제 연동으로 교체 완료).
 * POST /clothing: 서버 SQLite 캐시 → (미스 시) 무신사 스크래핑(3-2) + 정규화(3-3).
 * 첫 조회는 Playwright 브라우저 기동 포함 십수 초가 걸릴 수 있다 (캐시 적중은 즉시).
 *
 * 지원 외 쇼핑몰·없는 상품 등은 예외가 아니라 ok=false + error(한국어)로
 * 돌아온다 (AnalyzeResponse와 같은 방식). 예외는 네트워크/서버 오류일 때만.
 */
export async function fetchClothingSpec(
  url: string,
  timeoutMs = 60_000,
): Promise<ClothingResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/clothing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`clothing 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as ClothingResponse;
  } finally {
    clearTimeout(timer);
  }
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
