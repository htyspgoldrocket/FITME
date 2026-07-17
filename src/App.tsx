import { useState } from 'react';
import ModeSelect from './components/ModeSelect';
import ProfileInput from './components/ProfileInput';
import CameraView, { TIMER_OPTIONS, type TimerSeconds } from './components/CameraView';
import PhotoPreview from './components/PhotoPreview';
import MeasureResult from './components/MeasureResult';
import { captureFramesFromVideo } from './lib/image';
import type { CameraFacing } from './lib/camera';
import type { CapturedImage, MeasurementMode, UserProfile } from './types';

/** 앱 화면 단계 — 모드 선택 → 신체 정보(2-8b) → 카메라 → 미리보기 → 측정 결과(2-8e) */
type Screen = 'mode-select' | 'profile' | 'camera' | 'preview' | 'result';

function App() {
  const [screen, setScreen] = useState<Screen>('mode-select');
  const [mode, setMode] = useState<MeasurementMode | null>(null);
  const [image, setImage] = useState<CapturedImage | null>(null);
  // 키(필수)·몸무게(선택) — 척도 캘리브레이션·BMI 보정 입력(2-7b).
  // 재촬영·뒤로가기 후에도 유지되도록 App이 보관 (Phase 1 배운 것 3번)
  const [profile, setProfile] = useState<UserProfile | null>(null);
  // 층위 1 정적 안내(2-8c) — 세션 첫 카메라 진입에만 자동 표시 (재촬영 시 생략)
  const [guideSeen, setGuideSeen] = useState(false);
  // 층위 3 자동 촬영(2-8d) — 기본 ON, 재촬영 후에도 선택 유지
  const [autoShoot, setAutoShoot] = useState(true);
  // 전/후면 선택 — 재촬영으로 카메라에 재진입해도 유지
  const [facing, setFacing] = useState<CameraFacing>('environment');
  // 셔터 타이머 — facing과 동일하게 재진입해도 유지
  const [timerSec, setTimerSec] = useState<TimerSeconds>(0);

  const handleModeSelect = (selected: MeasurementMode) => {
    setMode(selected);
    setScreen('profile');
  };

  // 다중 프레임 캡처 중 여부 — 캡처 약 2초 동안 카메라 화면 유지 + 중복 셔터 방지
  const [capturing, setCapturing] = useState(false);

  const handleShutter = async (video: HTMLVideoElement) => {
    if (capturing) return;
    setCapturing(true);
    try {
      // 7프레임(전략 3) — 캡처 완료까지 카메라가 언마운트되지 않아야 한다
      setImage(await captureFramesFromVideo(video));
      setScreen('preview');
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setCapturing(false);
    }
  };

  if (screen === 'mode-select' || mode === null) {
    return <ModeSelect onSelect={handleModeSelect} />;
  }

  if (screen === 'profile') {
    return (
      <ProfileInput
        initial={profile}
        onSubmit={(p) => {
          setProfile(p);
          setScreen('camera');
        }}
        onBack={() => setScreen('mode-select')}
      />
    );
  }

  if (screen === 'camera') {
    return (
      <CameraView
        mode={mode}
        facing={facing}
        onToggleFacing={() =>
          setFacing((f) => (f === 'environment' ? 'user' : 'environment'))
        }
        timerSec={timerSec}
        onCycleTimer={() =>
          setTimerSec(
            (t) => TIMER_OPTIONS[(TIMER_OPTIONS.indexOf(t) + 1) % TIMER_OPTIONS.length],
          )
        }
        onBack={() => setScreen('profile')}
        onShutter={handleShutter}
        showGuide={!guideSeen}
        onDismissGuide={() => setGuideSeen(true)}
        autoShoot={autoShoot}
        onToggleAutoShoot={() => setAutoShoot((v) => !v)}
        capturing={capturing}
      />
    );
  }

  if (screen === 'preview' && image !== null) {
    return (
      <PhotoPreview
        image={image}
        mode={mode}
        onRetake={() => setScreen('camera')}
        onConfirm={() => setScreen('result')}
      />
    );
  }

  // 측정 결과 (2-8e) — /analyze 호출·로딩·실패 처리는 MeasureResult가 담당
  if (screen === 'result' && image !== null) {
    return (
      <MeasureResult
        image={image}
        mode={mode}
        profile={profile}
        onRetake={() => setScreen('camera')}
        onRestart={() => setScreen('mode-select')}
      />
    );
  }

  // 도달 불가 상태(예: image 없이 preview/result) — 처음으로 복귀
  return <ModeSelect onSelect={handleModeSelect} />;
}

export default App;
