// ============================================================
// 백엔드 API 호출 레이어
// Phase 1에서는 전부 stub(더미 반환)으로 시작했다. — CLAUDE.md 규칙 4 (Stub-First)
// 각 Phase에서 실제 백엔드 호출로 교체한다:
//   analyzeBody       → Phase 2-8 ✅ 교체 완료
//   fetchClothingSpec → Phase 3-4 ✅ 교체 완료
//   calculateFit      → Phase 4-4 ✅ 교체 완료 (Phase 1 stub 전부 소진)
// ============================================================

import type {
  AnalyzeResponse,
  BetaStatus,
  BodyMeasurements,
  CapturedImage,
  ClothingResponse,
  ClothingSpec,
  FitResponse,
  MeasurementMode,
  PhotoCheckResult,
  SynthesizeResponse,
  UserProfile,
} from '../types';

/** 백엔드 베이스 경로 — dev는 Vite 프록시(/api → localhost:8000)가 중계 */
export const API_BASE = '/api';

// ===== 베타 게이트 (6-2 — 주변인 무료 베타 접근 코드) =====

const BETA_CODE_KEY = 'fitme-beta-code';
// localStorage 접근 불가(시크릿 모드 등) 시 세션 동안만 유지하는 폴백
let betaCodeInMemory: string | null = null;

/** 저장된 베타 코드 — 없으면 null (로컬 개발 = 게이트 비활성이라 무해) */
export function getBetaCode(): string | null {
  try {
    return localStorage.getItem(BETA_CODE_KEY) ?? betaCodeInMemory;
  } catch {
    return betaCodeInMemory;
  }
}

export function saveBetaCode(code: string): void {
  betaCodeInMemory = code;
  try {
    localStorage.setItem(BETA_CODE_KEY, code);
  } catch {
    /* 저장 불가 — 메모리 폴백으로 세션 동안만 유지 */
  }
}

/** AI 비용 라우트(/analyze·/synthesize)에 붙일 베타 코드 헤더 */
function betaHeaders(): Record<string, string> {
  const code = getBetaCode();
  return code ? { 'X-Beta-Code': code } : {};
}

/**
 * 베타 게이트 상태 확인 (6-2) — GET /beta, AI 호출 0·사용량 카운트 0.
 * @throws 서버 미응답·HTTP 오류 시 Error — 호출부(BetaGate)는 fail-open
 *         (UX는 열고, 실제 방어는 백엔드 access_guard가 담당)
 */
export async function fetchBetaStatus(
  code: string | null,
  timeoutMs = 5000,
): Promise<BetaStatus> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/beta`, {
      headers: code ? { 'X-Beta-Code': code } : {},
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`beta 확인 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as BetaStatus;
  } finally {
    clearTimeout(timer);
  }
}

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
      // 베타 코드(6-2) — 배포 환경에서 access_guard(6-1)가 검사
      headers: { 'Content-Type': 'application/json', ...betaHeaders() },
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
 * 핏 계산 (4-4b — stub에서 실제 연동으로 교체 완료. Phase 1 stub 전부 소진).
 * POST /fit: 부위 비교(4-1) → 사이즈 추천(4-2, 하의 허리 A안) → 자연어
 * 피드백(4-3, Claude API 1회 — 실패 시 서버가 템플릿 폴백하므로 요청은 성공).
 *
 * 추천 불가(비교 가능한 실측 없음)는 예외가 아니라 ok=false + error(한국어).
 */
export async function calculateFit(
  measurements: BodyMeasurements,
  clothing: ClothingSpec,
  timeoutMs = 60_000,
): Promise<FitResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/fit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ measurements, clothing }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`fit 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as FitResponse;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * 가상 착용 이미지 합성 (5-3a — Phase 5-2c 백엔드 신규 연동).
 * POST /synthesize: 촬영 사진 + 의류 이미지 → 합성 이미지(base64). VTON 호출
 * 1회로 수십 초 걸릴 수 있어 타임아웃을 넉넉히 둔다.
 *
 * ⚠️ 서버가 쓰는 VTON 모델은 상업 사용 금지 라이선스(CLAUDE.md 12장) — 개발용.
 *
 * 합성용 이미지 없음·VTON 실패는 예외가 아니라 ok=false + error(한국어)로
 * 돌아온다 (AnalyzeResponse와 같은 방식). 예외는 네트워크/서버 오류일 때만.
 *
 * humanImage.frames(다중 프레임)는 서버가 쓰지 않으므로 전송에서 제외한다 —
 * 최대 7장을 그대로 보내면 페이로드가 7배로 불어난다.
 */
export async function synthesizeImage(
  humanImage: CapturedImage,
  clothing: ClothingSpec,
  timeoutMs = 120_000,
): Promise<SynthesizeResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const { frames: _frames, ...humanImageWithoutFrames } = humanImage;
  try {
    const res = await fetch(`${API_BASE}/synthesize`, {
      method: 'POST',
      // 베타 코드(6-2) — 배포 환경에서 access_guard(6-1)가 검사
      headers: { 'Content-Type': 'application/json', ...betaHeaders() },
      body: JSON.stringify({ humanImage: humanImageWithoutFrames, clothing }),
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`synthesize 실패: HTTP ${res.status}`);
    }
    return (await res.json()) as SynthesizeResponse;
  } finally {
    clearTimeout(timer);
  }
}
