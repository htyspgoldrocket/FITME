import { useEffect, useState } from 'react';
import { calculateFit, synthesizeImage } from '../lib/api';
import FitHeatmap from './FitHeatmap';
import type {
  AnalyzeResponse,
  BodyMeasurements,
  CapturedImage,
  ClothingSpec,
  FitResponse,
  SynthesizeResponse,
} from '../types';

interface FitResultViewProps {
  image: CapturedImage;
  measurements: BodyMeasurements;
  /** 히트맵 오버레이 위치 계산용 (5-3d) — 없으면(오래된 캐시 등) 일반 이미지로 폴백 */
  landmarks: AnalyzeResponse['landmarks'];
  spec: ClothingSpec;
  /** 같은 입력의 이전 핏 결과 (App 보관) — 뒤로가기 재진입 시 재요청(AI 1회) 방지 */
  cached: FitResponse | null;
  onLoaded: (response: FitResponse) => void;
  /** 같은 입력의 이전 합성 결과 (App 보관) — 뒤로가기 재진입 시 재요청(VTON 1회) 방지 */
  synthCached: SynthesizeResponse | null;
  onSynthesized: (response: SynthesizeResponse) => void;
  onBack: () => void;
  onRestart: () => void;
}

const PART_LABEL: Record<string, string> = {
  chest: '가슴',
  waist: '허리',
  hip: '엉덩이',
  shoulder: '어깨',
};

const STATUS_LABEL: Record<string, string> = {
  tight: '타이트',
  good: '잘 맞음',
  loose: '여유',
};

const CONFIDENCE_LABEL: Record<string, string> = {
  high: '높음',
  medium: '중간',
  low: '낮음',
};

type State =
  | { status: 'loading' }
  | { status: 'done'; response: FitResponse }
  | { status: 'error'; message: string };

type SynthState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; response: SynthesizeResponse }
  | { status: 'error'; message: string };

/** 핏 결과 화면 (4-4b) — /fit 호출·로딩·실패·결과 표시를 담당 */
function FitResultView({
  image,
  measurements,
  landmarks,
  spec,
  cached,
  onLoaded,
  synthCached,
  onSynthesized,
  onBack,
  onRestart,
}: FitResultViewProps) {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0); // "다시 시도" 시 증가 → 재호출

  // 5-3c: 가상 착용 합성 — 버튼을 눌러야 시작 (fit과 달리 자동 호출 아님, 비용 절약)
  const [synthState, setSynthState] = useState<SynthState>(
    synthCached !== null ? { status: 'done', response: synthCached } : { status: 'idle' },
  );

  const runSynthesis = () => {
    setSynthState({ status: 'loading' });
    synthesizeImage(image, spec)
      .then((response) => {
        setSynthState({ status: 'done', response });
        if (response.ok) onSynthesized(response);
      })
      .catch((e) => {
        setSynthState({
          status: 'error',
          message: e instanceof Error ? e.message : String(e),
        });
      });
  };

  // cached·onLoaded는 의존성에서 의도적으로 제외 — 캐시는 마운트 직후(attempt=0)
  // 판단 전용이고, onLoaded로 캐시가 갱신될 때 재실행되면 무한 루프가 된다
  // (MeasureResult·ClothingSpecView와 동일 패턴)
  useEffect(() => {
    if (attempt === 0 && cached !== null) {
      setState({ status: 'done', response: cached });
      return undefined;
    }
    let cancelled = false;
    setState({ status: 'loading' });
    calculateFit(measurements, spec)
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
  }, [measurements, spec, attempt]);

  if (state.status === 'loading') {
    return (
      <div className="result result--center fit">
        <div className="result__spinner" aria-hidden="true" />
        <h2>핏을 분석하고 있어요</h2>
        <p className="result__note">치수 비교와 추천문 생성에 몇 초 걸려요</p>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="result result--center fit">
        <h2>핏 분석 요청에 실패했어요</h2>
        <p className="result__note">{state.message}</p>
        <div className="result__actions">
          <button type="button" className="result__btn" onClick={onBack}>
            의류 정보로
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

  // ok=false — 비교 가능한 실측이 없는 사이즈표 등: 서버의 한국어 사유 그대로
  if (!response.ok || !response.result) {
    return (
      <div className="result result--center fit">
        <h2>핏을 판정하지 못했어요</h2>
        <p className="result__note">{response.error ?? '알 수 없는 오류'}</p>
        <div className="result__actions">
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={onBack}
          >
            의류 정보로
          </button>
        </div>
      </div>
    );
  }

  const { result } = response;

  return (
    <div className="result fit">
      <header className="result__header">
        <h2>핏 분석 결과</h2>
        <p className="result__note">
          {result.clothing.brand}
          {result.clothing.productName ? ` · ${result.clothing.productName}` : ''}
        </p>
      </header>

      <div className="fit__recommend">
        <span className="fit__recommend-label">추천 사이즈</span>
        <strong className="fit__recommend-size">{result.recommendedSize}</strong>
      </div>

      <table className="result__table">
        <tbody>
          {result.scores.map((s) => (
            <tr key={s.part}>
              <th scope="row">{PART_LABEL[s.part] ?? s.part}</th>
              <td>
                <span className={`fit__status fit__status--${s.status}`}>
                  {STATUS_LABEL[s.status] ?? s.status}
                </span>
              </td>
              <td className="result__value">
                {s.diff_cm > 0 ? '+' : ''}
                {s.diff_cm.toFixed(1)} cm
              </td>
              <td>
                {s.confidence && (
                  <span className={`result__conf result__conf--${s.confidence}`}>
                    {CONFIDENCE_LABEL[s.confidence] ?? s.confidence}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="fit__recommendation">{result.recommendation}</p>

      {response.warnings.length > 0 && (
        <details className="result__warnings" open>
          <summary>주의 사항 {response.warnings.length}건</summary>
          <ul>
            {response.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="fit__synth">
        <h3>가상 착용 보기</h3>

        {synthState.status === 'idle' && (
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={runSynthesis}
          >
            가상 착용 이미지 생성
          </button>
        )}

        {synthState.status === 'loading' && (
          <p className="result__note">합성 중이에요 — 최대 1분 정도 걸릴 수 있어요</p>
        )}

        {synthState.status === 'error' && (
          <>
            <p className="result__note">합성 요청에 실패했어요: {synthState.message}</p>
            <button type="button" className="result__btn" onClick={runSynthesis}>
              다시 시도
            </button>
          </>
        )}

        {synthState.status === 'done' && !synthState.response.ok && (
          <>
            <p className="result__note">
              {synthState.response.error ?? '합성하지 못했어요'}
            </p>
            <button type="button" className="result__btn" onClick={runSynthesis}>
              다시 시도
            </button>
          </>
        )}

        {synthState.status === 'done' &&
          synthState.response.ok &&
          synthState.response.imageBase64 &&
          (landmarks ? (
            <FitHeatmap
              imageBase64={synthState.response.imageBase64}
              originalImage={image}
              landmarks={landmarks}
              scores={result.scores}
            />
          ) : (
            <img
              src={`data:image/jpeg;base64,${synthState.response.imageBase64}`}
              alt="가상 착용 이미지"
              className="fit__synth-img"
            />
          ))}

        {synthState.status === 'done' && synthState.response.ok && synthState.response.imageBase64 && (
          <p className="result__note">
            {landmarks
              ? '색상 밴드는 대략적 위치 안내예요 — 실제 핏은 라벨의 cm 수치를 기준으로 봐주세요'
              : '합성 이미지는 외관 참고용이에요 — 실제 핏은 위 표의 수치를 기준으로 봐주세요'}
          </p>
        )}
      </div>

      <div className="result__actions">
        <button type="button" className="result__btn" onClick={onBack}>
          의류 정보로
        </button>
        <button type="button" className="result__btn" onClick={onRestart}>
          처음으로
        </button>
      </div>
    </div>
  );
}

export default FitResultView;
