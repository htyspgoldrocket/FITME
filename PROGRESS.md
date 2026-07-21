# PROGRESS.md — FITME 진행 상황

> 세션이 끊겨도 이 파일 + CLAUDE.md + `src/types/index.ts`만 읽으면 이어서 개발할 수 있다.

## 현재 위치

- **Phase 1: ✅ 완료 + 수정 재검증 완료** (2026-07-14, Gate 통과, 태그 `phase-1-complete`)
  - Gate 리포트(수정 이력 포함): `docs/gate-reports/phase-1-gate.md`
- **Phase 2: 🔄 진행 중 — Step 2-6 개발 완료, 실측 0/7로 Gate 보류** (2026-07-16)
  - 2-6 코드(랜드마크→8치수+타원 근사+범위 검사)는 완성·커밋(`c4b25aa`).
    실측 비교 결과 전 항목 기준 미달 → 원인 3가지 규명(배운 것 24번), 대응
    계획 확정(25번). **2-6 실측 재검증은 2-7b에서 수행.**
- **Step 2-7 ✅ 완료 (2026-07-16, 13표본 검증)** — 커밋 `22bfd52`
  - **기본 프레임 수 7 확정**: 편차 ≤2cm 항목 수 3프레임 4/8 → 5프레임 6/8 →
    **7프레임 7/8** (13표본 롤링). MAD 이상치 제거는 효과 없음(허리 산포는
    이상치가 아니라 넓은 분포)
  - **허리 3.5cm 잔존 — 프레임 수와 무관(3→5→7 모두 3.5)**: "natural waist 위치"
    정의 모호가 원인. **옵션 A(허리 정의 변경) 보류** — 편차 원인이 헐렁한 옷일
    가능성이 있어 밀착 옷 데이터에서 재확인 후 결정
  - **person01 데이터 역할 재정의**: 보정 기준 아님 — "파이프라인 확인 +
    나쁜 조건 엣지 케이스"용 (계수 역산은 밀착 옷 기준 데이터 확보 후)
- **Step 2-7c ✅ 완료 (2026-07-16)** — /check-photo + 대칭성 검사, 검증 10/10,
  커밋 `403a669`
- **v2 재검증 완료 (2026-07-16, 밀착 옷 재촬영)** — 결과는 배운 것 28번.
  요약: 절대 오차 대폭 개선(키 -0.8cm, 다리안쪽 -27.4→-14.7cm — 반바지 가설
  확인). 그러나 마커 42px(v1 59.9px)로 편차는 악화(Gate 4/8). **허리 2.2cm로
  옵션 A '진행 필요' 판정 — 단 마커 크기 교란 변수 있음, 사용자 결정 대기**
- **v3 재검증 완료 (2026-07-16)** — 배운 것 29번. 결론: **옵션 A(허리 정의
  변경) 진행 확정** (3장 전부 허리 >2cm — 옷·마커·거리 무관 일관 초과),
  **호모그래피 외삽 폐기 필요 실증** (v3 키 +70.8cm 폭주), **v2가 기하학적
  최적 기준 데이터** (스칼라 키 오차 -1.0cm)
- **Step 2-7b ✅ 완료 (2026-07-16)** — 키 캘리브레이션(A안 확정) + BMI 둘레 보정
  + 계수 역산(v2 기준). 상세는 아래 완료 이력 + 배운 것 30번
- **옵션 A 검증 완료 (2026-07-16, 신규 API 39회) — ❌ 기준 미달, 가설 기각**
  — 허리 정의를 기하 중간점으로 바꿔도 편차 >2cm 잔존 (배운 것 31번의 비교표).
  원인 재규명: 정의 모호가 아니라 **실루엣 가장자리 x 추정 노이즈 + 배치 내
  드리프트**. 프롬프트는 신정의로 변경된 상태, 구정의 캐시 39런은
  `fixtures/archive_predefA/` 보관
- **옵션 B 채택 (2026-07-16 사용자 결정)** — 둘레 3종의 반복 편차를 알려진
  한계로 문서화(CLAUDE.md 12장), Gate 일관성 기준은 **길이 항목+어깨**로 조정
  (13-2·9장 갱신). 허리 프롬프트는 신정의(기하 중간점) 확정, 허리 깊이 계수
  0.7273으로 재역산 완료 — 상세는 배운 것 32번
- **Step 2-8 🔄 진행 중 (2026-07-17 시작)** — 6개 sub-step 분해안 사용자 승인:
  a) 백엔드 /analyze 실제 배선 → b) 키·몸무게 입력 UI → c) 층위 1·2 →
  d) 층위 3(폴링+자동 촬영) → e) 7프레임 캡처+analyzeBody 연결 → f) 층위 4+통합
  - **층위 3 클라이언트 방식 확정(사용자 결정)**: **서버 폴링** (/check-photo
    재사용, OpenCV.js는 8MB WASM+로직 이중화라 기각)
  - **2-8a ✅ 완료**: /analyze를 실제 파이프라인(검출→척도→랜드마크→2-7 통계→
    2-7b 캘리브레이션)에 배선. 신규 계약 `AnalyzeResponse`(ok/reference/
    measurements?/warnings/stats?/error?) — 미검출·추출 실패를 가짜 숫자 없이
    전달(규칙 1). CLAUDE.md 6장·types/index.ts·schemas.py 동기화.
    MAX_FRAMES=9 비용 상한. 테스트 11건 재작성(API 0회 — 합성 마커 + 추출
    mock), 전체 53/53 + tsc 통과
  - **2-8b ✅ 완료 (2026-07-17)**: 키·몸무게 입력 UI — `ProfileInput.tsx` 신규,
    화면 흐름 모드 선택→**신체 정보**→카메라로 확장. profile은 App 보관
    (재촬영·뒤로가기 유지 — Phase 1 배운 것 3번). 입력 하드 한계(키 100~250,
    몸무게 20~300)만 UI가 차단, 정밀 오타 검증은 r 판정(2-7b) 몫.
    검증: tsc+build 통과, E2E 스모크 9/9 (`tests/e2e-profile-flow.mjs` —
    puppeteer-core 정식 자산화, 13-4). analyzeBody에 profile 전달은 2-8e에서
  - **2-8c ✅ 완료 (2026-07-17)**: 층위 1·2 — 촬영 전 정적 안내 오버레이
    (5항목, 세션 첫 진입 자동 표시 + ❓ 재열람, guideSeen은 App 보관) +
    정중앙 실루엣 SVG 가이드(기존 점선 프레임 교체) + 자이로 2축 분리 표시
    (좌우 수평·앞뒤 기울기 — camera.ts 데이터 기존 그대로, 표시만 확장.
    VERTICAL_TOLERANCE_DEG export 1줄만 변경). 검증: tsc+build, E2E 14/14
    (안내 표시/닫힘/재진입 생략/재열람 포함), 스크린샷 육안 확인
  - **2-8d ✅ 완료 (2026-07-17)**: 층위 3 — /check-photo 서버 폴링(1.2초 직렬,
    프레임은 실캡처와 동일한 1080px 규격 — 임계값 유효성) + 연속 2회 ready 시
    3초 자동 카운트다운(조건 깨지면 auto만 취소, 수동 타이머 보호 —
    countdownSource 구분. 사용자 취소 시 8초 재발동 억제). 판정 배너 +
    자동 촬영 토글(App 보관, 기본 ON). 서버 다운 시 수동 촬영 경로 무손상.
    Vite 프록시 /api→127.0.0.1:8000 신설(폰 터널 1개로 백엔드 커버).
    검증: E2E 신규 7/7(음성=초록 캠, 양성=마커 y4m로 자동 촬영→미리보기까지
    실백엔드 통짜) + 회귀 14/14. y4m 생성기 tests/gen_fake_camera.py
  - **2-8e ✅ 완료 (2026-07-17)**: 7프레임 캡처(`captureFramesFromVideo`,
    350ms×7≈2.1초, 캡처 중 셔터 잠금+정지 안내+폴링 일시정지) +
    `analyzeBody` stub→실제 /analyze(AnalyzeResponse, 타임아웃 180초 —
    프레임당 AI 1회라 장시간) + 측정 결과 화면 `MeasureResult.tsx`
    (로딩/네트워크 오류·재시도/ok:false 재촬영/8항목 테이블+신뢰도 배지+
    경고 접기). Phase 1 stub 3종 중 analyzeBody 교체 완료.
    검증: E2E 신규 11/11 — 가짜 백엔드(tests/e2e_fake_backend.py, 랜드마크만
    합성 패치·AI 0회)로 frames=7·profile 전송, 백엔드 다운→오류→재시도→
    성공 테이블(키 172.0 정확 복원)까지 통짜. 회귀 14/14+7/7, 스크린샷 확인.
    suspect 강등(마커-키 척도 불일치) 실동작 확인
  - **2-8f ✅ 완료 (2026-07-17) → Step 2-8 전체 완료**: 층위 4 — 결과 화면
    재촬영 권고 배너(사유: 좌우 비대칭 / 척도 suspect / 신뢰도 low ≥3개 —
    경고 접두어("좌우")·stats.scale.agreementLevel이 프론트-백엔드 계약) +
    권고 시 주의 사항 자동 펼침. ok:false 재촬영·경고 표시는 2-8e에 이미 구현.
    통합 점검: e2e-analyze 17/17(비대칭 백엔드 시나리오 포함, FITME_E2E_ASYM=1)
    + 회귀 14/14·7/7 + pytest 53/53 + dist 번들 API 키 흔적 grep 청정
- **Phase 2 Gate 상태 (2026-07-17): 자동 검증 통과 / 수동 검증 보류 — 미완**
  - **자동 검증 재확인 전부 통과 (2026-07-17)**: pytest 53/53, tsc+build,
    dist 번들 API 키 grep 청정, E2E 14/14(프로필·가이드)·17/17(분석 플로우)·
    7/7(자동 촬영, 실백엔드) — 2-8f 결과 재현. 로컬 자산 11종·git 동기화도
    보존 확인
  - **수동 검증(정밀 3회+간편 1회 일관성 확인)은 사용자 사정으로 보류** —
    사용자 결정(2026-07-17)으로 완료를 가정하고 Phase 3 진입. **Gate는
    통과 처리하지 않고 "미완"으로 정직 기록** (규칙 3의 예외는 사용자 명시
    지시에 근거). 수동 검증은 추후 수행 — 절차는 아래 기록 그대로 유효하며,
    통과 시점에 qa Gate 리포트 작성
- **Phase 3 🔄 진행 중 (2026-07-17 시작)** — 4개 Step 분해안 사용자 승인
  (3-1 URL 입력 UI / 3-2 스크래핑 / 3-3 정규화 / 3-4 실연동+SQLite).
  **3-2 첫 지원 쇼핑몰 = 무신사 (사용자 결정)**
  - **3-1 ✅ 완료 (2026-07-17)**: 의류 URL 입력 UI — `ClothingUrlInput.tsx`
    신규(http/https 검증, 폼 스타일은 profile__* 재사용), 화면 흐름
    측정 결과→**의류 URL**→의류 정보(stub, 3-2~3-4에서 구현 명시)로 확장.
    측정 결과 화면에 "의류 사이즈 비교" 버튼 추가 + **분석 캐시를 App으로
    승격**(MeasureResult cached/onLoaded — 의류 화면에서 뒤로 와도 재분석
    AI 7회 없음, 새 캡처 시 무효화). clothingUrl은 App 보관(재진입 유지).
    검증: tsc+build, E2E 신규 11/11(`tests/e2e-clothing-url.mjs` — 검증·전환·
    캐시·값 유지), 회귀 14/14·17/17·7/7 전부 통과
  - **3-2 ✅ 완료 (2026-07-17)**: 무신사 사이즈 테이블 추출 —
    `services/clothing_scrape.py` 신규. **DOM 파싱 대신 상품 페이지가 스스로
    호출하는 공개 JSON API 2개 사용** (goods-detail.musinsa.com/api2/goods/{no}
    → 브랜드·상품명·카테고리, …/actual-size → 사이즈별 실측 cm — 실상품 탐사로
    확인. UI 리뉴얼에 강건, 요청도 상품당 2회로 최소). Playwright request
    컨텍스트 + 일반 브라우저 UA. '가슴단면' 등 **단면 값은 원문 그대로 보존**
    — 둘레 환산·ClothingSpec 정규화는 3-3 몫. requirements.txt에
    playwright>=1.41.0,<2.0 추가(계획된 Phase 3 몫) + chromium 설치.
    검증: pytest 16건 신규(오프라인 — URL 판정·파싱·에러 경로) 전체 69/69,
    라이브 CLI 4종(아우터 5사이즈·바지 4사이즈 추출 성공 / 404 not-found /
    타 쇼핑몰 unsupported — 한국어 안내 확인)
  - **3-3 ✅ 완료 (2026-07-17)**: 표기 정규화 — `services/clothing_normalize.py`
    + `data/size_conversion.json`(부위명→필드 매핑·단면×2·카테고리 키워드·
    호칭 근사표가 단일 출처). **ClothingSize/ClothingSpec 계약 확장**(규칙 6:
    CLAUDE.md 6장→types/index.ts→schemas.py 동기화): 부위 필드 전부 선택
    (의류 종류마다 제공 부위가 다름 — 없는 부위를 0으로 채우지 않음, 규칙 1)
    + shoulder/sleeve/length/thigh/rise/hem 추가(어깨는 측정 신뢰 최상 항목이라
    Phase 4 핏에 중요) + estimated(호칭 근사 표시)/needsUserInput/warnings.
    호칭 폴백: 상의 80~120=가슴 호칭, 하의 24~44=인치, 60~120=cm 호칭,
    S~3XL 근사표, Free류=변환 불가→needsUserInput (실측 있으면 폴백 미사용 —
    무신사는 실측 제공이라 사실상 타 쇼핑몰 대비용). 검증: pytest 14건 신규
    (Gate 4표기 "95"/"L"/"38"/"Free" 포함, Pydantic 계약 통과 확인) 전체
    83/83 + tsc, 라이브 통합 2종(아우터 chest 105~135 / 바지 waist 74~86 —
    상식 범위)
  - **3-4a ✅ 완료 (2026-07-17)**: 백엔드 POST /clothing —
    `routes/clothing.py`(def 엔드포인트 — Playwright sync, 배운 것 4번) +
    `services/clothing_store.py`(SQLite 캐시, 키 musinsa:{goodsNo}, TTL 24h,
    DB는 gitignore) + **신규 계약 `ClothingResponse`**(ok/spec?/cached?/error?/
    code? — 실패를 크래시 없이 한국어 안내로 전달, AnalyzeResponse 방식.
    CLAUDE.md 6장→types/index.ts→schemas.py 동기화). 검증: pytest 6건 신규
    (오프라인 — 성공+캐시 적중·실패 미캐시·unsupported·TTL 만료) 전체 89/89
    + tsc, 라이브 3종(실상품 5사이즈 12.3초→캐시 0초 / 타 쇼핑몰 unsupported /
    없는 상품 not-found)
  - **3-4b ✅ 완료 (2026-07-17) → Step 3-4 전체 완료**: 프론트 —
    `fetchClothingSpec` stub→실제 POST /clothing(ClothingResponse, 타임아웃
    60초 — 첫 조회는 Playwright 기동 십수 초) + `ClothingSpecView.tsx` 신규
    (로딩/네트워크 오류·재시도/ok:false 한국어 안내/사이즈 표 — 값 있는 부위
    컬럼만 동적 표시, ≈=호칭 근사, needsUserInput·warnings 표시. 핏 진행
    버튼은 4-4 몫이라 미구현 — 규칙 4) + 조회 캐시 App 승격(URL 변경 시
    무효화, **ok=false는 캐시 안 함** — 재진입 재조회로 복구 기회).
    Phase 1 stub 3종 중 calculateFit만 남음(4-4).
    검증: tsc+build, E2E 신규 13/13(`tests/e2e-clothing-spec.mjs` — 표 표시·
    단면×2 환산·컬럼 동적·App 캐시·URL 변경 재조회·unsupported 안내),
    회귀 11/11(clothing-url — stub 검증을 실화면으로 갱신)·17/17·14/14·
    7/7(실백엔드) + pytest 89/89
- **Phase 2 수동 검증 재보류 (2026-07-18 사용자 결정)**: 통과를 가정하고
  진행, 검증은 추후 수행 — 이전 보류(2026-07-17)와 동일한 방식으로 정직 기록.
  Gate는 계속 "미완". 절차(위 "Gate 수동 검증 절차"·통합 체크리스트 A파트)는
  그대로 유효. **추후 문제 발생 시 확인 지점**: Phase 4 수동 검증(아는 옷
  대조)에서 추천이 실제와 어긋나면 가장 먼저 Phase 2 반복 일관성부터 의심하고
  이 검증을 수행할 것
- **Phase 3 수동 검증 ✅ 통과 (2026-07-18)** — 무신사 3종(카테고리 달리,
  조정 기준) 실서버 추출 + 사용자 대조 "정확히 일치" 확인:
  ① 상의 996177 무신사 스탠다드 반팔 티셔츠 6사이즈 ② 하의 6719352 토피
  데님 4사이즈 ③ 아우터 6516683 아크테릭스 5사이즈. 전부 ok=true·카테고리
  자동 판정 정확·경고 0건·상식 범위·×2 환산 일치. 캐시 실동작(아우터
  24h 내 재조회 0.2초, 무신사 접속 0)

### ✅ Phase 3 Gate 리포트 (2026-07-18, qa)

- **자동 검증: 통과** — pytest 전체 89/89 (2026-07-18 재실행. Gate 항목 포함:
  테스트 URL→ClothingSpec 구조 / "95"·"L"·"Free"·"38" 정규화 / needsUserInput
  플래그 / 스크래핑 실패 시 명확한 에러 — test_clothing_scrape 16 +
  test_clothing_normalize 14 + test_clothing_route 6)
- **수동 검증: 통과** — 위 무신사 3종 추출·대조 (사용자 확인 2026-07-18)
- **통합 검증: 통과 (데스크톱) / 실기기분 이월** — 촬영→측정→의류 URL→스펙
  표시 전체 흐름은 E2E 17/17(분석)·13/13(의류 스펙, 실정규화·실캐시 경유)로
  데스크톱 수준 통과. 실기기 전체 흐름은 측정이 Phase 2 수동 검증(보류)과
  결합돼 있어 함께 이월 (정직 기록 — 규칙 1)
- **미해결 이슈**: ① Phase 2 수동 검증 보류(사용자 결정 — 절차 보존, Phase 4
  아는 옷 대조 어긋날 시 최우선 수행) ② 실기기 통합 흐름 확인 이월(①과 결합)
  ③ 무신사 비공식 API 의존(12장 알려진 한계 — 오프라인 테스트가 파손 감지)
- **다음 Phase 진입 가능 여부: 가능** — 사용자 승인 대기

- **Phase 4 🔄 진행 중 (2026-07-18 시작)** — 4개 Step 분해안 사용자 승인
  (4-1 핏 계산 / 4-2 사이즈 추천 / 4-3 자연어 피드백 / 4-4 실연동).
  Phase 4 수동 검증(아는 옷 대조)이 Phase 2 편향 일정성 가정의 실질 검증
  - **4-1 ✅ 완료 (2026-07-18)**: 치수 비교 로직 — `services/fit.py`
    `score_parts()`: 몸 8항목 ↔ 옷 선택적 부위 중 **같은 정의 쌍만** 비교
    (둘레↔둘레 3쌍: 가슴·허리·엉덩이 — 옷 값은 3-3 단면×2 환산 둘레라 동일
    기준 / 직선↔직선 1쌍: 어깨. 소매↔팔길이·총장↔다리안쪽은 정의 불일치로
    판정 제외 — 활용 여부는 4-2 이후 결정). 옷에 없는 부위는 결과에서 제외
    (추정치 금지 — 규칙 1). **계약 확장**: FitScore.confidence?(측정 신뢰도
    부위별 전파 — CLAUDE.md 6장→types→schemas 동기화). tight/good/loose
    경계는 EASE_RANGES 상수(⚠️ 전부 추정 — 코드 주석 명시, Phase 4 수동
    검증에서 교정, 신축성·카테고리 세분화는 4-2).
    검증: pytest 14건 신규(논리 역전 0건 스윕·경계 포함/제외·부위 제외·신뢰도
    전파·계약) 전체 103/103 + tsc, **실데이터**(person01 v2 실측 + 무신사
    3종): 아우터 S/M 어깨·가슴 good(상식 부합), 논리 역전 없음.
    관찰 2건 기록: ① 릴렉스 핏 티셔츠 어깨 전 사이즈 loose = 의도된 동작
    (드롭숄더 옷이 실제로 루즈 — 카테고리·핏 유형 반영은 4-2 후보)
    ② 하의 허리 -14~-26cm tight 일괄 판정 — 몸 허리(배꼽/중간점 레벨) vs
    바지 허리밴드(착용 레벨) **측정 위치 정의 차이** 영향 포함 추정.
    4-2 사이즈 추천 설계 시 하의 허리 처리(레벨 보정 또는 hip 가중) 결정 필요
  - **4-2 ✅ 완료 (2026-07-19)**: 사이즈 추천 — fit.py `recommend_size()`.
    설계안(아래 기록)대로 구현, **하의 허리는 A안 확정(사용자 결정
    2026-07-19)**: 전 사이즈 하한 미달 시 가중 부족량 최소 사이즈 +
    insufficient + 한국어 경고 (근거 없는 보정 없음 — 규칙 1).
    신축성 완화는 추천 필터에만 적용(FitScore.status는 4-1 원 기준 유지),
    무신사 미제공이라 기본 완화 0. 계약 변경 없음(반환은 dict —
    FitResult 조립·API 배선은 4-4).
    검증: pytest 11건 신규(이상 여유 선택·동점·tight 탈락·loose 비탈락·
    A안 경로·신축성 완화(둘레만)·추천 불가·estimated 경고·하의 hip 가중)
    전체 114/114. **실데이터 3종 = 설계 손계산과 정확히 일치**:
    티셔츠 M(1.35) / 아크테릭스 M(0.0) / 배럴 데님 XL+insufficient+경고.
    ⚠️ 미결(4-3·수동 검증으로 이월): 하의 허리 A안의 실제 체감 적합성은
    Phase 4 수동 검증(아는 바지 대조)이 판정
  - **4-3 ✅ 완료 (2026-07-19)**: 자연어 핏 피드백 — `services/fit_feedback.py`
    신규. `generate_feedback()`: 계산된 사실만 JSON으로 프롬프트에 전달
    (지어내기 금지 명시) → {"recommendation": …} 회수. **수치 모순 방어 3중**:
    ① 사실 전용 프롬프트 ② JSON 방어(2-5 패턴: 코드펜스 제거→{} 추출→
    1회만 재요청) ③ 추천 라벨 미포함 응답 거부. 실패·API 오류 시 **사실
    기반 템플릿 폴백**(같은 facts에서 기계 조립 — 가짜 정보 아님,
    source="claude"/"template"로 경로 구분). 추천 불가(None)면 API 미호출
    (비용 0). 모델 claude-opus-4-8 (FITME_FEEDBACK_MODEL 교체 가능).
    검증: pytest 12건 신규(facts 추출·템플릿 문구·코드펜스·재요청 1회 제한·
    라벨 검증·예외 폴백·API 미호출 경로 — 전부 mock, API 0회) 전체 126/126.
    **실호출 2회**(아우터 M 정상 / 데님 XL insufficient): 둘 다 source=claude,
    생성문이 부위별 판정·cm·신뢰도 low·A안 경고와 전부 일치 (모순 0건)
  - **4-4a ✅ 완료 (2026-07-19)**: 백엔드 POST /fit — `routes/fit.py`
    (def 엔드포인트 — 피드백이 동기 HTTP): recommend_size(4-2 A안) →
    추천 사이즈 FitScore(4-1) → generate_feedback(4-3, 폴백 내장이라 요청은
    실패하지 않음) → FitResult 조립. **신규 계약 FitRequest/FitResponse**
    (ok/result?/warnings/error? — 추천 불가를 가짜 사이즈 없이 전달,
    CLAUDE.md 6장→types→schemas 동기화). 검증: pytest 5건 신규(FitResult
    산출·신뢰도 low 반영(Gate 항목)·insufficient 경고 전달·추천 불가
    ok=false·422 — feedback mock, API 0회) 전체 131/131 + tsc,
    실서버 통짜 1회(실측+무신사 아우터 → M, 추천문 수치 일치, API 1회)
  - **4-4b ✅ 완료 (2026-07-19) → Step 4-4·Phase 4 개발 완료**: 프론트 —
    `calculateFit` stub→실제 POST /fit(FitResponse, 타임아웃 60초.
    **Phase 1 stub 3종 전부 소진**) + `FitResultView.tsx` 신규(로딩/오류·
    재시도/ok:false 사유/추천 사이즈 강조·부위별 판정 배지(타이트·잘 맞음·
    여유)+여유cm+신뢰도 배지·추천문·경고 — Phase 5 진행 버튼은 미구현,
    규칙 4) + 의류 스펙 화면에 "핏 분석 보기" 버튼(측정 성공 시에만 —
    App의 canFit) + 핏 캐시 App 승격(새 캡처·URL 변경·스펙 재로드 시
    무효화, ok=false 미캐시). 가짜 백엔드에 피드백 템플릿 경로 강제 추가
    (추천 로직·라우트는 실코드, AI 0회).
    검증: tsc+build, E2E 신규 10/10(`tests/e2e-fit.mjs` — 버튼 노출·추천
    사이즈·판정 배지·추천문-사이즈 일치·재진입 무재요청·전체 흐름 복귀),
    회귀 13/13·11/11·17/17, pytest 131/131, dist 번들 API 키 grep 청정
- **Phase 4 Gate 수동 검증 1차 ❌ 미통과 (2026-07-19, 아는 옷 3종 대조)** —
  규칙 3에 따라 Phase 4에 머물러 교정 후 재검증. 결과·원인 (정직 기록):
  ① **오버핏 티셔츠(4219389)**: 앱 M vs 실제 L — 1사이즈 불일치. 원인:
  이상 여유(+11)·EASE_RANGES가 레귤러 핏 추정 기준인데 오버핏 옷은 의도
  여유가 큼(M +16/L +18 둘 다 good 구간 — 상수가 작은 쪽을 고름). 상품명에
  "오버핏" 명시돼 있어 감지 가능했음
  ② **유벤투스 트랙 팬츠(4414673)**: 앱 2XL+부족 경고 vs 실제 훨씬 작은
  사이즈 — 큰 불일치. **주 원인은 허리 레벨이 아니라 신축성(고무줄 허리)**:
  무신사 실측 waist 68~84는 밴드 이완 상태 값이라 몸 허리(100)보다 작은 게
  정상인데, 무신사가 신축 정보를 안 줘 A안이 전 사이즈 tight로 처리.
  상품 종류("트랙팬츠"·카테고리)로 신축 허리 감지 가능했음
  ③ **노스페이스 3L 자켓(6113011)**: 대조 불가 — API 원응답 조사 결과
  goods는 SUCCESS인데 **actual-size가 SUCCESS + data:null** (무신사에 실측
  데이터 미등록 상품). 앱의 추출 거부는 옳음(규칙 1). 안내 문구만 부정확
  ("주소를 확인해 주세요" → "실측 미제공 상품" 안내가 정확)
  **공통 시사점**: 몸 치수는 줄자 실측을 썼으므로 이번 불일치는 측정(Phase 2)
  이 아니라 **핏 로직의 추정 상수 + 의류 메타데이터(핏 유형·신축) 미활용**
  문제로 분리 확인됨. 교정 후보는 사용자 협의 후 결정
- **Phase 4 교정 ✅ 구현 완료 (2026-07-19, 사용자 승인 3건)** + **방침 확정
  (사용자 결정)**: 핏 상수·키워드는 추정으로 두고 **앱 완성 우선** — 실측
  불일치는 다수 데이터 확보 후 일괄 검증·정교화 (모든 불일치를 즉시 잡으려
  하지 않음). 구현:
  (a) fit.py `detect_garment_traits()` — 상품명 키워드로 오버핏 감지 →
  이상 여유 상향(OVERSIZED_IDEAL_BONUS, 실착 L 역산 수준 추정) / 신축 허리
  감지(트랙팬츠·조거 등, 하의 전용) → 허리를 비교·표시에서 제외 + 밴딩 경고
  (b) clothing_scrape.py `extract_size_data()` — actual-size SUCCESS+data:null
  = "실측 사이즈 미제공 상품" 정확 안내 (6113011 실증)
  검증: pytest 7건 신규(오버핏→L·키워드 없으면 M 유지·밴딩 제외·상의 무시·
  봉투 3종) 전체 138/138, e2e-fit 회귀 10/10.
  **재검증 결과**: 티셔츠 **L 추천 — 실착과 일치 ✓** / 트랙팬츠 **S 추천**
  (2XL→S, insufficient 해소, 밴딩 경고 — 실착 대조 사용자 판정 대기) /
  자켓 정확 안내 ✓
- **수동 검증 판정 현황 (2026-07-19)**: ① 오버핏 티셔츠 — 앱 L = 실착 L
  **일치 ✓** ② 트랙팬츠 — 앱 S vs **실착 L 불일치** (2사이즈. 원인: 밴딩
  하의는 스포티/릴렉스 핏이라 엉덩이 이상 여유도 커야 하는데 기본값 +8 사용
  — S/M hip 동점→S. 실착 L은 hip +12) ③ 대체 자켓 5311114(블루종) —
  앱 M(95) 추천, 실착 판정 대기
- **트랙팬츠 A안 교정 ✅ (2026-07-19 사용자 승인)**: 밴딩 하의 엉덩이 이상
  여유 +5(→13, 실착 L 역산 추정 — ELASTIC_HIP_IDEAL_BONUS) → 재검증 **L =
  실착 일치 ✓**. pytest 139/139
- **수동 검증 최종 집계 (아는 옷 3종)**: ① 오버핏 티셔츠 **일치**(L) ②
  트랙팬츠 **일치**(L, 교정 후) ③ 블루종 자켓(5311114) **불일치** — 앱 M(95)
  vs 실착 L(100). 원인 분석: 이 자켓은 재단이 극단적으로 루즈(최소 M도
  가슴 +28·어깨 +12.5로 전 사이즈 전 부위 loose)해 실측 기준으론 M도 충분
  — 실착 L 선택은 ㉠호칭 관습(가슴 100 → "100" 선택) ㉡소매·총장(몸 팔 58
  vs M 소매 55 — 소매는 정의 불일치로 비교 제외 항목) 영향으로 추정.
  **방침(2026-07-19)에 따라 추가 역산 교정 없이 알려진 한계로 기록**:
  극단 루즈핏 아우터 + 호칭 관습은 현 실측 기반 로직의 한계 — 다수 데이터
  확보 시 호칭 매칭·소매/총장 반영 검토
### ✅ Phase 4 Gate 리포트 (2026-07-19, qa — 사용자 승인 대기)

- **자동 검증: 통과** — pytest 139/139 (FitResult 산출 / 논리 역전 0건 스윕 /
  여유·부족 cm 표시 / 신뢰도 low 반영)
- **수동 검증: 부분 통과 (2/3 일치, 정직 보고)** — 티셔츠 L=L ✓ /
  트랙팬츠 L=L ✓(교정 2건 후) / 블루종 자켓 M(95) vs 실착 L(100) ✗
  (원인: 극단 루즈핏 재단 + 호칭 관습·소매/총장 미반영 — 방침에 따라 알려진
  한계로 기록, 추가 역산 안 함). 자연어 피드백-수치 모순 5회 생성 전부 0건
- **통합 검증: 통과(데스크톱)** — 촬영→측정→의류→핏 E2E 10/10 + 회귀.
  실기기 흐름은 Phase 2 수동 검증 보류와 결합 이월
- **미해결 이슈**: ① 극단 루즈핏 아우터·호칭 관습(위) ② 핏 상수·키워드가
  표본 1~2벌 역산 추정 ③ Phase 2 수동 검증 보류 지속
- **다음 Phase 진입 가능 여부**: 규칙 3 원문("전부 일치") 미달 —
  **조건부 통과 (2026-07-19 사용자 승인 확정)**. 태그 phase-4-complete push됨

- **Phase 5 🔄 시작 (2026-07-19)** — 분해안: 5-1 엔진 단독 테스트 / 5-2
  백엔드 배선(+무신사 상품 이미지 URL 추출 확장) / 5-3 히트맵+프론트 /
  5-4 최종 통합 Gate.
  **합성 엔진 = A안(호스팅 API) 확정 (사용자 결정 2026-07-19)**. 근거:
  이 PC GPU가 Intel Iris Xe(내장)뿐 — NVIDIA 없음 확인 → 로컬 VTON(B안)
  불가. Replicate API 예정: 입력·출력 1시간 후 자동 삭제(공식 문서 확인),
  이미지당 과금, 사진 외부 전송 수용됨. 서비스화 시 개인정보 고지 필요
  (5-3에서 안내 문구). REPLICATE_API_TOKEN은 server/.env (로컬 전용)
- **합성 한계·대응 확정 (2026-07-20 사용자 결정: A+B)**: 이미지 기반 VTON은
  치수를 입력받지 못해 **사이즈별 핏 차이(팽팽함·눌림)를 그림으로 재현 불가**
  (IDM-VTON 포함 상용 공통 한계 — 항상 "적당히 맞는 모습"을 그림). 실핏 전달은
  Phase 4 수치 판정이 담당하고, 합성은 외관 확인용(A안 유지). 보완으로 **5-3
  히트맵에 부위별 수치 라벨 표기**(B — 예: "가슴 −4cm 부족")를 추가해 "그림≠
  실핏" 오해를 차단. C안(치수 조건형 합성)은 상용 API 부재 + GPU 부재로 기각
- **❌ 모델 결정 철회 — Replicate `cuuupid/idm-vton` 상업적 사용 불가 확인
  (2026-07-21, 사용자 지적 → 조사 확인)**: 원본 IDM-VTON은 `CC BY-NC-SA 4.0`
  라이선스로 상업적 사용이 명시적으로 금지("primarily intended for or
  directed toward commercial advantage or monetary compensation"). Replicate는
  호스팅 창구일 뿐 원본 라이선스가 그대로 적용됨. HuggingFace 원저자 페이지의
  "Commercial License" 토론(yisol/IDM-VTON#26)에서 여러 사용자가 상업 라이선스
  문의했으나 저자의 공식 승인·절차 확인 안 됨 — 구매 경로 자체가 불명확.
  동급 성능의 CatVTON도 동일 라이선스(상업 불가). FITME는 상업화 계획이 있으므로
  **이 모델로는 절대 진행 불가** — 07-19 기록한 "모델 확정"은 무효 처리.
  (참고: 자체 학습 모델을 만들어도 VITON-HD·DressCode 등 학습 데이터셋 라이선스가
  비상업 제한이라 우회 안 됨 — fashn.ai 개발자 가이드 확인)
- **✅ 모델 재확정: FASHN API (사용자 결정 2026-07-21)** — 상업적 사용 명시적
  허용(추가 라이선스 비용 없음, e커머스·마케팅 용도 포함). 가격 크레딧제
  최소 $7.50~, 회당 약 $0.075(Try-On Max) / 경량 버전 Try-On v1.6은 5~17초
  더 저렴한 편. 입력·출력 **72시간 후 자동 삭제**(Replicate 1시간보다 김 —
  안내 문구 톤 조정 필요, 5-3). 아키텍처는 A안(호스팅 API 호출) 그대로 유지 —
  provider만 교체. **정확한 요청/응답 스키마(model_image·product_image가
  URL 전용인지 base64도 되는지, 폴링 방식)는 미확인 — 5-1 재개 시 공식
  문서(docs.fashn.ai) 또는 실제 호출로 직접 확인 후 진행할 것 (규칙 1,
  짐작으로 코드 작성 금지)**
- **🚨 개발 단계 방침 확정 (2026-07-21 사용자 결정) — Replicate `cuuupid/idm-vton`로
  개발 재개, FASHN API 전환은 출시 전으로 이월**: 위 라이선스 문제(비상업
  CC BY-NC-SA 4.0)는 **해소되지 않았다.** 다만 지금 단계는 파이프라인 개발·
  테스트가 목적이고 실제 서비스 출시는 아니므로, **개발용으로는 Replicate
  cuuupid/idm-vton을 그대로 사용**하기로 사용자가 결정했다. FASHN API 조사
  내용(위 문단)은 출시 시 교체할 대안으로 계속 유효 — 폐기 아님.
  - **⚠️ 절대 잊지 말 것 (규칙 1 — 정직 기록)**: 지금 사용하는 VTON 모델은
    **상업적 사용이 금지된 라이선스**다. **이 앱을 실제로 서비스/판매하기
    전에 반드시 FASHN API(또는 다른 상업 허용 모델)로 교체해야 한다.**
    Phase 5 Gate·출시 체크리스트에 이 교체 작업을 필수 항목으로 반드시
    포함할 것 — 교체 없이 상업 출시하면 라이선스 위반. CLAUDE.md 12장에도
    동일 내용 기록(세션 시작 시 항상 재확인되도록).
  - 사용자 준비: replicate.com 가입 → API tokens에서 토큰(r8_…) 발급 →
    `server/.env`에 `REPLICATE_API_TOKEN=r8_…` 줄 추가 (+ Billing 카드 등록).
    키 로더는 utf-8-sig로 읽을 것 (메모장 BOM — 배운 것 18번 재사용)
- **Step 5-1 ✅ 완료 (2026-07-21)** — Replicate `cuuupid/idm-vton` 단독 테스트.
  `server/scripts/test_vton_standalone.py` 신규(재사용 가능한 1회성 테스트
  도구, generate_marker.py와 같은 성격). 입력: human_img=person01_v2_aruco.jpg
  (로컬 파일), garm_img=무신사 996177 티셔츠 이미지 URL(goods-detail API의
  thumbnailImageUrl, 베이스 도메인 `image.msscdn.net` 확인), category=
  "upper_body". **버전 미지정 `cuuupid/idm-vton` 호출은 404** — 모델 자체는
  존재(run_count 150만+)하지만 버전 고정 필요, `cuuupid/idm-vton:0513734a...`
  (latest_version)로 성공. 결과 `tests/fixtures/debug_vton_test01.jpg` —
  **사용자 육안 확인 통과** (원본 회색 티셔츠+ArUco 마커 → 무신사 흰 티셔츠로
  자연스럽게 교체, 얼굴·자세·배경·마커 전부 정상 유지). `replicate>=1.0.7,<2.0`
  requirements.txt 추가. **5-2 인수인계**: 모델 버전을 하드코딩했음 —
  Replicate가 모델을 갱신하면 버전이 바뀔 수 있어 5-2에서 버전 관리 방식
  (고정 vs 동적 조회) 결정 필요
- **5-2 진행 중 (2026-07-21)** — 분해: a) 무신사 이미지 URL 추출 / b) VTON
  서비스 모듈화 / c) POST /synthesize 라우트
  - **5-2a ✅ 완료**: `clothing_scrape.py` `parse_goods()`에 `imageUrl` 추출
    추가 — `thumbnailImageUrl`(상대 경로) + `IMAGE_CDN_BASE`(image.msscdn.net,
    5-1 실증 확인)로 절대 URL 조립, 이미 절대 URL이면 그대로 통과.
    `clothing_normalize.py` `normalize_scraped()`가 raw→spec으로 pass-through
    (없으면 키 자체 생략 — 가짜 채움 금지, 규칙 1). **계약 확장**
    `ClothingSpec.imageUrl?`(CLAUDE.md 6장→types/index.ts→schemas.py 동기화).
    검증: pytest 3건 신규(절대/상대 경로 변환, 누락 시 미포함) 전체 141/141 +
    tsc 통과, 실상품(996177) end-to-end 확인(scrape→normalize→Pydantic 검증
    까지 URL 일치, 5-1에서 쓴 이미지와 동일 URL 재확인)
  - **5-2b ✅ 완료**: `services/vton.py` 신규 — 5-1 스크립트 로직을 재사용
    가능한 `synthesize(human_image, garment_image_url, clothing_category,
    garment_des="") -> bytes`로 정리. **버전 관리**: `MODEL_VERSION` 상수로
    고정(동적 조회는 매 호출 API 1회 추가라 기각) — 코드 주석에 "실패 시
    replicate.com에서 최신 버전 확인 후 교체" 안내. **category 매핑**:
    `CATEGORY_MAP`으로 ClothingSpec.category('top'/'outer'→upper_body,
    'bottom'→lower_body, 'dress'→dresses) 변환, 미지원 종류는 API 호출 전
    `VtonError(unsupported-category)`로 즉시 차단. 에러는 `ClothingScrapeError`
    와 같은 패턴(code+한국어 message)의 `VtonError`로 통일(no-token/
    unsupported-category/synthesis-failed). 검증: pytest 13건 신규(category
    매핑 4종+미지원, 성공 경로 입력 필드 확인, garment_des 전달, API 예외
    래핑, 빈 출력, 토큰 없음, _extract_bytes 분기) 전체 154/154 + tsc,
    **실호출 1회**로 모듈 동작 재확인(`debug_vton_test02_module.jpg` 61.5KB —
    5-1과 동일 이미지 조합, 크기 유사해 정상 확인)
  - **5-2c ✅ 완료 (2026-07-21) → Step 5-2 전체 완료**: 백엔드 `POST /synthesize`
    — `routes/synthesize.py`(def 엔드포인트 — replicate 클라이언트가 동기
    HTTP, clothing.py의 Playwright와 같은 이유로 threadpool 필요, 배운 것
    4번 재사용) + **신규 계약 `SynthesizeRequest/SynthesizeResponse`**
    (ok/imageBase64?/error?/code? — 합성 실패를 크래시 없이 한국어로 전달,
    AnalyzeResponse 방식. CLAUDE.md 6장→types/index.ts→schemas.py 동기화).
    `ClothingSpec.imageUrl` 없으면 VTON 호출 전에 `no-garment-image`로 즉시
    차단(비용 0) + 사진 base64 손상 시 `synthesis-failed`. main.py 라우터
    등록, `/health` phase 5-2c로 갱신.
    검증: pytest 5건 신규(성공 경로 필드 전달·garment_des=productName 확인/
    이미지 없음 단락·API 미호출/잘못된 base64/VtonError 코드 그대로 전파/
    422) 전체 159/159 + tsc, **실서버 통짜 1회**(TestClient 경유, person01_v2
    사진 + 무신사 996177 실제 imageUrl) — ok:true, `debug_vton_test03_route.jpg`
    61.6KB, 5-1·5-2b 결과와 동일 품질 육안 재확인. **Phase 5 Step 1·2 완료 —
    다음은 5-3(히트맵+프론트 배선)**
- **Phase 5-3 진행 중 (2026-07-21)** — 분해: a) synthesizeImage API 함수 /
  b) 랜드마크 픽셀 좌표 노출(계약 확장) / c) "가상 착용 보기" 버튼+화면 /
  d) 히트맵 오버레이(Canvas) / e) 통합 검증. **히트맵 방식은 사용자 결정
  (2026-07-21): A) 정밀 랜드마크 기반** — measure.py의 median_landmarks를
  AnalyzeResponse에 노출해 실제 몸 위치에 정확히 배치(근사 비례·범례 방식은
  기각). 지금까지는 5-3a·5-3c를 함께 구현(API 함수는 버튼 배선과 묶어야
  실제 검증 가능해 순서 조정) — b·d는 다음 단계.
  - **5-3a·5-3c ✅ 완료**: `lib/api.ts` `synthesizeImage()`(POST /synthesize
    래퍼, humanImage.frames는 페이로드 절약을 위해 전송 제외) +
    `FitResultView`에 "가상 착용 보기" 섹션(idle/loading/error/done 상태,
    fit과 달리 **버튼 클릭으로만 시작** — 자동 호출 안 함, VTON 비용 절약) +
    "합성 이미지는 외관 참고용" 안내 문구(그림≠실핏 오해 차단, 07-20 결정
    선반영) + App에 `synthesis` 캐시 추가(fit과 동일 트리거로 무효화:
    새 사진·새 URL·새 스펙 로드, ok=false는 캐시 안 함).
    검증: tsc+build 통과, dist 번들 API 키 grep 청정, E2E 신규 8/8
    (`tests/e2e-synthesize.mjs` — 가짜 백엔드에 `/synthesize` 페이크 추가
    (`e2e_fake_backend.py`, VTON 호출 0·라우트 로직은 실코드), 버튼 클릭
    전 자동 호출 없음·클릭 시 이미지 표시·재진입 캐시로 재요청 없음 확인),
    회귀 10/10(fit)·13/13(clothing-spec)·17/17(analyze)·11/11(clothing-url)·
    14/14(profile)·7/7(autoshoot, 실백엔드 사전 기동 필요 — 배운 것 6번대로
    실백엔드로 재확인해 정상, 가짜 백엔드로 돌리면 배너 셀렉터 타임아웃은
    기존에 문서화된 전제조건 미충족일 뿐 회귀 아님) + pytest 159/159
  - **5-3b ✅ 완료**: `measure.py`에 `landmarks_by_part()` 신규 — 기존에
    대칭성 검사에만 쓰고 버리던 `median_landmarks`에서 4부위(chest/waist/
    hip/shoulder)의 좌·우 x + 평균 y를 뽑아 `measure_with_statistics()`
    반환에 `landmarks` 키로 추가. **신규 계약** `PartLandmark`
    (leftX/rightX/y) + `AnalyzeResponse.landmarks?`(CLAUDE.md 6장→
    types/index.ts→schemas.py 동기화). `routes/analyze.py`가 그대로 전달.
    **프레이밍 전제 확인(5-1·5-2 산출물로 검증)**: person01_v2 원본
    1080×1440 vs VTON 출력 3종 전부 768×1024 — 종횡비 동일(0.75), 크롭 없이
    균등 축소만 있음 확인. 따라서 좌표는 원본 기준으로 반환하고, 프론트가
    (합성 이미지 실제 크기/원본 크기) 배율로 스케일링(5-3d 몫) — 좌표계 자체를
    복잡하게 만들지 않음.
    검증: pytest 3건 신규(4부위 좌우 평균 정확성, 랜드마크 쌍 없으면 해당
    부위 제외 — 가짜 좌표 금지, 파이프라인 통합 확인) + 기존 analyze 라우트
    테스트에 landmarks 응답 검증 추가, 전체 162/162 + tsc, **실사진
    데이터**(person01_v2 랜드마크 캐시, API 0회)로 합리적 픽셀값 확인
    (shoulder y=582.5→hip y=929, 프레임 내 순서·비율 상식적). E2E 회귀
    analyze/fit/synthesize/clothing-url 전부 통과, build 통과
  - **5-3d ✅ 완료 → Step 5-3 전체 완료**: `components/FitHeatmap.tsx` 신규
    — Canvas에 합성 이미지를 그린 뒤, `FitScore.part`별로 5-3b 랜드마크를
    (합성 이미지 실제 크기/원본 크기) 배율로 스케일링해 반투명 색상 밴드
    (tight=빨강/good=초록/loose=파랑, 기존 `fit__status` 배지와 동일 색
    계열) + 수치 라벨("가슴 +2.3cm" 등, 07-20 결정 반영) 오버레이.
    `landmarks` 없으면(오래된 캐시 등) 기존 일반 `<img>`로 폴백 — 크래시
    없이 정직하게 대체 표시. FitResultView가 `image`(원본 크기 기준)·
    `landmarks`(App→analysis에서 전파)를 새로 받아 배선.
    검증: tsc+build+dist 번들 API 키 grep 청정, **E2E 픽셀 검증**
    (`e2e-synthesize.mjs` 확장 — 가짜 백엔드 합성 이미지를 1x1 대신 원본과
    종횡비 동일한 270×360 단색 JPEG로 교체(Pillow), 밴드 중심 픽셀이
    배경과 다름을 실제로 확인해 "스케일링·배치 로직이 그렸다"를 렌더 여부가
    아니라 픽셀 색으로 검증 — 가슴 밴드가 파랑 계열로 나와 loose 판정과
    일치 확인) 8/8 통과, 회귀 fit/clothing-spec/clothing-url/profile-flow
    전부 통과 + pytest 162/162. **Phase 5 Step 1·2·3 전부 완료 — 다음은
    5-4(최종 통합 Gate)**
- **5-4 진행 중 (2026-07-21)** — 최종 통합 Gate. **자동 검증 파트 ✅ 완료**:
  - **FitResult.imageUrl 배선 (마지막 미충족 계약)**: /fit 서버는 채우지 않음
    (합성은 온디맨드 /synthesize — VTON 비용) → **합성 성공 시 프론트 App이
    핏 캐시의 result.imageUrl에 data URL을 채움** (fit·synthesis 캐시가 같은
    트리거로 무효화되므로 불일치 없음). 검증 관측 지점으로 FitResultView 루트에
    `data-image-url` 속성 추가, e2e-synthesize에 합성 전 empty→재진입 후
    filled 검증 2건 확장 (12/12 통과)
  - **Gate 자동 검증 3항목 근거**: ① 합성 이미지 정상 생성 — 5-1·5-2b·5-2c
    실호출 3회 산출물(debug_vton_test01~03, 사용자 육안 확인) + E2E 가짜 경로
    ② 히트맵 FitScore 일치 — e2e-synthesize 픽셀 검증(가슴 loose=파랑 계열
    확인) ③ FitResult.imageUrl 채워짐 — 위 신규 배선+E2E
  - **전체 회귀 재확인 (2026-07-21)**: pytest 162/162, tsc+build, dist 번들
    API 키 grep 청정, E2E 전 스위트 통과 — synthesize 12/12(확장) ·
    fit 10/10 · analyze 17/17 · clothing-spec 13/13 · clothing-url 11/11 ·
    profile-flow 14/14 · autoshoot 7/7(실백엔드)
  - **남은 것**: 수동 검증(합성 육안·히트맵 체감 일치) + 최종 통합 검증
    (실기기 전 과정 완주 — Phase 2 수동 검증·Phase 3/4 실기기 이월분과
    한 세션으로 묶어 처리, 아래 통합 체크리스트) + 라이선스 항목(FASHN 교체는
    출시 전 필수로 유지 — 개발 Gate에서는 "미교체 상태 명시"로 기록)
- **5-4 실기기 세션 1차 (2026-07-21) — 발견 사항과 B안 개선 (정직 기록)**:
  - **C파트(전체 흐름) ✅**: 촬영→측정→의류→핏→합성 실기기 완주, 로그 확인
    (/analyze 1줄 = 프로덕션 단일 호출). **B파트(합성 육안·히트맵 체감) ✅**
    사용자 확인. **A파트(정밀 3회 일관성) ❌ 미통과**: 어깨 0.8 ✓ / 팔 2.4 ·
    다리안쪽 7.9 · 상체 3.4 ✗ — 3회 전부 척도 불일치 r=1.09~1.11(근거리) +
    다리안쪽 44~52cm 상식 밖(밑단-가랑이 혼동 추정, 하의는 밀착 확인됨)
  - **원인 규명 — 층위 3이 근거리를 유도**: 구 기준(마커 ≥60px 하한만)은
    "작으면 가까이 오라"고만 안내 → 사용자가 깊이 편향 구간까지 접근.
    fixtures 오프라인 재계산으로 실증: 42px→r=1.006(ok) / 57px→1.161 /
    59.9px→1.121 / 실기기 3회(≥60px 통과) r=1.09~1.11 전부 depth_bias.
    구 하한 60의 근거("v2 42px Gate 4/8")는 **마커 척도 시절(2-7b 이전)**
    실증 — A안(키 척도) 확정 후 무효
  - **간편 모드 카드 미검출 진단 (실패 사진 재현)**: ① 밝은 셔츠 위 밝은
    카드 = 대비 부족(회전시켜도 실패 — 근본 원인) ② 세로 방향 미지원(±45°)
    ③ 덤: 발 근처 밝은 얼룩 23×14px 오탐 발견(detect_card 강건성 한계 —
    앱에서는 markerSizeOk·r 판정이 방어, 알려진 문제로 기록만). 대응: 어두운
    밀착 상의 + 밝은 카드 가로 방향으로 재시도 안내
  - **B안 개선 구현 ✅ (사용자 승인 — 검증 중단 후 개선 먼저)**:
    ① 거리 밴드 판정 — MIN/MAX_MARKER_WIDTH_PX(40~55px), /check-photo 사유가
    방향 안내(다가와/물러나), measure.py 강등도 밴드 기준. 신규 pytest 6건
    (구 60px 거부 회귀 방어선 포함) 전체 168/168 (커밋 e698b30)
    ② 원거리 인지 UI — 화면 테두리 색(빨강/초록, 2m에서 인지) + TTS 음성
    안내(판정 사유·카운트다운 낭독, 같은 안내 7초 억제, 🔊 토글 App 보관).
    y4m 1080px 네이티브 42px 재생성(밴드 내 + suspect 시나리오 유지).
    E2E 전 스위트 통과: autoshoot 10/10(테두리·토글 검증 추가)·analyze 17/17·
    profile 14/14·synthesize 12/12·fit 10/10·clothing 11/11·13/13
  - **개선 백로그 (③~⑥, 미구현)**: 층위 1 안내 그림화 / 실루엣 거리 자 /
    카드 전용 오버레이(가로 박스+대비 조건) / 촬영 후 실패 시각화
  - **1차 실기기 정밀 3회 원값 (2026-07-21 15:21/15:22/15:24 — 참고 기록.
    스크린샷 원본은 사용자 보관, 수치는 여기 보존)**:
    | 항목 | 1회 | 2회 | 3회 | 편차 |
    |---|---|---|---|---|
    | 키(입력 고정) | 172.0 | 172.0 | 172.0 | 0.0 |
    | 어깨 | 41.8 | 42.6 | 41.9 | 0.8 ✓ |
    | 가슴둘레 | 106.8 | 103.0 | 101.0 | 5.8 (기록만) |
    | 허리둘레 | 93.3 | 103.7 | 95.7 | 10.4 (기록만) |
    | 엉덩이둘레 | 101.7 | 106.6 | 99.5 | 7.1 (기록만) |
    | 팔 길이 | 65.5 | 65.2 | 67.6 | 2.4 ✗ |
    | 다리 안쪽 | 44.1 | 52.0 | 46.7 | 7.9 ✗ (3회 전부 상식 밖) |
    | 상체 길이 | 76.6 | 74.3 | 77.7 | 3.4 ✗ |
    척도 불일치: 9% / 11% / 9% (전부 depth_bias — 근거리). 신뢰도 거의 전
    항목 낮음(2회차 어깨만 높음). 촬영 조건: 밀착 상의+속바지, 마커 가슴 부착.
    카드 실패 사진 원본은 사용자 OneDrive 바탕화면 20260721_155140.jpg
- **5-4 실기기 재검증 보류 (2026-07-21 사용자 결정) — 개선 백로그 ③~⑥ 먼저
  진행**: 분해안 승인 — B-1 카드 전용 오버레이(⑤) → B-2 실루엣 거리 자(④) →
  B-3 층위 1 그림화(③) → B-4 촬영 후 실패 시각화(⑥). 재검증 절차·통과 기준은
  위 기록 그대로 유효, 백로그 완료 후 재개. 음성 안내·자동 촬영 기능은 코드
  확인 결과 그대로 존재(사용자 질의에 검증 답변) — 백로그는 그 위에 얹는 작업
  - **B-1 (⑤) ✅ 완료 (2026-07-21)**: 간편 모드 카드 전용 오버레이 —
    실루엣 SVG에 가로 카드 박스(ISO 비율 85.6:53.98, 가슴 위치 viewBox y40~54,
    실선으로 실루엣 점선과 구분) + 기준물 문구 교체("💳 카드를 가로 방향으로,
    어두운 상의 위에", 박스를 가리지 않게 28.5%로 하향) + 층위 1 항목 ②도
    카드일 때 방향·대비 문구로 분기. 근거: 1차 실기기 실증(세로 방향 미지원
    ±45° + 밝은 옷 위 대비 부족). `CameraView.tsx`+`index.css`만 수정 —
    판정 로직·자동 촬영·TTS 무변경. 검증: tsc+build, E2E profile-flow
    18/18(신규 4건: 간편 박스 표시·문구 방향/대비 포함·정밀 모드 박스 없음·
    마커 문구 유지), 회귀 autoshoot 10/10(실백엔드)·analyze 17/17,
    스크린샷 육안 확인(박스 가슴 위치·문구 비간섭)
  - **B-2 (④) ✅ 완료 (2026-07-21)**: 실루엣 거리 자 — 실루엣 SVG 내부에
    머리(y=2)·발(y=186) 노란 점선 기준선 + 라벨("머리를 이 선에" /
    "↓ 발을 이 선에 — 약 2m"). 층위 3 판정(마커 픽셀 밴드) 이전의 예방 층 —
    1차 실기기 A파트 실패 주범(근거리 접근)을 거리 판정 전에 시각적으로 차단.
    **구현 교훈**: 처음 HTML 퍼센트 역산(5.8%/82.2%)으로 만들었다가 스크린샷
    육안 확인에서 어긋남 발견(SVG meet 레터박스 — viewBox 비율 0.5 vs 요소
    박스 비율이 달라 세로 letterbox 발생) → **SVG viewBox 좌표 내부에 직접
    그리는 방식으로 교체**(화면 비율 무관 정확 정렬). 발 라벨은 y=170으로
    올려 하단 고정 토글·배너(bottom 118px)와 비겹침. `CameraView.tsx`+
    `index.css`만 수정 — 판정 로직 무변경. 검증: tsc+build, E2E profile-flow
    20/20(신규 2건: 기준선 2개·라벨 2m 안내), 회귀 analyze 17/17·autoshoot
    10/10(실백엔드), 스크린샷 육안 확인(v3 — 선이 실루엣 머리·발에 정확히
    붙고 라벨 겹침 없음)
- **다음 시작 지점: 백로그 B-3 (③ 층위 1 안내 그림화) → B-4 →
  5-4 실기기 재검증(A파트 정밀 3회 + 간편 1회) → qa Gate 리포트**
- (아래는 4-2 설계 기록 — 구현 완료됐으나 근거 추적용 보존)
  설계안 요지 (2026-07-18 제시 — 세션 무관 재개용 기록):
  - **알고리즘 2단계**: ① 하한 필터 — 비교 부위 중 tight가 있는 사이즈는
    후보 탈락 ② 후보 중 이상 여유(EASE_RANGES 중앙값: chest +11 / waist +7 /
    hip +8 / shoulder +1)에 가중 거리 최소인 사이즈 추천. 동점이면 작은 쪽
  - **가중치(추정)**: top/outer = chest .6·shoulder .3·waist .1 /
    bottom = hip .6·waist .3 / dress = chest .5·waist .25·hip .25
  - **관찰 1 반영**: 필터는 하한만(loose는 탈락 아님 — 드롭숄더 옷 배제 방지)
    + 어깨 가중 낮음. 손계산: 티셔츠 M / 아크테릭스 M 추천 (상식 부합)
  - **관찰 2 반영(핵심 결정 지점 — ⚠️ 사용자 답 대기)**: 하의 허리 처리
    3안 중 선택 — A안(권장): 필터 유지 + 전 사이즈 tight면 가장 덜 tight한
    사이즈 + insufficient 플래그·경고 반환 (근거 없는 보정 없이 정직 안내,
    배럴 데님이면 XL+플래그) / B안: 허리를 필터에서 빼고 점수만 반영 (단점:
    허리 100에 hip 기준 S 추천 같은 비상식 가능) / C안: 레벨 보정 계수 도입
    (단점: 라이즈마다 달라 상수화 근거 없음 — 규칙 1 위반 소지).
    사용자가 판정 전 추가 확인 원함 — 재개 시 3안 설명부터
  - **신축성**: stretch high → 필터 하한 −4cm, low → −2cm (둘레만, 추정).
    무신사 미제공이라 없으면 완화 0 (안전 기본값)
  - **엣지**: 비교 부위 0인 사이즈 제외, 전부 그러면 추천 불가(None)+사유.
    estimated 사이즈는 사용하되 플래그 유지
  - **검증 계획**: pytest(필터·거리·동점·insufficient·신축성·불가 경로) +
    실데이터 3종(예상: 티셔츠 M / 아크테릭스 M / 데님 XL+플래그)
  - 구현 산출물은 fit.py 확장 `recommend_size()` — 계약 변경 없음
    (FitResult 조립·API 배선은 4-4)

## 실기기 세션 통합 체크리스트 (Phase 2 + Phase 3 수동 검증 — 한 세션 처리)

> 준비물: 폰, ArUco 마커(7cm 출력본), 신용카드, 줄자로 잰 본인 키(cm),
> 밀착 의류(v2 촬영 조건), 무신사 상품 URL 3종(상의/하의/아우터 등 카테고리 달리)

**0. 환경 구성 (프로덕션 빌드 — dev 서버 금지, 배운 것 1번)**
```powershell
# 창 1 — 백엔드
cd C:\claude_code\FITME\server
.\venv\Scripts\uvicorn.exe main:app --port 8000
# 창 2 — 프론트 프로덕션 빌드 + preview (4173)
cd C:\claude_code\FITME
npm run build
npm run preview
# 창 3 — 터널 (폰에서 출력된 https URL 접속)
& "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" tunnel --url http://localhost:4173
```
- [ ] 폰에서 접속 → 첫 측정 후 uvicorn 콘솔 `POST /analyze` **1줄** 확인
      (2줄 = dev 접속 = 비용 2배 → 중단·재확인. 1-b 항목 참조)
- [ ] ⚠️ 터널은 세션 동안만 열고 종료 시 즉시 닫기 (API 키 보호)

**A. Phase 2 파트 — 측정 일관성 (정밀 3회 + 간편 1회)**
- 촬영 조건 (v2 기준 — 배운 것 28·29번 근거): **밀착 의류**, 마커를 가슴에
  **평평하게**, 약 2m 거리, **전신을 프레임에 꽉 차게**, 같은 옷·자리·거리 유지
- [ ] 정밀 모드(마커): 실제 키·몸무게 입력 → 자동 촬영 → 결과 8항목 스크린샷
      × **3회 반복**
- [ ] 간편 모드(카드): 동일 절차 × 1회
- [ ] 판정: 3회 간 **키·팔·다리안쪽·상체·어깨** 편차 ≤2cm → 통과 (13-2).
      둘레 3종·실측 차이는 기록만 (12장 알려진 한계 / Phase 4 편향 자료)

**B. Phase 3 파트 — 의류 추출 대조 (무신사 3종)**
- [ ] 측정 결과 → "의류 사이즈 비교" → 무신사 URL 3종 순서대로 조회
      (카테고리 달리 — 예: 상의/하의/아우터. AI 호출 0, 첫 조회만 십수 초)
- [ ] 각 상품: 앱 사이즈 표 스크린샷 ↔ 무신사 페이지 실제 사이즈표 대조
      (단면 표기는 앱이 ×2 둘레 환산임을 감안 — 예: 가슴단면 52.5 = 앱 105.0)
- [ ] 통합 확인: 촬영→측정→의류 URL→스펙 표시 전체 흐름이 실기기에서 끊김 없음

**C. 예상 AI 호출·비용 (추정 — 시작 전 참고)**
- Phase 2 파트: 측정 4회 × 7프레임 = **AI 28회** (자동 촬영 /check-photo 폴링과
  Phase 3 파트는 AI 0회)
- 회당 단가(추정): 모델 claude-opus-4-8 = 입력 $5/1M·출력 $25/1M 토큰.
  호출당 입력 ≈ 이미지(1080px, ≈2,100토큰) + 프롬프트 ≈ 3,000토큰,
  출력 ≈ 300토큰(좌표 JSON) → **약 $0.02/회**
- 세션 합계 ≈ 28회 × $0.02 ≈ **$0.6 수준** (프롬프트·이미지 비율에 따라 ±,
  여유 잡아 $1 미만). 재촬영이 늘면 측정 1회당 +$0.15 정도로 계산
- 실측 확인: 세션 후 Anthropic 콘솔 usage에서 실제 토큰·비용 대조

**D. 세션 종료 후**
- [ ] Phase 2: 통과 시 qa Gate 리포트 작성(9장 양식) → 사용자 승인 →
      Phase 2 Gate 상태를 "미완"에서 통과로 갱신
- [ ] Phase 3: 통과 시 qa Gate 리포트 작성 → 사용자 승인
- [ ] 두 리포트를 PROGRESS.md에 기록(13-4) + git commit·push
- [ ] 태그: `git tag phase-2-complete && git tag phase-3-complete && git push --tags`
- [ ] 실패 항목이 있으면 규칙 3에 따라 해당 Phase에 머물러 수정 → 세 검증
      처음부터 재실행 (Phase 4 진입 금지)
  ⚠️ Phase 4 수동 검증(아는 옷 대조)은 Phase 2 편향 일정성 가정의 실질
  검증이므로, 늦어도 그 전에 Phase 2 수동 검증(반복 일관성)을 완료할 것

## 주의사항 / 배운 것 (Phase 3에서)

1. ★ **React StrictMode(dev 전용)가 /analyze를 마운트 시 2회 전송** — 2-8e부터
   있던 동작(cancelled 플래그로 UI는 정상, 프로덕션 빌드는 1회). **dev 서버
   경유 실폰 검증 시 측정 1회 = AI 14회(7×2)로 비용 2배.**
   → **협의 완료 (2026-07-18 사용자 결정): 실기기 수동 검증은 프로덕션 빌드
   (build→preview→터널)로 수행. 코드 개선(마운트 가드·StrictMode 제거)은
   하지 않음 — 프로덕션에서는 무해하고, 코드 변경 0으로 해결되며, 실사용자와
   동일 조건이라 오히려 더 정확.** 절차는 아래 "Gate 수동 검증 절차" 1번과
   실기기 세션 통합 체크리스트에 반영됨. dev 서버로 실폰 측정 금지.
2. React 제어 입력은 puppeteer 삼중 클릭으로 텍스트 교체가 안 됨 — E2E에서
   값을 바꿀 때는 Ctrl+A 선택 후 타이핑 (e2e-clothing-url.mjs 참조).
3. ★ **무신사는 비공식 공개 API 2개로 사이즈표가 나온다** (2026-07-17 탐사):
   `goods-detail.musinsa.com/api2/goods/{no}`(상품)와 `…/actual-size`(실측).
   응답 봉투는 `{meta:{result:'SUCCESS'}, data:…}`. 부위 값은 **단면(flat)**
   기준(예: 가슴단면 52.5 = 둘레 105). 비공식이므로 무신사가 바꾸면 깨질 수
   있음 — 파싱은 순수 함수로 분리해 두어(parse_goods/parse_sizes) 구조 변경
   시 오프라인 테스트로 즉시 감지·수정 가능. 요청은 상품당 2회(부하 최소),
   일반 브라우저 UA 필수.
4. **Playwright sync API는 FastAPI async 라우트에서 직접 못 씀** — 3-4에서
   `/clothing` 라우트는 `def`(threadpool) 엔드포인트로 만들거나 async API로
   전환할 것. (→ 3-4a에서 `def`로 구현 완료)
5. **가짜 구현(E2E fake)은 실계약의 에러 경로까지 따라야 한다** — 3-4b에서
   fake scrape가 URL 무관 성공을 반환해, 지원 외 쇼핑몰 시나리오가 오류
   화면 대신 성공 화면을 띄워 E2E 실패. 실코드의 판정 함수(parse_musinsa_url)를
   fake가 재사용하도록 수정해 해결. 새 fake를 만들 때는 "성공 응답"만이 아니라
   "어떤 입력에서 어떤 실패를 내는가"까지 실코드와 맞출 것.
6. **e2e-autoshoot.mjs는 실백엔드(8000) 사전 기동 전제** — 다른 E2E처럼
   가짜 백엔드를 스스로 띄우지 않음. 서버 없이 돌리면 배너 셀렉터 타임아웃
   2건으로 실패 (3-4b 회귀 중 실제 겪음 — 코드 문제 아님).
- (이하 절차 기록은 추후 수동 검증 재개용으로 보존)
  - **수동 검증 세션 중간 기록 (2026-07-17)**: ① 자이로 2축 실폰 작동 확인
    (데스크톱 불가 항목). ±7° 맞추기 어렵다는 의견 있었으나 **사용자 결정으로
    현 상태 유지** (배지는 순수 안내용 — 판정·측정에 미관여, 기울기 실판정은
    마커 비율이 담당) — 임의 "개선" 금지 ② 기준물 칩 배 높이 버그 발견·수정
    (32%→24%, `8cca4e5`) ③ 다중 프레임 7장 실동작 사용자 확인
  - **Gate 수동 검증 절차 (세션 무관 재개용 — 결과 대기 중)**:
    1. 환경 — **프로덕션 빌드 기준 (2026-07-18 결정, dev 서버 금지)**:
       dev 서버는 StrictMode가 /analyze를 2회 전송해 측정 1회 = AI 14회
       (비용 2배)가 되므로, 실기기 검증은 반드시 프로덕션 빌드로 한다
       (코드 변경 0 + 비용 절반 + 실사용자와 동일 조건).
       ```powershell
       # ① 백엔드
       cd C:\claude_code\FITME\server
       .\venv\Scripts\uvicorn.exe main:app --port 8000
       # ② 프론트 (새 창): 빌드 후 preview (포트 4173)
       cd C:\claude_code\FITME
       npm run build
       npm run preview
       # ③ 터널 (새 창): 4173으로 연결 — 폰에서 https URL 접속
       & "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" tunnel --url http://localhost:4173
       ```
       preview는 vite.config.ts의 server 설정(proxy /api→8000, allowedHosts
       .trycloudflare.com)을 상속한다 — 2026-07-18 로컬 검증 완료(정적 200 /
       preview 경유 /api/health ok / trycloudflare 호스트 헤더 200).
       터널 1개(4173)로 백엔드까지 커버. ⚠️ 터널은 검증 시간에만 (API 키 보호)
    1-b. **AI 호출 수 확인 (검증 시작 전 1회 필수)**: 첫 측정 직후 uvicorn
       콘솔에서 `POST /analyze` 로그가 **1줄**인지 확인 → 1줄 = 프레임 7장
       = AI 7회 (정상). **2줄이면 dev 서버(StrictMode 이중 전송 = 14회)로
       접속한 것** — 즉시 중단하고 폰이 4173 preview 터널에 접속했는지 확인.
       교차 확인은 Anthropic 콘솔 usage 대시보드
    2. 정밀 모드 3회: 실제 키·몸무게 입력 → 마커 가슴에 평평(칩 위치 참고),
       ~2m, 전신 꽉 차게 → 자동 촬영 → 결과 8항목 스크린샷.
       **같은 옷·자리·거리로 3회 반복** (측정 1회 = API 7회)
    3. 간편 모드(카드) 1회 동일 절차
    4. 판정: 3회 간 **키·팔·다리안쪽·상체·어깨** 편차 ≤2cm → 통과.
       둘레 3종·실측 차이는 기록만 (12장 알려진 한계 / Phase 4 편향 자료)
    5. 통과 시 qa Gate 리포트 작성(9장 양식) → 사용자 승인 → Phase 3
  - **Gate 기준(조정, 2026-07-16)**: 일관성(반복 편차 2cm)은 길이 항목+어깨에
    적용, 둘레 3종은 알려진 한계 — CLAUDE.md 13-2

## 로컬 전용 자산 (GitHub에 없음 — PC 이동 시 이 목록만 신경 쓰면 됨)

| 자산 | 복구 가능성 |
|------|-------------|
| `server/tests/fixtures/person01_card.jpg` (1206px) | ❌ 재촬영/폰 재복사 필요 — **개인 클라우드 백업 권장** |
| `server/tests/fixtures/person01_aruco.jpg` (1080px 실전 조건) | △ 원본에서 재생성 가능 (아래 원본 필요) |
| `server/tests/fixtures/person01_aruco_original.jpg` (3000×4000) | ❌ 재촬영/폰 재복사 필요 — **백업 권장** |
| `server/tests/fixtures/person01_truth.json` (실측값, 옷 입은 상태) | △ 숫자만 다시 입력하면 됨 (재실측 불필요, 값은 본인이 앎) |
| `server/tests/fixtures/person01_aruco.landmarks.json` (좌표 캐시) | ✅ API 1회 호출로 재생성 (`--fresh`) |
| `server/tests/fixtures/debug_*.jpg` (확인용 이미지) | ✅ 전부 재생성 가능 |
| `server/tests/fixtures/calibration_set.json` (다인 검증 manifest) | ✅ 형식은 fixtures/README.md — 몇 줄 재작성 |
| `server/.env` (ANTHROPIC_API_KEY) | ✅ 키 1줄 재입력 (유출 의심 시 콘솔에서 재발급) |
| `server/venv` | ✅ `python -m venv venv` + `pip install -r requirements.txt` |
| `node_modules` | ✅ `npm install` |

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

### Step 2-2 — OpenCV 신용카드 검출, 간편 모드 (2026-07-14 완료)

**만든 파일**
- `server/services/reference_detect.py` — `detect_card()`: ReferenceInfo 형태 반환
- `server/tests/test_reference_detect.py` — pytest 5건

**기능**
- 윤곽선 → 4꼭짓점 → 비율(85.6:53.98 ≈ 1.586) 판정, 기울어진 카드 대응
- 2전략: A) 에지 기반 닫힌 4각형(카드 온전할 때 정밀) → B) 밝은 블롭−피부
  마스크(YCrCb) + 회전 사각형 피팅(손가락이 카드를 쥐어 윤곽이 손으로 새는
  실사용 기본 상황 대응 — 실사진에서 A 실패, B 성공)
- 오검출 방지 필터: 비율 1.35~1.85, 면적 0.02~2%, 채움 ≥0.7, 가로 방향 ±45°
- **꼭짓점 순서 계약: 좌상→우상→우하→좌하 (2-4 호모그래피가 이 순서에 의존,
  테스트로 고정)**
- 알려진 한계(코드 주석에 명시): 전략 B는 "옷보다 밝은 카드" 가정 — 어두운
  카드+어두운 옷 미지원, fixtures 3명분 모이면 보강 판단

**검증 결과**
- 실사진(person01_card.jpg) 검출 성공 — 육안(디버그 이미지) + 사용자 확인
- 음성: 노이즈·단색·앱 스크린샷 → 전부 detected:false
- 자동 테스트 10/10 통과 (기존 5 + 신규 5)
- 디버그 CLI: `.\venv\Scripts\python.exe services\reference_detect.py <사진> [출력.jpg]`

**관련 커밋**: `5dad5ee`(개발), `e6a4fed`(테스트)

### Step 2-3 — ArUco 마커 검출(정밀 모드) + 마커 PDF (2026-07-15 완료)

**만든/바꾼 파일**
- `server/services/reference_detect.py` — `detect_aruco()` 추가 (2-2 카드 검출 무변경)
- `server/scripts/generate_marker.py` — 마커 PDF 생성 (1회 실행 도구)
- `server/data/aruco_marker.pdf` (+ 미리보기 PNG)
- `server/tests/test_reference_detect.py` — ArUco 테스트 6건 추가

**마커 규격 (중요)**
- 한 변 **7cm** — `services/reference_detect.py`의 `MARKER_SIZE_MM = 70.0`이
  **단일 출처** (검출·PDF 생성·척도 계산이 전부 이 값 참조. 바꾸면 재출력 필수)
- DICT_4X4_50, 기본 ID 0. cv2.aruco 4.9 신 API(`ArucoDetector` 클래스) 사용
- PDF: A4 300dpi, 100% 출력 경고, 7cm 검증 눈금자, 절취선(마커에서 1.5cm) 포함

**검증 결과**
- 실물 검증: 사용자가 100% 출력(자로 7cm 확인)·절취·촬영 → **ID 0 검출 성공**
- 배경 사각형(창문·책상) 오인식 0건 — ID 패턴 검증이 전부 reject
- 합성 페이지 자기 검증(827px 기대/826px 검출), 노이즈·카드 사진 음성
- 전체 테스트 16/16 통과, 2-2 카드 검출 회귀 없음
- 꼭짓점 순서 계약(좌상→우상→우하→좌하) 카드와 동일 — 테스트로 고정

**관련 커밋**: `9239f8a`(검출), `cd2a8dd`(PDF 절취선), `0e1b293`(테스트)

### Step 2-4 — 호모그래피 척도 계산 (2026-07-15 완료)

**만든 파일**
- `server/services/measure.py`
  - `compute_scale(ReferenceInfo)` — 카드/ArUco **공통 인터페이스**. 4꼭짓점 ↔
    실측 mm 대응으로 호모그래피(px→기준물 평면 mm) 계산
  - `distance_mm(scale, p1, p2)` — 사진 위 두 점의 실거리(2-6이 사용할 함수)
  - 반환값 `trace`에 계산 전 과정(꼭짓점·변 길이·가로/세로 척도) 포함 — 역추적용

**코드에 명시한 전제 2가지**
1. 꼭짓점 순서 계약(좌상→우상→우하→좌하, 2-2/2-3 테스트로 고정)에 의존
2. 호모그래피는 **기준물이 놓인 평면에서만 정확** — 깊이 차이는 촬영 가이드
   (전략 1) + 타원 근사(2-6)가 보완

**검증** (합성 이미지)
- 기하 검증: 실제 500mm → 500.000mm (오차 0.0005mm)
- 렌더링 파이프라인(마커 그리기→원근 왜곡→검출→척도→거리): 오차 0.67%

**관련 커밋**: `f87bd01`

### Step 2-5 — Claude Vision 신체 부위 좌표 추출 (2026-07-15 완료)

**만든 파일**
- `server/services/claude_vision.py` — `extract_body_landmarks(base64, w, h)`:
  **15개 랜드마크** 픽셀 좌표 추출 (head_top, neck_base, 어깨×2, 가슴/허리/
  엉덩이 실루엣 가장자리×각2, left_wrist, crotch, left_ankle, 발뒤꿈치×2).
  좌표는 `measure.distance_mm()`에 바로 입력 가능한 [x,y] 형태.
- **랜드마크 → 8개 치수(BodyMeasurements) 매핑은 2-6 몫** (여기서 안 함)

**JSON 방어 (그룹 B-5)**
- 코드펜스 제거 → 정규식 `{}` 추출 → 스키마 검증(15키 전부, [x,y] 숫자,
  이미지 범위 내) → 실패 시 **1회만** 재요청 (무한루프 금지)

**검증**
- 1080px fixture(person01_aruco.jpg)로 실제 호출 — 15개 지점 전부 올바른
  부위에 찍힘 (debug_landmarks_person01_aruco.jpg 육안 확인, 좌우 규약 준수)
- API 사용량: 총 2회 (키 확인 핑 1 + 좌표 추출 1)
- 자동 테스트 11건 추가 (파싱 방어 3, 스키마 검증 4, 재요청 로직 3, 캐시 1)
  — **전부 API 호출 0회** (mock + 불통 주소 기법). 전체 37/37 통과

**관련 커밋**: `7f29107`(개발), `c2a42fd`(테스트)

### Step 2-7 — 전략 3: 다중 측정 중앙값·해부학 비율·신뢰도 (2026-07-16 완료)

**만든 것** (`measure.py` 확장, 기존 로직 무변경)
- `measure_with_statistics()`: N회 랜드마크 → 항목별 중앙값 + 반복 편차 통계.
  신뢰도용 편차는 "보고값(중앙값)의 안정성"(N≥5: 3회-중앙값 산포) 사용
- 해부학 비율 교차 검증(범위는 "추정" 명시), 신뢰도 산정 기준 상수화
  (편차 1/2cm, 마커 40px, 기울기 비 0.9~1.1, 범위 위반 시 강제 low, 둘레 상한 medium)

**검증 (동일 사진 13표본, API 신규 12회 사용 — 전부 캐시됨)**
| 구분 | 단일 | 3프레임 | 5프레임 | 7프레임 |
|------|-----:|-----:|-----:|-----:|
| 편차 ≤2cm 항목 | 0/8 | 4/8 | 6/8 | **7/8** |
- 키 4.4→0.1cm 등 극적 개선. **기본 프레임 수 7 확정**
- 허리 3.5cm는 프레임 수 무관(정의 모호) → 옵션 A 보류(밀착 옷 데이터 후 결정)
- 신뢰도 시스템이 반바지 왜곡(다리안쪽·상체길이)을 스스로 low 강등 + 경고 4건

**관련 커밋**: `22bfd52`

### Step 2-7b — 키 캘리브레이션(A안)·BMI 둘레 보정·계수 역산 (2026-07-16 완료)

**만든/바꾼 것**
- `models/schemas.py`: `UserProfile`(heightCm 필수, weightKg 선택) +
  `AnalyzeRequest.profile`(선택 — 2-8 UI 연결 전까지 기존 규격 불파손)
- `services/measure.py` 2-7b 섹션: `scalar_distance_mm`, `height_scale_from_runs`
  (사진당 척도 1개 — head-heel 픽셀 중앙값), `check_scale_agreement`(5%/20% 구간),
  `bmi_depth_ratios`(BMI 구간표, 추정 명시), `landmarks_to_measurements` 척도 주입
  확장, `measure_with_statistics`에 profile 통합(suspect 시 전 항목 신뢰도 강등,
  stats.scale 역추적 필드)
- 계수 역산(v2·truth_v2·A척도 기준, **표본 1명 — 일반화 미검증**): 어깨 곡면
  1.1823, 둘레 깊이 base chest 0.7681 / waist 0.9740 / hip 0.8331 (person01
  BMI 26.6의 +0.05 가감 제외값)
- `scripts/verify_27b.py`: 척도 3방식 + A/B 비교 + 최종 파이프라인 표 (캐시
  39회분, **신규 API 호출 0**)
- `tests/test_measure_27b.py`: 합성 데이터 10건 — 전체 47/47 통과
- `person01_truth_v2.json`에 weight_kg 78.7 기록 (gitignore 확인 — 로컬 전용)

**A/B 결정 (사용자 확정)**: A안(전 항목 키 척도). 근거 = 폭 원자료의 사진 간
일관성(같은 사람)에서 A 산포 1.1~3.0cm vs B 2.2~5.2cm — B의 이론적 장점(폭은
마커 평면)이 마커 검출 노이즈에 밀려 실현 안 됨. 반복 편차는 동률.

**최종 오차 (표 6)**: 키 0(자명) / 어깨 v1 +2.2, v3 +1.3 (역산 전이 양호) /
엉덩이 -0.3~-2.4 / 가슴·허리 v1/v3 +4~+9(깊이 편향 전이 — 배운 것 30번) /
다리안쪽 -14~-37 잔존(crotch 정의 편향, 계수 범위 밖 — 기록만).
반복 편차 Gate: v1 7/8, v2 4/8, v3 5/8 (미달 항목은 허리=옵션 A 예정,
v2 엉덩이·다리안쪽·상체=몸이 프레임에 작은 사진 조건).

**관련 커밋**: `dbf84d4`

**다인(多人) 검증 상시 구조 (2026-07-16 추가 — 사용자 요청)**
- 추가 검증 시점이 미정이므로, 표본만 확보되면 **Phase 진행과 무관하게 언제든**
  돌릴 수 있는 구조를 선행 구축: `scripts/calibrate_multi.py` +
  `fixtures/calibration_set.json`(manifest, 로컬 전용) + fixtures/README.md에
  대상 추가 절차(v2 촬영 조건 필수, --collect 13 = API 13회/대상)
- 기능: 대상별 계수 역산 / 사람 간 산포(일반화 판정) / N≥2 시 Leave-One-Out
  ±3cm/±5cm 검증 자동 / r 판정 ok 아닌 대상 경고(계수 오염 방지)
- 구조 검증: N=1(person01 v2)로 실행 → 2-7b 계수를 차이 0.0000으로 재현 확인
- 계수 상수 갱신은 자동 아님 — 사용자 결정 후 수동 + pytest·verify_27b 재검증

**fixture 2종 체계 (2026-07-15 정리, 로컬 전용)**
- `person01_aruco.jpg` = 3000×4000 원본 → **폭 1080px 리사이즈 + JPEG 85%**
  (image.ts와 동일 방식) — **실전 조건, 기본 테스트용**
- `person01_aruco_original.jpg` = 3000×4000 원본 그대로 — 상한 성능·디버깅용
- 3조건 척도 실측: 855px → 1px=1.806mm / **1080px(실전) → 1px=1.174mm (마커
  59.9px)** / 원본 → 1px=0.420mm (마커 166.6px, 가로/세로 완전 일치)
- 테스트 16/16이 새 1080px fixture로 통과 확인

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

- ~~2-1 FastAPI~~ ✅ → ~~2-2 카드~~ ✅ → ~~2-3 ArUco~~ ✅ → ~~2-4 호모그래피~~ ✅
  → ~~2-5 Claude Vision~~ ✅ → ~~2-6 cm 산출~~ ⚠️(개발 완료, 실측 0/7은 참고 기록화)
  → ~~2-7 다중 프레임·신뢰도~~ ✅(프레임 7 확정) → **2-7c 가이드 백엔드(다음)**
  → 2-7b 정확도 보강(키·몸무게, 계수 역산은 밀착 옷 데이터 후)
  → 2-8 촬영 가이드 4층위 UI + 실제 API 연결 + 키·몸무게 입력 UI
- **사전 준비물 (사용자에게 요청할 것)**: 카드 포함 전신 사진 + 줄자 실측 정답값,
  현재 1명분(person01) 확보 — 추가 표본은 향후 과제(절대 정확도 검증 시).
- Phase 2 Gate (2026-07-16 기준 전환): 자동 7항목 + 수동(일관성 확인: 반복 편차
  2cm + 실측 차이 참고 기록) + 통합 + 보안(프론트 번들 API 키 grep).
  절대 정확도(±3cm/±5cm, 3명)는 Gate 제외 — 배운 것 26번, CLAUDE.md 13-2

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
5. **fixtures 사진은 로컬 전용(.gitignore)** → 사진 없는 환경(새 클론)에서는
   사진 의존 테스트 3건이 skip 처리됨 (실패 아님). 전체 테스트 수가 줄어
   보여도 정상.
6. **카드 검출은 비율 필터가 생명**: 배경의 액자·탁자(크기 초과), 체크무늬
   옷(정사각형 1.0), 벽·바닥 패치(세로 방향)를 카드로 착각하지 않는 것은
   비율(1.586±)·면적·채움·가로방향 필터 조합 덕분. 필터 값을 바꿀 때는
   반드시 실사진 + 음성 3종 테스트를 다시 돌릴 것.
7. **"닫힌 윤곽" 가정은 실사용에서 깨진다**: 손가락이 카드를 쥐면 윤곽이 손으로
   이어져 교과서식 4각형 검출이 실패. 가림을 전제로 한 전략 B가 기본 경로.
8. **커밋 ≠ 보존 완료**: `git status`에서 "ahead of origin"이 보이면 아직 push 안 된
   것. Step 완료 보존 시 반드시 push까지 확인.
9. ★ **ArUco는 좌우 반전(거울상) 사진에서 검출 불가 — 실물로 입증됨** (2026-07-15).
   폰 기본 카메라의 셀피 "미리보기처럼 저장" 설정이 원인이었고 재촬영으로 해결.
   FITME 앱 캡처는 Phase 1 설계상 원본 저장이라 안전하지만, **프론트에 파일
   업로드 경로를 추가하게 되면 EXIF 회전과 함께 거울상 여부도 검사해야 함**.
10. ★ **조건부 숙제 — 원본 해상도 사진 확보**: 현재 fixtures의 aruco 사진이
   368×1146(폰에서 크롭·축소된 편집본, 마커 42px). 검출은 통과했지만
   **2-4 척도 정밀도·2-6 실측 검증에는 부족** (마커 1px 오차 ≈ 1.7mm 증폭).
   2-4 시작 전 또는 늦어도 2-6 검증 전까지 원본(3000×4000급, 마커 100px+)
   확보 필요. 카톡 전송은 재압축되므로 USB/Drive로, 크롭 편집본 말고 원본을.
11. **마커 여백(절취선 안쪽 흰 여백)이 인식에 필요** — 마커 테두리에 바짝 자르면
   검출 실패. PDF의 절취선(1.5cm)을 따라 자르도록 안내 유지.
12. ★ **"원본 해상도 확보" 숙제 해결 (2026-07-15). 단, 실전 조건은 1080px** —
   웹 getUserMedia는 비디오 파이프라인이라 폰 사진모드 12MP와 다르고,
   CLAUDE.md 그룹 B-8이 1080px 리사이즈를 규정. 정확도 판단은 항상 1080px
   fixture 기준으로.
13. ★ **폰→PC 사진 이동 시 카톡·메신저는 자동 재압축** (여러 번 실패로 확인).
   구글 드라이브(원본 크기 업로드) 또는 USB(DCIM 직접 복사)로만 원본 유지됨.
   갤러리 "공유" 버튼도 축소본을 보낼 수 있음.
14. ★ **촬영 가이드에 반영할 실측 교훈 (2-8 UI 작업 시)**: ① 전신을 프레임에
   꽉 차게 찍으면 마커가 예상보다 크게 잡힘(60px, 척도 1.174mm/px).
   ② 마커를 평평하게 붙이면 가로/세로 척도가 완전 일치(0.4201/0.4201) —
   기울면 벌어지므로 "평평하게"가 중요.
15. ★ **미결 질문: 1080px(1px=1.174mm)에서 ±3cm 달성 가능한가** — 2-6 실측
   검증에서 숫자로 확인. 오차가 크면 original fixture로 원인 구분(해상도 vs
   알고리즘). 다중 프레임(2-7) 적용 후 최종 판단.
   개선 옵션(기준 미달 시 협의): ① 다중 프레임 중앙값(2-7 계획분)
   ② 캡처 1080→1920px 상향(CapturedImage 계약+CLAUDE.md 변경 필요)
   ③ 스트림 4K 요청(지원 기기 한정).
   → **종결(2026-07-16)**: 답은 "단일 마커 단독으로는 불가"(24번에서 실증).
   방침 전환으로 절대 정확도 자체가 Gate에서 제외됨(26번).
16. **남은 정리**: 카드 사진(person01_card.jpg, 1206px)도 2-6 간편 모드 검증
   전까지 원본 확보 → 1080px+원본 2종으로 정리할 것.
17. ★ **현행 Claude 모델은 temperature 파라미터 미지원** (Opus 4.7 이후 제거,
   보내면 400 — 실제 겪음). 편차 억제는 결정적 프롬프트 + 다중 프레임
   중앙값(2-7)이 담당. CLAUDE.md 그룹 B-6도 이에 맞게 갱신됨 (2026-07-15).
18. ★ **메모장으로 .env 저장 시 UTF-8 BOM이 붙어 키 로드 실패** → 로더를
   utf-8-sig로 처리해 해결 (claude_vision.py `_load_api_key`).
19. **사용 모델: claude-opus-4-8** — 부위 인식 품질이 측정 정확도를 좌우하므로
   상위 모델 사용. 환경변수 FITME_VISION_MODEL로 교체 가능.
20. **좌표 결과는 fixtures/person01_aruco.landmarks.json에 캐시** — CLI 재실행
   시 추가 API 호출 없음 (`--fresh` 옵션으로만 재호출). 개발 중 비용 절약 패턴.
21. ★ **2-6 검증 기준: 옷 입은 상태로 통일** (앱·줄자 동일 조건 — 줄자 실측도
   사진 촬영 시와 동일한 옷·자세로 잰다). 앱도 옷을 재고 줄자도 옷을 재면,
   오차 발생 시 "알고리즘 문제 vs 옷 두께 문제"의 혼동 없이 **알고리즘
   정밀도만 분리 검증**할 수 있음. 미결 질문 15번(1080px에서 ±3cm 가능한가)은
   척도·좌표 정밀도 문제이므로 옷 변수를 섞으면 답이 나오지 않음 (왜곡 4대
   요인 중 ④ 자세·의류에 대한 Gate 방침 결정, 2026-07-15).
22. ★ **미해결 과제 — 의류 두께 보정**: 실제 서비스에서는 "옷 위 측정값 →
   실제 몸 치수" 보정이 필요. 후보 방안: ① 밀착 의류 촬영 안내(전략 1)
   ② 의류 종류별 통계 보정 ③ AI 몸 윤곽 추정 ④ Phase 4 핏 예측에서
   상쇄(측정·사이즈표 기준만 일관되면 실용적). **Phase 4 설계 시 결정할 것.**
23. **person01_truth.json은 "옷 입은 상태 실측값"임을 파일에 명시할 것**
   (fixtures/README.md 템플릿에 반영됨).
24. ★ **2-6 실측 비교 결과: 0/7 통과 (미결 질문 15번의 답)** — 병목은 해상도가
   아니라 구조적 원인 3가지: ① 호모그래피 원거리 외삽 불안정(같은 사진·같은
   랜드마크인데 1080px 키 175.9 vs 원본 160.3 — 15.6cm 요동. 마커 코너
   서브픽셀 노이즈가 1300px 외삽에서 ±10%로 증폭. 마커 근처 측정은 두 해상도
   일치 = 거리가 문제) ② 의류 왜곡(헐렁한 반바지의 옷 가랑이를 crotch로 짚음
   → 다리안쪽 −27cm) ③ 측정 정의 차이(줄자 곡면 vs 직선 투영 — 어깨 −22%,
   둘레 일관 −10~−16%는 systematic이라 계수로 보정 가능).
25. ★ **2-6 대응 계획 확정 (2026-07-16 사용자 결정, CLAUDE.md 반영됨)**:
   ① 카메라 UI에 밀착 의류 안내 문구(전략 1 → 2-8에서 구현)
   ② 2-7 다중 프레임 중앙값 먼저(원인 1 완화)
   ③ 키·몸무게 입력(UserProfile 타입 신설 — 키 캘리브레이션 + BMI 둘레 보정, 2-7b)
   ④ 정의 보정 계수(2-7b, 3명 검증 필수).
   재검증은 밀착 의류 재촬영 사진으로 2-7b에서. 기존 반바지 사진은
   "가이드 무시 사용자" 엣지 케이스 자료로 보존.
   (→ 26번에서 일부 조정: 재촬영 보류, 절대 정확도 Gate 제외,
   계수는 "3명 검증"이 아닌 person01 1명 역산으로 변경)
26. ★ **Gate 기준 전환 (2026-07-16 사용자 결정, CLAUDE.md 13-2 재작성)**:
   Phase 2 통과 기준을 절대 정확도(±3cm/±5cm, 3명 검증)에서 **일관성(동일
   사진 반복 측정 편차 2cm 이내)**으로 전환. 절대 정확도는 12장 "알려진
   한계" + 향후 과제로 이월. **이유 4가지**: ① 추가 피험자 확보 불가(표본
   1명), 재촬영도 보류 ② Phase 3~5가 통째로 남은 상태에서 정확도에만
   매달리면 전체 지연 ③ 문헌 계수 인용 배제 — 우리 조건(마커 기반·옷 위·
   정면 너비→둘레)에 맞는 연구가 사실상 없고, 어정쩡한 인용은 "검증된 척"
   착각(규칙 1 위반 소지) ④ 편향이 일정하면 Phase 4 핏 예측 성립 — 실질
   검증은 Phase 4 수동 검증(아는 옷 대조)이 담당. 계수는 person01 1명
   역산값 사용. 옷에 따라 변하는 편향(crotch 등)은 계수로 보정 불가 —
   밀착 의류 안내로만 완화(12장 한계 명시).
   (→ 27번에서 일부 조정: person01은 보정 기준이 아님 — 계수 역산은
   밀착 옷 기준 데이터 확보 후로 변경)
27. ★ **촬영 가이드를 제품 핵심 기능으로 격상 (2026-07-16 사용자 결정,
   CLAUDE.md 전략 1 하위 "4층위" 명세)**: 밀착 옷 재촬영을 시도해 보니
   **가이드 없이 정확한 사진을 찍는 것 자체가 어렵다**는 것이 확인됨.
   추가로 원근 왜곡(머리 확대, 한쪽 몸 부각, 광각 가장자리 늘어남)을 인식 —
   호모그래피는 마커 평면만 보정하므로 몸 전체 원근은 예방·감지로만 대응
   가능. 4층위: ①정적 안내 ②실시간 오버레이 ③실시간 검증+자동 촬영
   (/check-photo, 2-7c) ④촬영 후 피드백(대칭성 검사). UI는 2-8.
   person01 데이터 역할 재정의: 보정 기준 아님, 파이프라인 확인+엣지 케이스용.
28. ★ **v2(밀착 옷) 재검증 결과 (2026-07-16, 신규 API 13회)**:
   **[실측값 변화]** 둘레 3종 거의 불변(가슴 100→100, 허리 99→100, 엉덩이
   101→100) → 헐렁한 옷도 둘레 "실측"에는 영향 적음. 길이 2종 변화: 팔길이
   52→58(이전 기준점 오류), 다리안쪽 72→75(드로즈로 사타구니 기준점 명확).
   **[절대 오차 — 대폭 개선]** 키 +3.9→-0.8cm, 다리안쪽 -27.4→-14.7cm
   (12.7cm 개선 — "반바지가 사타구니를 가려 AI가 오인" 가설 확인), 팔길이
   +4.9→+1.1cm, 어깨 -10.4→-7.4cm(곡면vs직선 정의 차이 잔존), 둘레 -6~-13cm
   (계수 미보정 상태라 예상 범위).
   **[편차 — 악화, 원인 규명]** Gate 4/8 (v1 사진은 7/8). 원인: **마커가
   42px**(v1 59.9px, 임계 40 아슬아슬 통과)로 척도가 1.66mm/px(v1 1.17) —
   같은 px 노이즈가 1.42배의 cm 노이즈로 증폭. 몸도 프레임에서 작음.
   → **마커 크기가 편차의 지배 변수**임이 실증됨. 층위 3 임계(40px) 상향
   (50~60px) 또는 "더 가까이" 안내 강화 검토 필요.
   **[허리/옵션 A]** 3.5→2.2cm 개선됐지만 기준(2.0) 초과 → 규칙상 "진행
   필요" 판정. 단 마커 크기 교란 변수가 있어(42px 사진), 마커 60px+ 조건
   재확인 후 결정해도 됨 — 사용자 결정 대기.
   **[품질 게이트 실전]** /check-photo: ready 판정(비율 1.0014 — 광각 우려
   무혐의), 대칭성 경고 없음(치우침 우려도 무혐의). 판정 자체는 유효했으나
   "42px 통과"가 결과적으로 관대했음 — 위 임계 상향 근거.
29. ★ **v3 재검증 — 척도 체계의 구조적 결론 (2026-07-16, 신규 API 13회)**:
   **[호모그래피 외삽 폐기 실증]** v3는 마커 윗변이 아랫변보다 2px 긴
   사다리꼴로 검출 → 원근 성분 폭주로 키 219.5cm(+70.8cm). 진단 결과
   v1의 "정확해 보였던 키 176"도 +22.9cm 부풀림이 우연히 참값 근처에
   떨어진 운이었음 (v2만 코너 완벽 → 호모그래피=스칼라). **원거리 측정은
   스칼라 척도(mmPerPx)로 전환 필요, 호모그래피는 마커 근방 전용.**
   **[깊이 편향 발견]** 스칼라 기준 키 오차: v1 -18.9 / v2 **-1.0** / v3
   -23.5cm. head-heel/마커 비율(참값 24.6): v2 24.5(일치), v1 21.8, v3 21.1
   — **가까이 찍을수록(마커 크게) 가슴 평면이 머리·발보다 카메라에 가까워
   축소 편향 증가.** "마커를 크게" 요구와 기하 정확도는 트레이드오프 —
   해결책은 더 가까운 촬영이 아니라 **큰 마커 출력(7→10cm) 또는 키
   캘리브레이션(2-7b)**. 임계 60px 상향은 유지하되 충족 수단을 재고할 것.
   **[옵션 A 확정]** 허리 편차(스칼라, 7프레임): v1 3.28 / v2 2.14 / v3
   3.53cm — 옷(헐렁/밀착)·마커 크기(42~60px)·거리 모두 바꿔도 일관 초과.
   교란 변수 제거 완료 → **"정의 모호"가 실제 원인. 옵션 A 진행 확정.**
   **[v1/v2/v3 역할 확정]** v1(헐렁+중간 거리)=의류 왜곡 엣지 케이스(crotch
   -27cm 실증) / **v2(밀착+원거리)=기하학적 최적 기준 데이터** (2-7b 키
   캘리브레이션 검증의 1차 기준, 단 마커 42px 노이즈 유의) / v3(밀착+근거리)
   =호모그래피 폭주·깊이 편향 실증용 엣지 케이스. 총 39회분 랜드마크 캐시
   보유(사진당 13회) — 향후 알고리즘 변경 검증에 API 비용 0으로 재사용 가능.
30. ★ **2-7b 검증에서 배운 것 (2026-07-16, 신규 API 0)**:
   **[A안 확정 근거]** "폭은 마커 평면이라 마커 척도가 정확"이라는 이론(B안)이
   데이터에서 기각됨 — 마커 검출 노이즈(42~60px)가 사진 간 폭을 2~5cm 흔들고,
   어깨는 실제로 마커(가슴 부착)보다 뒤 평면에 있음. 키 척도가 폭도 더 일관됨.
   **[잔존 둘레 오차의 정체]** v1/v3 가슴 +4~5cm는 깊이 편향(r=1.12/1.16)이
   폭을 그 비율만큼 부풀린 것과 정확히 일치 — 즉 계수 문제가 아니라 촬영 거리
   문제이며, r 판정(depth_bias 경고)이 정확히 그 사진들을 짚음. **촬영 가이드
   조건(r≈1, v2)에서는 계수가 유효.** 허리 v3 +9.5는 허리 폭 자체의 정의
   불안정(31.5→34.4) — 옵션 A 후 waist 깊이 계수(1.024로 이례적으로 큼 — 폭
   과소의 흡수값 의심) 재역산 검토.
   **[반복 편차의 지배 변수 재해석]** A안에서는 마커 크기가 측정 척도와 무관해짐
   → v2 편차 4/8의 원인은 마커 42px가 아니라 **몸이 프레임에 작게 잡힌 것**
   (mm/px가 커서 같은 랜드마크 px 노이즈가 큰 cm로 증폭). 층위 3 가이드는
   "마커 크게"보다 **"전신을 프레임에 꽉 차게"**가 본질 (마커 임계는 검출·검증
   품질용으로 유지).
   **[마커의 새 역할]** 주 척도 → 심판: 키 입력 오류의 유일한 독립 검증(r>20%
   suspect → 전 항목 강등) + 품질 게이트(/check-photo) + 기울기 판정. 마커 없인
   키 오타를 잡을 방법이 없으므로 마커는 계속 필수.
   **[기록 각주]** v1 팔길이 오차 +8.7은 v1 truth의 기준점 오류값(52) 대비 —
   정확값(58, truth_v2) 기준이면 +2.7. inseam -14~-37 systematic(crotch
   랜드마크가 실제 사타구니보다 아래) — 어깨형 정의 계수 후보로 기록만
   (이번 범위 밖, 계수화는 표본 추가 후 검토).
31. ★ **옵션 A(허리 기하 정의) 검증 — 가설 기각 (2026-07-16, 신규 API 39회)**:
   **[최종 비교표 — 허리 7프레임 편차 cm (시간순 롤링, 현행 계수 기준 동일 환산)]**
   | 사진 | 구정의(natural waist) | 신정의(기하 중간점) | 폭px 산포 구→신 |
   |------|----:|----:|----:|
   | v1 | 4.09 | 4.88 | 10.0→12.0 |
   | v2 | 2.39 | **4.32** | 4.6→8.3 |
   | v3 | 4.54 | 4.45 | 10.2→10.0 |
   → 세 사진 모두 기준(2cm) 미달, v2는 오히려 악화. **"정의 모호가 원인"
   가설(29번) 기각.**
   **[재규명된 원인 2가지]** ① 실루엣 가장자리 x 추정 자체의 노이즈 — 새 정의가
   y(높이)는 완벽히 고정했는데(중간점 이탈 v2 ≤5px) 폭 산포는 그대로임 ②
   기하 중간점은 chest/hip **레벨 추정 노이즈를 상속**(hip y가 런 간 40~80px
   요동 → 허리 레벨도 요동) — natural waist(배꼽)라는 시각적 앵커를 잃음.
   **[더 큰 발견 — 배치 간 드리프트]** 정의를 안 바꾼 가슴도 v2에서 구배치
   산포 0.3cm → 신배치 5.6cm. 같은 사진·같은 정의라도 **랜드마크 추출 배치가
   달라지면 둘레 폭 항목의 산포 수준 자체가 변동**함이 실증됨 — 구배치의
   "가슴 0.3cm"는 운이었고, 둘레 폭 ±2cm 일관성은 현 방식(비전 모델 실루엣
   가장자리)의 구조적 한계일 가능성. 길이 항목(키·다리·상체)은 양 배치 모두
   안정 — 관절·정점 앵커는 강건, "옷 위 가장자리"만 취약.
   **[부수 발견]** 신정의 허리 폭은 3~4cm 넓음(중간점이 배꼽보다 배 쪽) →
   역산 시 waist 깊이 계수 0.777로 정상화(기존 1.024 이상치는 natural waist
   폭 과소의 흡수값이었음이 확인). 단 편차 미달이라 재역산은 정의 확정 후.
   **[기록]** 신정의 캐시 39런 = fixtures 현행, 구정의 캐시 39런 =
   `archive_predefA/` 보관 (양 배치 모두 재사용 가능 자산).
32. ★ **옵션 B 채택 + 후속 처리 (2026-07-16 사용자 결정, API 0)**:
   **[결정]** ① 둘레 3종(가슴·허리·엉덩이) 전부를 알려진 한계로 문서화
   (CLAUDE.md 12장 — 원인·실증 근거·완화 후보 3종 포함) ② Gate 일관성 기준을
   길이 항목+어깨로 조정(13-2, 9장 자동·수동·하단 주의문) ③ 허리 프롬프트는
   신정의(기하 중간점) 확정 — 계수 정상화 + 정의 논란 종결.
   **[허리 계수 재역산]** 신정의 v2 캐시 기준 d=0.7773 → base 0.7273
   (BMI 가감 제외). 결과: 허리 절대 오차 +13.9/+13.9/+17.9 → **+0.2/0.0/+3.5cm**
   (v1/v3 전이도 양호 — 신정의가 옷·거리에 강건함을 시사).
   **[계수 배치 드리프트 기록]** 신정의 배치로 전체 재역산 시 어깨 1.1843 /
   chest 0.7591 / hip 0.7780 (현행: 1.1823/0.7681/0.8331 — 구배치 유지).
   이 차이(둘레 환산 1~3cm)가 표본 1명 계수의 실제 불확실성 규모다. 유지 이유:
   승인 범위(허리만) + 배치마다 계수를 갈면 끝이 없음 — 다인 검증 시 일괄 재산정.
   **[조정된 기준 하의 현재 상태 — 정직 기록]** 길이+어깨 5항목 편차:
   v2(기준 조건) **5/5 통과** (0.3/0.3/0.3/0.2/0.8). v1은 팔길이 5.3cm 초과
   — 신배치에서 손목 y가 50px 요동(헐렁한 소매가 손목을 가리는 v1 옷 조건
   추정, 엣지 케이스 성격과 일치). v3는 다리안쪽 2.3/상체 2.1cm 소폭 초과
   (근거리 왜곡 엣지). **촬영 가이드 준수 조건(v2)에서는 신기준 전 항목
   통과** — Gate 수동 검증은 가이드 준수 촬영으로 수행하므로 성립.

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
