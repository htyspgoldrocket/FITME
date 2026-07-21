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
  /** 같은 사진의 이전 분석 결과 (3-1) — 의류 화면에서 뒤로 왔을 때 재분석(AI 7회) 방지 */
  cached: AnalyzeResponse | null;
  onLoaded: (response: AnalyzeResponse) => void;
  onRetake: () => void;
  onRestart: () => void;
  /** 측정 성공 시에만 노출 — 의류 URL 입력(3-1)으로 진행 */
  onNext: () => void;
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
function MeasureResult({
  image,
  mode,
  profile,
  cached,
  onLoaded,
  onRetake,
  onRestart,
  onNext,
}: MeasureResultProps) {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0); // "다시 시도" 시 증가 → 재호출

  // cached·onLoaded는 의존성에서 의도적으로 제외 — 캐시는 마운트 직후(attempt=0)
  // 판단 전용이고, onLoaded로 캐시가 갱신될 때 재실행되면 무한 루프가 된다
  useEffect(() => {
    if (attempt === 0 && cached !== null) {
      setState({ status: 'done', response: cached });
      return undefined;
    }
    let cancelled = false;
    setState({ status: 'loading' });
    analyzeBody(image, mode, profile)
      .then((response) => {
        if (!cancelled) {
          setState({ status: 'done', response });
          onLoaded(response);
        }
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

  // ok=false — 기준물 미검출·좌표 추출 실패: 사유 + 재촬영 유도 (가짜 숫자 없음).
  // 5-4 백로그 B-4 — 서버가 본 사진을 그대로 보여주고(검출됐다면 위치 표시),
  // 실패 단계에 맞는 원인 체크리스트를 붙인다. 1차 실기기에서 텍스트 사유만으로는
  // 무엇을 고쳐야 할지 알기 어려움(세로 카드·대비 부족)이 실증된 데 따른 개선.
  if (!response.ok || !response.measurements) {
    const refName = mode === 'simple' ? '카드' : '마커';
    const corners = response.reference.detected
      ? response.reference.cornersPx
      : undefined;
    const causes = !response.reference.detected
      ? mode === 'simple'
        ? [
            '카드가 세로 방향이면 인식되지 않아요 — 가로 방향으로 들어 주세요',
            '밝은 옷 위 밝은 카드는 대비가 부족해요 — 어두운 상의 위에 대 주세요',
            '카드 전체가 가려지지 않고 선명하게 보여야 해요',
          ]
        : [
            '마커가 접히거나 휘면 인식이 어려워요 — 평평하게 대 주세요',
            '마커 전체가 프레임 안에 선명하게 보여야 해요',
            '어두우면 인식률이 떨어져요 — 밝은 곳에서 찍어 주세요',
          ]
      : [
          `${refName}는 정상 검출됐어요(사진의 초록 테두리) — 신체 인식이 안 됐어요`,
          '전신(머리부터 발끝까지)이 프레임에 다 들어와야 해요',
          '주변이 어두우면 신체 인식이 어려워요 — 밝은 곳에서 찍어 주세요',
        ];
    // 검출 라벨 위치 — 기준물 좌상단 위쪽, 화면 밖으로 잘리지 않게 클램프
    const labelX = corners
      ? Math.min(Math.min(...corners.map(([x]) => x)), image.width - 330)
      : 0;
    const labelY = corners
      ? Math.max(Math.min(...corners.map(([, y]) => y)) - 20, 50)
      : 0;
    return (
      <div className="result result--center">
        <h2>측정하지 못했어요</h2>
        <p className="result__note">{response.error ?? '알 수 없는 오류'}</p>
        <div className="result__failure-photo">
          <img
            src={`data:${image.mimeType};base64,${image.base64}`}
            alt="측정에 사용된 사진"
          />
          {corners && (
            <svg viewBox={`0 0 ${image.width} ${image.height}`} aria-hidden="true">
              <polygon points={corners.map(([x, y]) => `${x},${y}`).join(' ')} />
              <text x={labelX} y={labelY}>✓ {refName} 검출됨</text>
            </svg>
          )}
        </div>
        <ul className="result__causes">
          {causes.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
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

  // 층위 4 (2-8f) — 촬영 후 피드백: 측정은 됐지만 품질 신호가 나쁘면
  // 구체 사유와 함께 재촬영을 권고한다 (경고 문구 접두어는 백엔드 계약:
  // check_symmetry "좌우 …", check_scale_agreement level "suspect")
  const lowCount = FIELD_LABELS.filter(([key]) => m.confidence[key] === 'low').length;
  const retakeReasons: string[] = [];
  if (response.warnings.some((w) => w.startsWith('좌우'))) {
    retakeReasons.push(
      '몸이 좌우 비대칭으로 찍혔어요 — 정면을 보고 몸을 화면 정중앙에 맞춰 주세요',
    );
  }
  if (response.stats?.scale.agreementLevel === 'suspect') {
    retakeReasons.push(
      '키 입력값과 기준물 크기가 크게 어긋나요 — 키 입력값과 마커 100% 배율 출력을 확인해 주세요',
    );
  }
  if (lowCount >= 3) {
    retakeReasons.push(
      `신뢰도가 낮은 항목이 ${lowCount}개예요 — 촬영 가이드(❓)를 지켜 다시 찍으면 좋아져요`,
    );
  }

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

      {retakeReasons.length > 0 && (
        <div className="result__retake">
          <strong>📸 재촬영을 권장해요</strong>
          <ul>
            {retakeReasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={onRetake}
          >
            다시 촬영하기
          </button>
        </div>
      )}

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
        <details className="result__warnings" open={retakeReasons.length > 0}>
          <summary>주의 사항 {response.warnings.length}건</summary>
          <ul>
            {response.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="result__actions">
        <button type="button" className="result__btn" onClick={onRetake}>
          다시 촬영
        </button>
        <button type="button" className="result__btn" onClick={onRestart}>
          처음으로
        </button>
        <button
          type="button"
          className="result__btn result__btn--primary"
          onClick={onNext}
        >
          의류 사이즈 비교
        </button>
      </div>
    </div>
  );
}

export default MeasureResult;
