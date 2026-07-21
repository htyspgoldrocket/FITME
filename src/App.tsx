import { useState } from 'react';
import ModeSelect from './components/ModeSelect';
import ProfileInput from './components/ProfileInput';
import CameraView, { TIMER_OPTIONS, type TimerSeconds } from './components/CameraView';
import PhotoPreview from './components/PhotoPreview';
import MeasureResult from './components/MeasureResult';
import ClothingUrlInput from './components/ClothingUrlInput';
import ClothingSpecView from './components/ClothingSpecView';
import FitResultView from './components/FitResultView';
import { captureFramesFromVideo } from './lib/image';
import type { CameraFacing } from './lib/camera';
import type {
  AnalyzeResponse,
  CapturedImage,
  ClothingResponse,
  FitResponse,
  MeasurementMode,
  SynthesizeResponse,
  UserProfile,
} from './types';

/**
 * 앱 화면 단계 — 모드 선택 → 신체 정보(2-8b) → 카메라 → 미리보기 →
 * 측정 결과(2-8e) → 의류 URL 입력(3-1) → 의류 정보(3-4b) → 핏 결과(4-4b)
 */
type Screen =
  | 'mode-select'
  | 'profile'
  | 'camera'
  | 'preview'
  | 'result'
  | 'clothing-url'
  | 'clothing-spec'
  | 'fit-result';

function App() {
  const [screen, setScreen] = useState<Screen>('mode-select');
  const [mode, setMode] = useState<MeasurementMode | null>(null);
  const [image, setImage] = useState<CapturedImage | null>(null);
  // 같은 사진의 분석 결과 캐시 (3-1) — 의류 화면에서 뒤로 와도 재분석(AI 7회) 없음.
  // 새 사진을 캡처하면 무효화한다
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  // 의류 상품 페이지 URL (3-1) — 재입력 진입 시 유지되도록 App이 보관
  const [clothingUrl, setClothingUrl] = useState<string | null>(null);
  // 같은 URL의 의류 조회 결과 캐시 (3-4b) — 뒤로가기 재진입 시 재요청 없음.
  // URL이 바뀌면 무효화한다 (분석 캐시와 동일 패턴)
  const [clothing, setClothing] = useState<ClothingResponse | null>(null);
  // 핏 결과 캐시 (4-4b) — 입력(측정·의류)이 바뀌면 무효화 (재요청 = AI 1회)
  const [fit, setFit] = useState<FitResponse | null>(null);
  // 가상 착용 합성 캐시 (5-3c) — fit과 같은 트리거(새 사진·새 의류)로 무효화.
  // fit과 달리 자동 호출은 안 함(버튼으로 시작, VTON 1회 비용 절약)
  const [synthesis, setSynthesis] = useState<SynthesizeResponse | null>(null);
  // 키(필수)·몸무게(선택) — 척도 캘리브레이션·BMI 보정 입력(2-7b).
  // 재촬영·뒤로가기 후에도 유지되도록 App이 보관 (Phase 1 배운 것 3번)
  const [profile, setProfile] = useState<UserProfile | null>(null);
  // 층위 1 정적 안내(2-8c) — 세션 첫 카메라 진입에만 자동 표시 (재촬영 시 생략)
  const [guideSeen, setGuideSeen] = useState(false);
  // 층위 3 자동 촬영(2-8d) — 기본 ON, 재촬영 후에도 선택 유지
  const [autoShoot, setAutoShoot] = useState(true);
  // 음성 안내(5-4 개선 ②) — 사용자가 카메라에서 2m 떨어져 배너를 읽을 수 없어
  // 판정 사유를 TTS로 읽어준다. autoShoot과 같은 이유로 App이 보관
  const [voiceGuide, setVoiceGuide] = useState(true);
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
      setAnalysis(null); // 새 사진 → 이전 분석 캐시 무효화 (3-1)
      setFit(null); // 측정이 바뀌므로 핏 캐시도 무효화 (4-4b)
      setSynthesis(null); // 사진이 바뀌므로 합성 캐시도 무효화 (5-3c)
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
        voiceGuide={voiceGuide}
        onToggleVoiceGuide={() => setVoiceGuide((v) => !v)}
        capturing={capturing}
        // 프로필 화면을 거쳐야 카메라에 오므로 실사용에선 항상 존재 — 폴백은 기준 키
        heightCm={profile?.heightCm ?? 170}
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
        cached={analysis}
        onLoaded={setAnalysis}
        onRetake={() => setScreen('camera')}
        onRestart={() => setScreen('mode-select')}
        onNext={() => setScreen('clothing-url')}
      />
    );
  }

  // 의류 URL 입력 (3-1)
  if (screen === 'clothing-url') {
    return (
      <ClothingUrlInput
        initial={clothingUrl}
        onSubmit={(url) => {
          if (url !== clothingUrl) {
            setClothing(null); // 새 URL → 이전 조회 캐시 무효화
            setFit(null); // 의류가 바뀌므로 핏 캐시도 무효화 (4-4b)
            setSynthesis(null); // 의류가 바뀌므로 합성 캐시도 무효화 (5-3c)
          }
          setClothingUrl(url);
          setScreen('clothing-spec');
        }}
        onBack={() => setScreen('result')}
      />
    );
  }

  // 의류 정보 (3-4b) — /clothing 호출·로딩·실패 처리는 ClothingSpecView가 담당
  if (screen === 'clothing-spec' && clothingUrl !== null) {
    const canFit = analysis?.ok === true && analysis.measurements != null;
    return (
      <ClothingSpecView
        url={clothingUrl}
        cached={clothing}
        // ok=false는 캐시하지 않음 — 같은 URL 재진입 시 재조회로 복구 기회를 준다.
        // 스펙이 새로 로드되면 이전 핏 결과도 입력이 달라진 것 → 무효화
        onLoaded={(r) => {
          setClothing(r.ok ? r : null);
          setFit(null);
          setSynthesis(null); // 의류 스펙이 새로 로드되면 합성 캐시도 무효화 (5-3c)
        }}
        onEditUrl={() => setScreen('clothing-url')}
        onRestart={() => setScreen('mode-select')}
        onFit={canFit ? () => setScreen('fit-result') : null}
      />
    );
  }

  // 핏 결과 (4-4b) — /fit 호출·로딩·실패 처리는 FitResultView가 담당
  if (
    screen === 'fit-result' &&
    image !== null &&
    analysis?.measurements != null &&
    clothing?.spec != null
  ) {
    return (
      <FitResultView
        image={image}
        measurements={analysis.measurements}
        landmarks={analysis.landmarks}
        spec={clothing.spec}
        cached={fit}
        // ok=false는 캐시하지 않음 — 재진입 시 재계산으로 복구 기회
        onLoaded={(r) => setFit(r.ok ? r : null)}
        synthCached={synthesis}
        // 합성 성공 시 핏 캐시의 FitResult.imageUrl도 채운다 (6장 계약 — Phase 5
        // 합성 이미지). fit과 synthesis는 같은 트리거로 무효화되므로 불일치 없음
        onSynthesized={(r) => {
          setSynthesis(r);
          if (r.ok && r.imageBase64) {
            setFit((prev) =>
              prev?.ok && prev.result
                ? {
                    ...prev,
                    result: {
                      ...prev.result,
                      imageUrl: `data:image/jpeg;base64,${r.imageBase64}`,
                    },
                  }
                : prev,
            );
          }
        }}
        onBack={() => setScreen('clothing-spec')}
        onRestart={() => setScreen('mode-select')}
      />
    );
  }

  // 도달 불가 상태(예: image 없이 preview/result) — 처음으로 복귀
  return <ModeSelect onSelect={handleModeSelect} />;
}

export default App;
