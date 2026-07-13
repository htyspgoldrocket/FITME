# PROGRESS.md — FITME 진행 상황

> 세션이 끊겨도 이 파일 + CLAUDE.md + `src/types/index.ts`만 읽으면 이어서 개발할 수 있다.

## 현재 위치

- **Phase 1: ✅ 완료** (2026-07-14, Gate 전 항목 통과 + 사용자 승인)
  - Gate 리포트: `docs/gate-reports/phase-1-gate.md`
- **다음 시작 지점: Phase 2 — Step 2-1** (아래 "다음 할 일" 참조)

## Phase 1 완료 스냅샷

### 만들어진 것 (전부 실기기 검증 완료)
```
앱 플로우:  모드 선택(간편/정밀) → 카메라(전/후면) → 촬영 → 미리보기 → 재촬영/확정
```

| 파일 | 역할 |
|------|------|
| `src/types/index.ts` | 공유 타입 전체 (CLAUDE.md 6장과 1:1 동기화) — Phase 2~5 계약 |
| `src/lib/api.ts` | `analyzeBody`/`fetchClothingSpec`/`calculateFit` **stub** (더미 반환) |
| `src/lib/camera.ts` | `startCamera(facing)` 전/후면 + 폴백, 자이로 수직 감시 |
| `src/lib/image.ts` | `captureFromVideo`: 1080px 리사이즈, JPEG 85%, rotation=0 |
| `src/components/ModeSelect.tsx` | 간편/정밀 모드 선택 화면 |
| `src/components/CameraView.tsx` | 카메라 + 가이드 오버레이 + 자이로 + 전환/셔터 |
| `src/components/PhotoPreview.tsx` | 미리보기 + 재촬영/사용 |
| `src/App.tsx` | 화면 상태 머신 (mode-select→camera→preview→done) |
| `vite.config.ts` | PWA(manifest+sw) + dev 터널 allowedHosts |

### 세션 복원 시 알아야 할 설계 결정
1. **캡처는 절대 거울상 금지** — 전면 카메라도 미리보기만 CSS 반전. ArUco는 좌우
   반전 시 검출 불가 (`camera.ts`, `CameraView.tsx` 주석 참조).
2. **rotation=0 구조적 보장** — 비디오 프레임→Canvas 캡처라 EXIF 없음. 파일 업로드
   경로를 추가하게 되면 그때는 EXIF 보정 필요.
3. **셔터는 스트림 `loadeddata` 전 비활성** — 전환 중 빈 프레임 캡처 레이스 방지.
4. **facing 상태는 App 보관** — 재촬영 후에도 전/후면 유지.
5. **stub 교체 시점**: `analyzeBody`→Phase 2-8, `fetchClothingSpec`→Phase 3-4,
   `calculateFit`→Phase 4-4. 그 전에는 건드리지 않는다 (규칙 4·5).

### 폰 수동 검증 방법 (Phase 2에서도 동일하게 사용)
1. `npm run dev` (포트 5173)
2. `& "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" tunnel --url http://localhost:5173`
3. 출력된 `https://*.trycloudflare.com` URL을 폰에서 접속 (HTTPS라 카메라 허용됨)
4. ⚠️ Phase 2부터는 백엔드에 API 키가 생기므로 터널은 검증 시간에만 짧게 열 것

### 검증 자산 (스크래치패드에 있던 것 — 필요 시 재작성 가능)
- stub 규격 검사(`check-stub.mjs`), 전체 플로우 스모크(`e2e-smoke.mjs`),
  카메라 전환 스모크(`e2e-flip.mjs`) — puppeteer-core + Chrome 가짜 카메라 방식.
- CLAUDE.md 13-4에 따라 Phase 2부터는 `server/tests/`에 정식 보관할 것.

## 다음 할 일 — Phase 2: 신체 치수 분석 엔진

**시작 전 필수 (규칙 2 / 5-3)**: Phase 2를 Step 목록(권장: 2-1~2-8, CLAUDE.md 9장)으로
분해해 사용자 확인부터 받는다.

- **Step 2-1**: FastAPI 서버 스캐폴딩 + `/analyze` 빈 엔드포인트 (더미 응답)
  - `server/main.py`, `server/routes/analyze.py`, Pydantic 모델(타입과 1:1)
  - 버전 고정: fastapi ^0.109.0, uvicorn ^0.27.0, pydantic ^2.5.0, anthropic ^0.18.0,
    opencv-python ^4.9.0, numpy ^1.26.0, pillow ^10.2.0 (규칙 8 — 임의 상향 금지)
  - `server/.env`에 API 키 (이미 .gitignore:4로 차단 확인됨)
- **사전 준비물 (사용자에게 요청할 것)**: 카드 포함 전신 사진 + 줄자 실측 정답값,
  **최소 3명분** (`server/tests/fixtures/`에 보관)
- Phase 2 Gate: 자동 7항목 + 수동 실측 비교(길이 ±3cm, 둘레 ±5cm, 3명 전원) + 통합

## Phase 1 커밋 이력

| Step | 내용 | 커밋 |
|------|------|------|
| 1-1 | Vite+React+TS 셋업 + .gitignore(.env) | 0d199e9 |
| 1-2 | src/types/index.ts 공유 타입 전체 정의 | a190bf9 |
| 1-3 | analyzeBody/fetchClothingSpec/calculateFit stub | d841f77 |
| 1-4 | 모드 선택 UI + PWA 설정 | 21c0247 |
| 1-5 | 후면 카메라 UI + 가이드 오버레이 + 자이로 | 072b0f2 |
| 1-6 | 촬영 → 미리보기 → 재촬영 + 1080px 리사이즈 | 7278491 |
| 추가 | 전면/후면 카메라 전환 + 레이스 수정 | 1e69b2a |
| — | dev 터널 allowedHosts | 984a7fd |
