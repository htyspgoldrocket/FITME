import { useState } from 'react';
import type { UserProfile } from '../types';

interface ProfileInputProps {
  /** 재진입 시 이전 입력 유지 — 값은 App이 보관한다 */
  initial: UserProfile | null;
  onSubmit: (profile: UserProfile) => void;
  onBack: () => void;
}

// 입력 하드 한계 — 단위 혼동·오타만 차단한다 (측정 상식 범위 검사는 백엔드 몫).
// 키 오타의 정밀 검증은 마커 교차 검증(r 판정, 2-7b)이 담당.
const HEIGHT_MIN = 100;
const HEIGHT_MAX = 250;
const WEIGHT_MIN = 20;
const WEIGHT_MAX = 300;

function parseInput(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === '') return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : NaN;
}

/** 키·몸무게 입력 화면 (2-8b) — 키는 척도 캘리브레이션 기준(필수), 몸무게는 둘레 보정(선택) */
function ProfileInput({ initial, onSubmit, onBack }: ProfileInputProps) {
  const [heightStr, setHeightStr] = useState(initial ? String(initial.heightCm) : '');
  const [weightStr, setWeightStr] = useState(
    initial?.weightKg !== undefined ? String(initial.weightKg) : '',
  );

  const height = parseInput(heightStr);
  const weight = parseInput(weightStr);

  const heightError =
    height !== null && !(height >= HEIGHT_MIN && height <= HEIGHT_MAX)
      ? `키는 ${HEIGHT_MIN}~${HEIGHT_MAX}cm 범위로 입력해 주세요`
      : null;
  const weightError =
    weight !== null && !(weight >= WEIGHT_MIN && weight <= WEIGHT_MAX)
      ? `몸무게는 ${WEIGHT_MIN}~${WEIGHT_MAX}kg 범위로 입력해 주세요`
      : null;

  const canSubmit = height !== null && heightError === null && weightError === null;

  const handleSubmit = () => {
    if (!canSubmit || height === null) return;
    onSubmit({ heightCm: height, ...(weight !== null ? { weightKg: weight } : {}) });
  };

  return (
    <div className="profile">
      <header className="profile__header">
        <h1>신체 정보 입력</h1>
        <p>정확한 측정을 위해 키가 필요해요</p>
      </header>

      <label className="profile__field">
        <span className="profile__label">
          키 (cm) <em className="profile__required">필수</em>
        </span>
        <input
          type="number"
          inputMode="decimal"
          placeholder="예: 172"
          value={heightStr}
          onChange={(e) => setHeightStr(e.target.value)}
          autoFocus
        />
        <span className={heightError ? 'profile__hint profile__hint--error' : 'profile__hint'}>
          {heightError ?? '전체 측정의 척도 기준으로 사용됩니다 — 정확할수록 결과가 정확해요'}
        </span>
      </label>

      <label className="profile__field">
        <span className="profile__label">
          몸무게 (kg) <em className="profile__optional">선택</em>
        </span>
        <input
          type="number"
          inputMode="decimal"
          placeholder="예: 68"
          value={weightStr}
          onChange={(e) => setWeightStr(e.target.value)}
        />
        <span className={weightError ? 'profile__hint profile__hint--error' : 'profile__hint'}>
          {weightError ?? '입력하면 가슴·허리·엉덩이 둘레 추정이 체형에 맞게 보정됩니다'}
        </span>
      </label>

      <div className="profile__actions">
        <button type="button" className="profile__btn" onClick={onBack}>
          뒤로
        </button>
        <button
          type="button"
          className="profile__btn profile__btn--primary"
          disabled={!canSubmit}
          onClick={handleSubmit}
        >
          다음 (촬영하기)
        </button>
      </div>
    </div>
  );
}

export default ProfileInput;
