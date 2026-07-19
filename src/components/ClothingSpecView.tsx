import { useEffect, useState } from 'react';
import { fetchClothingSpec } from '../lib/api';
import type { ClothingResponse, ClothingSize } from '../types';

interface ClothingSpecViewProps {
  url: string;
  /** 같은 URL의 이전 조회 결과 (App 보관) — 뒤로가기 재진입 시 재요청 방지 */
  cached: ClothingResponse | null;
  onLoaded: (response: ClothingResponse) => void;
  onEditUrl: () => void;
  onRestart: () => void;
  /** 핏 분석(4-4)으로 진행 — 측정 결과가 있을 때만 App이 전달 */
  onFit: (() => void) | null;
}

const CATEGORY_LABEL: Record<string, string> = {
  top: '상의',
  bottom: '하의',
  dress: '원피스',
  outer: '아우터',
};

/** 사이즈 표 컬럼 순서·한국어 라벨 (ClothingSize 선택 필드와 1:1) */
const PART_COLUMNS: [key: keyof ClothingSize, label: string][] = [
  ['chest_cm', '가슴둘레'],
  ['waist_cm', '허리둘레'],
  ['hip_cm', '엉덩이둘레'],
  ['shoulder_cm', '어깨너비'],
  ['sleeve_cm', '소매길이'],
  ['length_cm', '총장'],
  ['thigh_cm', '허벅지둘레'],
  ['rise_cm', '밑위'],
  ['hem_cm', '밑단둘레'],
];

type State =
  | { status: 'loading' }
  | { status: 'done'; response: ClothingResponse }
  | { status: 'error'; message: string };

/** 의류 정보 화면 (3-4b) — /clothing 호출·로딩·실패·스펙 표시를 담당 */
function ClothingSpecView({
  url,
  cached,
  onLoaded,
  onEditUrl,
  onRestart,
  onFit,
}: ClothingSpecViewProps) {
  const [state, setState] = useState<State>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0); // "다시 시도" 시 증가 → 재호출

  // cached·onLoaded는 의존성에서 의도적으로 제외 — 캐시는 마운트 직후(attempt=0)
  // 판단 전용이고, onLoaded로 캐시가 갱신될 때 재실행되면 무한 루프가 된다
  // (MeasureResult와 동일 패턴)
  useEffect(() => {
    if (attempt === 0 && cached !== null) {
      setState({ status: 'done', response: cached });
      return undefined;
    }
    let cancelled = false;
    setState({ status: 'loading' });
    fetchClothingSpec(url)
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
  }, [url, attempt]);

  if (state.status === 'loading') {
    return (
      <div className="result result--center clothing-spec">
        <div className="result__spinner" aria-hidden="true" />
        <h2>사이즈 정보를 가져오고 있어요</h2>
        <p className="result__note">첫 조회는 십수 초 정도 걸릴 수 있어요</p>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div className="result result--center clothing-spec">
        <h2>사이즈 조회 요청에 실패했어요</h2>
        <p className="result__note">{state.message}</p>
        <div className="result__actions">
          <button type="button" className="result__btn" onClick={onEditUrl}>
            주소 다시 입력
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

  // ok=false — 지원 외 쇼핑몰·없는 상품 등: 서버의 한국어 안내를 그대로 표시
  if (!response.ok || !response.spec) {
    return (
      <div className="result result--center clothing-spec">
        <h2>사이즈를 가져오지 못했어요</h2>
        <p className="result__note">{response.error ?? '알 수 없는 오류'}</p>
        <div className="result__actions">
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={onEditUrl}
          >
            주소 다시 입력
          </button>
        </div>
      </div>
    );
  }

  const spec = response.spec;
  // 값이 하나라도 있는 부위 컬럼만 표시 (없는 부위는 컬럼 자체를 안 만든다)
  const columns = PART_COLUMNS.filter(([key]) =>
    spec.sizes.some((s) => typeof s[key] === 'number'),
  );
  const hasEstimated = spec.sizes.some((s) => s.estimated);

  return (
    <div className="result clothing-spec">
      <header className="result__header">
        <h2>의류 정보</h2>
        <p className="result__note">
          {spec.brand}
          {spec.productName ? ` · ${spec.productName}` : ''} ·{' '}
          {CATEGORY_LABEL[spec.category] ?? spec.category}
        </p>
      </header>

      {columns.length > 0 && (
        <div className="spec__scroll">
          <table className="result__table spec__table">
            <thead>
              <tr>
                <th scope="col">사이즈</th>
                {columns.map(([key, label]) => (
                  <th scope="col" key={key}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {spec.sizes.map((s) => (
                <tr key={s.label}>
                  <th scope="row">
                    {s.label}
                    {s.estimated ? ' ≈' : ''}
                  </th>
                  {columns.map(([key]) => (
                    <td className="result__value" key={key}>
                      {typeof s[key] === 'number' ? `${s[key]}` : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="result__note">
        단위 cm · 단면 표기는 둘레(×2)로 환산된 값
        {hasEstimated ? ' · ≈ 표시는 실측이 아닌 호칭 기반 근사치' : ''}
      </p>

      {spec.needsUserInput && (
        <p className="result__note spec__needs-input">
          치수를 알 수 없는 사이즈가 있어요 — 핏 비교에 쓰려면 실측값 입력이
          필요합니다 (입력 기능은 Phase 4에서 제공)
        </p>
      )}

      {spec.warnings && spec.warnings.length > 0 && (
        <details className="result__warnings">
          <summary>주의 사항 {spec.warnings.length}건</summary>
          <ul>
            {spec.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="result__actions">
        <button type="button" className="result__btn" onClick={onEditUrl}>
          주소 다시 입력
        </button>
        <button type="button" className="result__btn" onClick={onRestart}>
          처음으로
        </button>
        {onFit && (
          <button
            type="button"
            className="result__btn result__btn--primary"
            onClick={onFit}
          >
            핏 분석 보기
          </button>
        )}
      </div>
    </div>
  );
}

export default ClothingSpecView;
