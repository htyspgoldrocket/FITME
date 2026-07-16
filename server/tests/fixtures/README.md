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

✅ 이 폴더의 사진·json은 .gitignore로 **로컬 전용**이다 (README.md만 커밋됨).
git에 올라가지 않으므로, PC를 옮기면 사진·실측값을 수동으로 복사해야 한다.
