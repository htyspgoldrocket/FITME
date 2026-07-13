import { useState } from 'react';
import ModeSelect from './components/ModeSelect';
import type { MeasurementMode } from './types';

/** 앱 화면 단계 — Phase 1 범위: 모드 선택 → 카메라 → 미리보기 */
type Screen = 'mode-select' | 'camera' | 'preview';

function App() {
  const [screen, setScreen] = useState<Screen>('mode-select');
  const [mode, setMode] = useState<MeasurementMode | null>(null);

  const handleModeSelect = (selected: MeasurementMode) => {
    setMode(selected);
    setScreen('camera');
  };

  if (screen === 'mode-select') {
    return <ModeSelect onSelect={handleModeSelect} />;
  }

  // TODO(Phase 1-Step 5): 카메라 화면 구현. 지금은 자리표시자.
  return (
    <main className="placeholder">
      <p>
        선택한 모드: <strong>{mode === 'simple' ? '간편(카드)' : '정밀(ArUco)'}</strong>
      </p>
      <p>카메라 화면은 Step 1-5에서 구현됩니다.</p>
      <button type="button" onClick={() => setScreen('mode-select')}>
        모드 다시 선택
      </button>
    </main>
  );
}

export default App;
