import { useEffect, useState } from 'react';
import { fetchBetaStatus, getBetaCode, saveBetaCode } from '../lib/api';

interface BetaGateProps {
  onPass: () => void;
}

/**
 * 베타 게이트 (Phase 6-2b) — 배포 환경(서버에 FITME_BETA_CODE 설정)에서만
 * 초대 코드 입력 + 개인정보·비상업 고지를 띄운다.
 *
 * - 저장된 코드가 유효하면(재방문) 게이트 없이 통과
 * - 서버 확인이 실패하면(로컬 개발·서버 다운) 게이트 없이 진행(fail-open) —
 *   실제 강제는 백엔드 access_guard(6-1)가 AI 라우트에서 수행하므로
 *   게이트 우회로는 비용이 발생하지 않는다
 */
function BetaGate({ onPass }: BetaGateProps) {
  const [state, setState] = useState<'checking' | 'input' | 'submitting'>('checking');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await fetchBetaStatus(getBetaCode());
        if (cancelled) return;
        if (!status.active || status.codeOk) onPass();
        else setState('input');
      } catch {
        if (!cancelled) onPass();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onPass]);

  const submit = async () => {
    const entered = code.trim();
    if (!entered) return;
    setState('submitting');
    setError(null);
    try {
      const status = await fetchBetaStatus(entered);
      if (!status.active || status.codeOk) {
        saveBetaCode(entered);
        onPass();
        return;
      }
      setError('코드가 올바르지 않아요 — 초대 메시지의 코드를 확인해 주세요');
    } catch {
      setError('서버에 연결할 수 없어요 — 잠시 후 다시 시도해 주세요');
    }
    setState('input');
  };

  // 저장된 코드 확인 중 — 유효하면 이 화면은 스치듯 지나간다
  if (state === 'checking') {
    return (
      <div className="beta beta--center">
        <div className="result__spinner" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="beta">
      <h1 className="beta__title">FITME</h1>
      <p className="beta__badge">무료 베타 · 비상업 테스트 서비스</p>

      {/* 개인정보 고지 (6-2) — 사진 외부 전송을 시작 전에 알린다 */}
      <div className="beta__notice">
        <strong>시작 전에 알려드려요</strong>
        <ul>
          <li>
            촬영한 사진은 신체 치수 분석(Anthropic Claude API)과 가상 착용
            합성(Replicate)을 위해 외부 AI 서버로 전송돼요
          </li>
          <li>합성에 쓰인 사진과 결과는 1시간 후 자동 삭제돼요 (Replicate 정책)</li>
          <li>FITME 서버는 사진을 저장하지 않아요</li>
        </ul>
      </div>

      <label className="beta__label" htmlFor="beta-code">
        초대 코드
      </label>
      <input
        id="beta-code"
        className="beta__input"
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') void submit();
        }}
        placeholder="초대받은 코드를 입력하세요"
        autoComplete="off"
      />
      {error && <p className="beta__error">{error}</p>}
      <button
        type="button"
        className="beta__btn"
        disabled={state === 'submitting' || code.trim() === ''}
        onClick={() => void submit()}
      >
        동의하고 시작하기
      </button>
    </div>
  );
}

export default BetaGate;
