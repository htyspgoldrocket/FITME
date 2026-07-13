# PROGRESS.md — FITME 진행 상황

## 현재 위치
- **Phase**: 1 (모바일 앱 기반 구축) — 개발 완료, **수동 검증(사용자 폰 테스트) 대기 중**
- **다음 할 일**: 사용자 수동 검증 → Gate 승인 → Phase 2 진입

## Phase 1 Step 완료 이력
| Step | 내용 | 커밋 |
|------|------|------|
| 1-1 | Vite+React+TS 셋업 + .gitignore(.env) | 0d199e9 |
| 1-2 | src/types/index.ts 공유 타입 전체 정의 | a190bf9 |
| 1-3 | analyzeBody/fetchClothingSpec/calculateFit stub | d841f77 |
| 1-4 | 모드 선택 UI + PWA 설정 | 21c0247 |
| 1-5 | 후면 카메라 UI + 가이드 오버레이 + 자이로 | 072b0f2 |
| 1-6 | 촬영 → 미리보기 → 재촬영 + 1080px 리사이즈 | 7278491 |

## Phase 1 Gate 리포트 (2026-07-13)

### 자동 검증 — ✅ 통과
- `npm run build` (tsc 포함): 에러 0건 통과
- `tsc --noEmit`: 타입 불일치 0건
- stub 형태 검증: `analyzeBody`를 esbuild 번들 후 Node에서 실제 호출 —
  simple/precise 두 모드 모두 `BodyMeasurements` 규격(8개 수치 필드, confidence,
  mode, reference) 충족. 12개 체크 전부 PASS.

### 통합 검증 — ✅ 데스크톱 통과 / ⏳ 실기기 확인 대기
- Chrome(가짜 카메라 장치, puppeteer)로 빌드본 자동 주행:
  모드 선택 → 카메라(비디오 스트림 재생) → 촬영 → 미리보기(1080×608, JPEG)
  → 재촬영 → 사진 확정까지 9개 체크 전부 PASS. rotation=0은 비디오 프레임
  캡처 방식상 EXIF가 존재하지 않아 구조적으로 보장.
- 실제 모바일 기기에서의 동일 플로우는 아래 수동 검증에 포함.

### 수동 검증 — ⏳ 사용자 확인 대기 (규칙 3: 자동만으로 통과 처리 금지)
- [ ] iOS Safari + Android Chrome에서 후면 카메라 실행
- [ ] 모드 선택 → 카메라 → 촬영 → 미리보기 → 재촬영 순서 동작
- [ ] 세로/가로 촬영 모두 미리보기 정방향
- [ ] 선택한 모드가 화면 전환 후에도 유지

### 보안 — ✅ 통과
- `git ls-files`에 `.env` 없음. `server/.env`는 `.gitignore:4`가 차단함을
  `git check-ignore -v`로 확인.

### 미해결 이슈
- 없음 (수동 검증 대기 항목 제외)

### 다음 Phase 진입 가능 여부
- **불가** — 수동 검증 4항목이 사용자 확인 전. 통과 확인 + 사용자 승인 후 Phase 2 진입.

## 수동 검증 방법 (사용자용)
1. `npm run dev` 실행 (포트 5173)
2. 폰 카메라는 HTTPS가 필요하므로 별도 터미널에서 `ngrok http 5173` 실행
3. ngrok이 출력한 https URL을 폰(iOS Safari / Android Chrome)에서 접속
4. 위 수동 검증 4항목 확인 후 결과 회신

## 마지막 커밋
- 7278491 (Phase 1-Step 6)
