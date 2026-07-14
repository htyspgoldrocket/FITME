# PROGRESS.md — FITME 진행 상황

> 세션이 끊겨도 이 파일 + CLAUDE.md + `src/types/index.ts`만 읽으면 이어서 개발할 수 있다.

## 현재 위치

- **Phase 1: ✅ 완료 + 수정 재검증 완료** (2026-07-14, Gate 통과, 태그 `phase-1-complete`)
  - Gate 리포트(수정 이력 포함): `docs/gate-reports/phase-1-gate.md`
- **Phase 2: 🔄 진행 중 — Step 2-1 완료** (2026-07-14, 사용자 직접 확인 + 자동 테스트 통과)
- **다음 시작 지점: Step 2-2 — OpenCV 신용카드 사각형 검출 (간편 모드)**
  - 만들 것: `server/services/reference_detect.py` (윤곽 검출 → 4꼭짓점 →
    85.6:53.98 비율 필터 → `ReferenceInfo` 반환) + 검출 테스트
  - 필요물: 카드 포함 전신 사진 최소 1장 (`server/tests/fixtures/`) — 사용자에게 요청

## Phase 2 Step 완료 이력

### Step 2-1 — FastAPI 스캐폴딩 + /analyze 더미 (2026-07-14 완료)

**만든 파일**
- `server/main.py` — FastAPI 앱, CORS(localhost:5173), `/health`
- `server/requirements.txt` — CLAUDE.md 8장 버전 고정 (전부 범위 내 설치 확인)
- `server/models/schemas.py` — `src/types/index.ts`와 1:1 Pydantic 모델
- `server/routes/analyze.py` — `POST /analyze` 더미 (응답에 `"stub"` 표시 필드,
  규칙 1의 의도된 예외. Step 2-6에서 실측정으로 교체하며 제거)
- `server/tests/test_analyze.py` + `conftest.py` — pytest 5건

**검증 결과**
- 직접 확인: 사용자가 브라우저 `/docs`(Swagger)로 통과 확인
- 자동 테스트: 5/5 통과 (simple/precise 규격, 422 검증 2건, /health)

**관련 커밋**: `e2f6acf`(개발), `07141b4`(테스트)

## Phase 1 수정 반영 (2026-07-14, Gate 통과 후)

**무엇을**: 셔터 타이머(끔/3/5/10초) 추가 — 카운트다운 오버레이, 만료 시 자동 촬영,
재탭/전환/이탈 시 취소, 선택값 App 보관(재촬영 후 유지). 커밋 e2cd036.

**왜**: 사용자 요청. 기준물을 몸에 대고 약 2m 거리에서 전신을 찍어야 하는 앱 특성상,
폰을 거치하고 타이머로 촬영하는 시나리오가 실사용에 필수적.

**재검증 결과 (전부 통과)**:
- 자동: 빌드+타입 체크, 타이머 E2E 9/9
- 회귀: 전체 플로우 9/9, 카메라 전환 5/5 (기존 기능 영향 없음)
- 수동: 사용자가 실제 폰에서 타이머 촬영 확인 (터널 경유)

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
6. **셔터 타이머**(끔/3/5/10초)는 `onShutter` 호출 시점만 늦출 뿐 캡처 파이프라인과
   무관. 카운트다운 중 셔터 재탭·카메라 전환·화면 이탈 시 자동 취소. 타이머
   선택값은 facing처럼 App 보관(재촬영 후 유지).

### 폰 수동 검증 방법 (Phase 2에서도 동일하게 사용)
1. `npm run dev` (포트 5173)
2. `& "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" tunnel --url http://localhost:5173`
3. 출력된 `https://*.trycloudflare.com` URL을 폰에서 접속 (HTTPS라 카메라 허용됨)
4. ⚠️ Phase 2부터는 백엔드에 API 키가 생기므로 터널은 검증 시간에만 짧게 열 것

### 검증 자산 (스크래치패드에 있던 것 — 필요 시 재작성 가능)
- stub 규격 검사(`check-stub.mjs`), 전체 플로우 스모크(`e2e-smoke.mjs`),
  카메라 전환 스모크(`e2e-flip.mjs`) — puppeteer-core + Chrome 가짜 카메라 방식.
- CLAUDE.md 13-4에 따라 Phase 2부터는 `server/tests/`에 정식 보관할 것.

## Phase 2 남은 계획 (Step 분해는 2026-07-14 사용자 승인됨)

- ~~2-1 FastAPI 스캐폴딩~~ ✅ → **2-2 카드 검출(다음)** → 2-3 ArUco → 2-4 호모그래피
  → 2-5 Claude Vision(이때부터 API 키 필요, `server/.env`) → 2-6 cm 산출·타원 근사
  → 2-7 다중 프레임·신뢰도 → 2-8 프론트 연결
- **사전 준비물 (사용자에게 요청할 것)**: 카드 포함 전신 사진 + 줄자 실측 정답값,
  **최소 3명분** (`server/tests/fixtures/`에 보관). 2-2 개발에는 우선 1장이면 시작 가능.
- Phase 2 Gate: 자동 7항목 + 수동 실측 비교(길이 ±3cm, 둘레 ±5cm, 3명 전원) + 통합
  + 보안(프론트 번들 API 키 grep)

## 주의사항 / 배운 것 (Phase 2에서)

1. **Windows에서 requirements.txt 주석은 영어(ASCII)로**: 한글 주석을 넣으면 pip가
   시스템 인코딩(cp949)으로 읽다가 UnicodeDecodeError로 설치 실패. 실제로 겪음.
2. **서버 실행 명령** (venv는 `server/venv`, gitignore됨 — 새 환경에서는
   `python -m venv venv` 후 `pip install -r requirements.txt`로 재생성):
   ```powershell
   cd C:\claude_code\FITME\server
   .\venv\Scripts\uvicorn.exe main:app --reload --port 8000
   # 확인: http://localhost:8000/docs (Swagger) 또는 /health
   ```
3. **테스트 실행 명령**:
   ```powershell
   cd C:\claude_code\FITME\server
   .\venv\Scripts\python.exe -m pytest tests/ -v
   ```
4. PowerShell 5.1 콘솔에서 API 응답의 한글이 깨져 보이는 것은 표시 문제
   (실제 바이트는 UTF-8 정상). Swagger나 프론트에서는 정상.

## 주의사항 / 배운 것 (Phase 1 수정에서)

1. **자동 E2E가 진짜 버그를 잡는다**: 가짜 카메라 장치 + 자동 주행 테스트가
   "카메라 전환 중 셔터 → 빈 프레임 캡처" 레이스를 실기기 테스트 전에 발견했다.
   Phase 2부터는 검증 스크립트를 `server/tests/`에 정식 보관하며 누적할 것.
2. **비동기 하드웨어(스트림)와 얽힌 버튼은 준비 상태 게이트가 필수**: 스트림
   `loadeddata` 전 셔터 비활성 패턴. 타이머도 같은 게이트 위에서 동작해 안전.
   Phase 2에서 API 호출 버튼(분석 중 중복 탭 등)에도 같은 패턴을 적용할 것.
3. **화면 전환을 넘어 유지돼야 하는 사용자 선택은 상위(App)에 보관**: 컴포넌트
   리마운트로 facing/타이머가 초기화되는 문제를 두 번 겪음. 새 선택 상태를 추가할
   때는 "재촬영/뒤로가기 후에도 유지돼야 하나?"를 먼저 묻기.
4. **데이터와 UI 표현의 분리**: 전면 카메라 거울상은 미리보기(CSS)만. 캡처 데이터는
   항상 원본 — ArUco는 좌우 반전 시 검출 불가이므로 이 원칙은 Phase 2의 전제 조건.
5. **Gate 후 수정도 수동(실기기) 재검증까지**: 데스크톱 자동 테스트만으로 끝내지
   않고 폰 확인 후에 기록을 갱신해야 Gate 기록의 신뢰가 유지된다 (규칙 1·3).

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
| 추가 | 셔터 타이머(끔/3/5/10초, 카운트다운·취소) — 2026-07-14, Gate 후 사용자 요청 | e2cd036 |
