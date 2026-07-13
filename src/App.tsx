import { useState } from 'react';
import ModeSelect from './components/ModeSelect';
import CameraView from './components/CameraView';
import PhotoPreview from './components/PhotoPreview';
import { captureFromVideo } from './lib/image';
import type { CameraFacing } from './lib/camera';
import type { CapturedImage, MeasurementMode } from './types';

/** 앱 화면 단계 — Phase 1 범위: 모드 선택 → 카메라 → 미리보기 */
type Screen = 'mode-select' | 'camera' | 'preview' | 'done';

function App() {
  const [screen, setScreen] = useState<Screen>('mode-select');
  const [mode, setMode] = useState<MeasurementMode | null>(null);
  const [image, setImage] = useState<CapturedImage | null>(null);
  // 전/후면 선택 — 재촬영으로 카메라에 재진입해도 유지
  const [facing, setFacing] = useState<CameraFacing>('environment');

  const handleModeSelect = (selected: MeasurementMode) => {
    setMode(selected);
    setScreen('camera');
  };

  const handleShutter = (video: HTMLVideoElement) => {
    try {
      setImage(captureFromVideo(video));
      setScreen('preview');
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  };

  if (screen === 'mode-select' || mode === null) {
    return <ModeSelect onSelect={handleModeSelect} />;
  }

  if (screen === 'camera') {
    return (
      <CameraView
        mode={mode}
        facing={facing}
        onToggleFacing={() =>
          setFacing((f) => (f === 'environment' ? 'user' : 'environment'))
        }
        onBack={() => setScreen('mode-select')}
        onShutter={handleShutter}
      />
    );
  }

  if (screen === 'preview' && image !== null) {
    return (
      <PhotoPreview
        image={image}
        mode={mode}
        onRetake={() => setScreen('camera')}
        onConfirm={() => setScreen('done')}
      />
    );
  }

  // Phase 1의 끝 — 사진 확정. 측정(analyzeBody 실제 호출)은 Phase 2에서 연결.
  return (
    <main className="placeholder">
      <p>✅ 사진이 준비되었습니다 ({image?.width}×{image?.height}px)</p>
      <p>신체 치수 분석은 Phase 2에서 연결됩니다.</p>
      <button type="button" onClick={() => setScreen('camera')}>
        다시 촬영
      </button>
      <button type="button" onClick={() => setScreen('mode-select')}>
        처음으로
      </button>
    </main>
  );
}

export default App;
