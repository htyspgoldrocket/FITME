# 테스트 픽스처 — 샘플 사진 + 실측 정답값

Phase 2 검증용 테스트 세트를 이 폴더에 보관한다 (CLAUDE.md 13-2, 13-4).

## 필요한 것 (현재 표본: person01 1명 — 추가 표본은 향후 과제, CLAUDE.md 13-2)

각 사람(person01, person02, …)마다:

1. **사진**: 신용카드(또는 ArUco 마커)를 가슴 부근에 대고 찍은 **전신 사진**
   - 파일명 예: `person01_card.jpg` (간편 모드), `person01_aruco.jpg` (정밀 모드)
   - 촬영 조건: 정면, 약 2m 거리, 밝은 곳, 밀착 의류, 카드가 선명히 보일 것
2. **실측 정답값**: 줄자로 잰 값을 `person01_truth.json`으로 저장:

```json
{
  "name": "person01",
  "measured_over_clothes": true,
  "note": "사진 촬영 시와 동일한 옷·자세로 옷 위에서 줄자 실측 (2-6 Gate 방침)",
  "height": 175.0,
  "weight_kg": 70.0,
  "shoulder_width": 45.0,
  "chest_circumference": 96.0,
  "waist_circumference": 80.0,
  "hip_circumference": 95.0,
  "arm_length": 58.0,
  "inseam": 78.0,
  "torso_length": 62.0
}
```
(단위: cm. 잴 수 없는 항목은 해당 키를 빼면 됨 — 있는 항목만 비교한다.)

⚠️ **실측은 반드시 "사진 촬영 시와 동일한 옷을 입은 상태"에서 옷 위로 잰다.**
앱도 옷을 재고 줄자도 옷을 재야, 오차가 나왔을 때 알고리즘 정밀도만 분리
검증할 수 있다 (옷 두께 변수 제거 — PROGRESS.md 배운 것 21번 참조).
"옷 위 측정 → 실제 몸 치수" 보정은 Phase 4 설계 시 결정 (배운 것 22번).

## 용도

- Step 2-2~2-7 개발 중 검출·측정 테스트 입력
- Phase 2 Gate 수동 검증: 일관성 확인(동일 사진 반복 편차 2cm) + 실측 차이 참고
  기록 (절대 정확도 ±3cm/±5cm는 표본 확보 시 향후 과제 — CLAUDE.md 13-2)

## 다인(多人) 계수 검증 — 표본이 생기면 Phase 진행과 무관하게 언제든 (2-7b 후속)

새 대상 1명을 추가하는 절차 (`scripts/calibrate_multi.py`가 소비):

1. **촬영 — v2 조건 필수**: 밀착 의류 + 마커를 가슴에 평평하게 + 약 2m 정면
   전신 (`/check-photo` ready 판정 권장). 헐렁한 옷·근거리 사진은 계수를
   오염시키므로 등록 금지 (r 판정이 ok가 아니면 스크립트가 경고함)
2. **실측**: 위 템플릿대로 `personNN_truth.json` — 촬영과 동일한 옷 위 줄자
   실측 + `weight_kg`(BMI 보정 정합에 필요, 권장)
3. **랜드마크 캐시 수집**: `python scripts/calibrate_multi.py --collect 13`
   (⚠️ 캐시 없는 대상당 API 13회 호출 — 이후 재실행은 API 0)
4. **등록**: `calibration_set.json`의 `subjects`에 항목 추가 (photo/truth 파일명)
5. **실행**: `python scripts/calibrate_multi.py` → 대상별 역산 계수·사람 간
   산포·Leave-One-Out 오차(N≥2) 출력

계수 상수(measure.py `SHOULDER_CURVE_COEF`, `DEPTH_RATIOS`) 갱신은 **자동이
아니라 사용자 결정 후 수동**이며, 갱신 시 pytest + `verify_27b.py` 재실행.

✅ 이 폴더의 사진·json은 .gitignore로 **로컬 전용**이다 (README.md만 커밋됨).
git에 올라가지 않으므로, PC를 옮기면 사진·실측값을 수동으로 복사해야 한다.
