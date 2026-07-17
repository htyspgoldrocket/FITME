import { useEffect, useState } from 'react';
import { analyzeBody } from '../lib/api';
import type {
  AnalyzeResponse,
  CapturedImage,
  MeasurementMode,
  UserProfile,
} from '../types';

interface MeasureResultProps {
  image: CapturedImage;
  mode: MeasurementMode;
  profile: UserProfile | null;
  onRetake: () => void;
  onRestart: () => void;
}

/** 측정 항목 표시 순서·한국어 라벨 (BodyMeasurements 키와 1:1) */
const FIELD_LABELS: [key: string, label: string][] = [
  ['height', '키'],
  ['shoulder_width', '어깨 너비'],
  ['chest_circumference', '가슴둘레'],
  ['waist_circumference', '허리둘레'],
  ['hip_circumference', '엉덩이둘레'],
  ['arm_length', '팔 길이'],
  ['inseam', '다리 안쪽'],
  ['torso_length', '상체 길이'],
];

const CONFIDENCE_LABEL: Record<string, string> = {
  high: '높음',
  medium: '중간',
  low: '낮음',
};

type State =
  | { status: 'loading' }
  | { status: 'done'; response: AnalyzeResponse }
  | { status: 'error'; message: string };

/** 측정 결과 화면 (2-8e) — /analyze 호출·로딩·실패·결과 표시를 담당 */
function MeasureResult({ image, mode, profile, onRetake, onRestart }: MeasureResultProps) {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0); // "다시 시도" 시 증가 → 재호출

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });
    analyzeBody(image, mode, profile)
      .then((response) => {
        if (!cancelled) setState({ status: 'done', response });
      })
      .catch((e) => {
        if (!cancelled) {
          setState({
            status: 'error',
            message: e instanceof Error ? e.message : String(e),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [image, mode, profile, attempt]);

  if (state.status === 'loading') {
    const n = image.frames?.length ?? 1;
    return (
      <div className="result result--center">
        <div className="result__spinner" aria-hidden="true" />
        <h2>신체 치수를 측정하고 있어요</h2>
        <p className="result__note">
          사진 {n}장을 분석 중입니다 — 최대 2분 정도 걸릴 수 있어요
        </p>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="result result--center">
        <h2>측정 요청에 실패했어요</h2>
        <p className="result__note">{state.message}</p>
        <div className="result__actions">
          <button type="button" className="result__btn" onClick={onRetake}>
            다시 촬영
          </button>
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={() => setAttempt((a) => a + 1)}
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  const { response } = state;

  // ok=false — 기준물 미검출·좌표 추출 실패: 사유 + 재촬영 유도 (가짜 숫자 없음)
  if (!response.ok || !response.measurements) {
    return (
      <div className="result result--center">
        <h2>측정하지 못했어요</h2>
        <p className="result__note">{response.error ?? '알 수 없는 오류'}</p>
        <div className="result__actions">
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={onRetake}
          >
            다시 촬영
          </button>
        </div>
      </div>
    );
  }

  const m = response.measurements;
  const values = m as unknown as Record<string, number>;

  return (
    <div className="result">
      <header className="result__header">
        <h2>측정 결과</h2>
        <p className="result__note">
          {mode === 'simple' ? '🟢 간편 모드' : '🔵 정밀 모드'} · 프레임{' '}
          {response.stats?.runs ?? 1}장 중앙값
          {response.stats?.scale.source === 'height' ? ' · 키 기준 척도' : ''}
        </p>
      </header>

      <table className="result__table">
        <tbody>
          {FIELD_LABELS.map(([key, label]) => (
            <tr key={key}>
              <th scope="row">{label}</th>
              <td className="result__value">{values[key].toFixed(1)} cm</td>
              <td>
                <span className={`result__conf result__conf--${m.confidence[key]}`}>
                  {CONFIDENCE_LABEL[m.confidence[key]] ?? m.confidence[key]}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {response.warnings.length > 0 && (
        <details className="result__warnings">
          <summary>주의 사항 {response.warnings.length}건</summary>
          <ul>
            {response.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      <p className="result__note">의류 사이즈 비교는 다음 단계(Phase 3)에서 연결됩니다.</p>

      <div className="result__actions">
        <button type="button" className="result__btn" onClick={onRetake}>
          다시 촬영
        </button>
        <button type="button" className="result__btn" onClick={onRestart}>
          처음으로
        </button>
      </div>
    </div>
  );
}

export default MeasureResult;
