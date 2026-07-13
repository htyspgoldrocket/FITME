# ✅ Phase 1 Gate 리포트 — 모바일 앱 기반 구축

- **판정일**: 2026-07-14
- **판정**: **통과** (자동 · 수동 · 통합 · 보안 전 항목)
- **사용자 승인**: 2026-07-14 사용자가 "Phase 1이 검증을 통과했어"로 명시 승인
- **다음 Phase 진입 가능 여부**: **가능** (Phase 2)

---

## 자동 검증 — 통과

| 항목 | 실행 방법 | 결과 |
|------|-----------|------|
| 빌드 | `npm run build` (tsc && vite build) | 에러 0건, PWA sw.js/manifest 생성 확인 |
| 타입 체크 | `tsc --noEmit` | 타입 불일치 0건 |
| stub 규격 | `src/lib/api.ts`를 esbuild로 번들 → Node에서 실제 호출 (`check-stub.mjs`) | 12/12 PASS |

stub 검증 세부: `analyzeBody`가 simple/precise 두 모드 모두에서 `BodyMeasurements`
규격(8개 수치 필드, confidence 레코드, mode 일치, reference 구조·모드-기준물 일치)을
충족. `fetchClothingSpec` → `ClothingSpec`, `calculateFit` → `FitResult` 규격 충족.

## 수동 검증 — 통과 (실제 폰, 사용자 직접 확인)

접속 방법: `npm run dev` + Cloudflare 빠른 터널(`cloudflared tunnel --url http://localhost:5173`).

- [x] 모바일 브라우저에서 후면 카메라 실행
- [x] 모드 선택 → 카메라 → 촬영 → 미리보기 → 재촬영 순서 동작
- [x] 세로/가로 촬영 모두 미리보기 정방향
- [x] 선택한 모드가 화면 전환 후에도 유지
- [x] 🔄 전면 카메라 전환: 미리보기 거울상, 촬영·재촬영 정상, 재촬영 후 전면 유지

## 통합 검증 — 통과

**데스크톱 자동 주행** (Chrome headless + 가짜 카메라 장치, puppeteer — `e2e-smoke.mjs`):
앱 시작 → 모드 선택 → 카메라(스트림 재생) → 촬영 → 미리보기(**1080×608px, JPEG**)
→ 재촬영 → 사진 확정까지 9/9 PASS. 스크린샷 육안 확인 완료.

**카메라 전환 회귀** (`e2e-flip.mjs`): 후면→전면→촬영→재촬영(전면 유지)→후면 복귀 5/5 PASS.

**실기기 전체 플로우**: 위 수동 검증에서 사용자가 폰으로 완주 확인.

`rotation=0` 보장 근거: 캡처가 비디오 프레임 → Canvas 방식이라 EXIF 메타데이터가
원천적으로 존재하지 않음 (파일 업로드 경로 없음).

## 보안 — 통과

- `git ls-files`에 `.env` 계열 파일 없음
- `server/.env`(플레이스홀더)를 실제로 만들어 `git check-ignore -v`로 `.gitignore:4`가
  차단함을 확인
- 프론트엔드에 API 키 없음 (Phase 1은 백엔드 미구현, stub만 존재)

## 검증 중 발견·수정한 버그

1. **카메라 전환 중 셔터 레이스**: 스트림 교체가 끝나기 전 셔터를 누르면 빈 프레임
   캡처 에러 발생 → 새 스트림 `loadeddata` 전까지 셔터 비활성화로 수정 (1e69b2a)
2. **재촬영 시 전/후면 선택 초기화**: CameraView 재마운트로 facing 상태 소실 →
   상태를 App으로 승격해 유지 (1e69b2a)

## 미해결 이슈

- 없음

## 관련 커밋

| 커밋 | 내용 |
|------|------|
| 0d199e9 | 1-1: Vite+React+TS 셋업 + .gitignore(.env) |
| a190bf9 | 1-2: src/types/index.ts 공유 타입 전체 정의 |
| d841f77 | 1-3: analyzeBody/fetchClothingSpec/calculateFit stub |
| 21c0247 | 1-4: 모드 선택 UI + PWA 설정 |
| 072b0f2 | 1-5: 후면 카메라 UI + 가이드 오버레이 + 자이로 |
| 7278491 | 1-6: 촬영 → 미리보기 → 재촬영 + 1080px 리사이즈 |
| 1e69b2a | 추가: 전면/후면 카메라 전환 + 레이스 버그 수정 |
| 984a7fd | dev: Cloudflare 터널 allowedHosts |
