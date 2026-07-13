import { useState } from 'react';
import ModeSelect from './components/ModeSelect';
import CameraView from './components/CameraView';
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

  // TODO(Phase 1-Step 6): 캡처 → CapturedImage 생성 → 미리보기 화면
  const handleShutter = (_video: HTMLVideoElement) => {
    alert('촬영 캡처는 Step 1-6에서 구현됩니다.');
  };

  if (screen === 'mode-select' || mode === null) {
    return <ModeSelect onSelect={handleModeSelect} />;
  }

  if (screen === 'camera') {
    return (
      <CameraView
        mode={mode}
        onBack={() => setScreen('mode-select')}
        onShutter={handleShutter}
      />
    );
  }

  // TODO(Phase 1-Step 6): 미리보기(PhotoPreview) 화면
  return (
    <main className="placeholder">
      <p>미리보기 화면은 Step 1-6에서 구현됩니다.</p>
      <button type="button" onClick={() => setScreen('camera')}>
        카메라로 돌아가기
      </button>
    </main>
  );
}

export default App;
