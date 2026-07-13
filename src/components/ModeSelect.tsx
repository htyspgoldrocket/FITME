import type { MeasurementMode } from '../types';

interface ModeSelectProps {
  onSelect: (mode: MeasurementMode) => void;
}

/** 측정 모드 선택 화면 — 간편(신용카드) / 정밀(ArUco 마커) */
function ModeSelect({ onSelect }: ModeSelectProps) {
  return (
    <div className="mode-select">
      <header className="mode-select__header">
        <h1>FITME</h1>
        <p>측정 모드를 선택하세요</p>
      </header>

      <button
        type="button"
        className="mode-card mode-card--simple"
        onClick={() => onSelect('simple')}
      >
        <span className="mode-card__badge">🟢 간편 모드</span>
        <strong>신용카드 기준</strong>
        <ul>
          <li>지갑 속 카드 한 장이면 준비 끝</li>
          <li>카드를 측정 부위 정면에 대고 촬영</li>
          <li>정확도: 중상</li>
        </ul>
      </button>

      <button
        type="button"
        className="mode-card mode-card--precise"
        onClick={() => onSelect('precise')}
      >
        <span className="mode-card__badge">🔵 정밀 모드</span>
        <strong>ArUco 마커 기준</strong>
        <ul>
          <li>앱 제공 마커를 프린터로 출력(100% 배율)</li>
          <li>마커를 부위 정면에 대고 촬영</li>
          <li>정확도: 최고</li>
        </ul>
      </button>
    </div>
  );
}

export default ModeSelect;
