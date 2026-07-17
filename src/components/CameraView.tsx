import { useEffect, useRef, useState } from 'react';
import {
  gyroNeedsPermission,
  requestGyroPermission,
  startCamera,
  stopCamera,
  watchTilt,
  VERTICAL_TOLERANCE_DEG as TILT_TOLERANCE_DEG,
  type CameraFacing,
  type TiltState,
} from '../lib/camera';
import type { MeasurementMode } from '../types';

/** 셔터 타이머(초). 0 = 즉시 촬영 */
export type TimerSeconds = 0 | 3 | 5 | 10;
export const TIMER_OPTIONS: TimerSeconds[] = [0, 3, 5, 10];

interface CameraViewProps {
  mode: MeasurementMode;
  /** 전면/후면 선택 — 재촬영 등 화면 전환 후에도 유지되도록 App이 보관 */
  facing: CameraFacing;
  onToggleFacing: () => void;
  /** 셔터 타이머 — facing과 동일하게 App이 보관해 재촬영 후에도 유지 */
  timerSec: TimerSeconds;
  onCycleTimer: () => void;
  onBack: () => void;
  /** 촬영 버튼 탭 시 현재 비디오 프레임 전달 — 캡처 파이프라인은 Step 1-6 */
  onShutter: (video: HTMLVideoElement) => void;
  /** 층위 1 정적 안내(2-8c) — 세션 첫 진입에만 자동 표시되도록 App이 보관 */
  showGuide: boolean;
  onDismissGuide: () => void;
}

/** 층위 1 — 촬영 전 정적 안내 항목 (CLAUDE.md 전략 1 4층위 명세) */
const GUIDE_ITEMS: { icon: string; text: (refName: string) => string }[] = [
  { icon: '👕', text: () => '몸에 밀착되는 옷을 입어 주세요 — 헐렁한 옷은 측정을 크게 왜곡해요' },
  { icon: '📐', text: (ref) => `${ref}를 가슴에 평평하게 대 주세요` },
  { icon: '📏', text: () => '약 2m 거리에서, 전신이 프레임에 꽉 차게 나오도록' },
  { icon: '📱', text: () => '카메라는 배꼽~가슴 높이에서 수직으로 (거치대 + 타이머 활용)' },
  { icon: '🧍', text: () => '몸을 화면 정중앙에 — 가장자리는 광각 왜곡이 생겨요' },
];

/** 촬영 화면 — 전/후면 카메라 + 전신/기준물 가이드 오버레이 + 자이로 수직 표시 */
function CameraView({
  mode,
  facing,
  onToggleFacing,
  timerSec,
  onCycleTimer,
  onBack,
  onShutter,
  showGuide,
  onDismissGuide,
}: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  // 층위 1 안내: 세션 첫 진입엔 자동으로 열리고, 이후엔 ❓ 버튼으로 재열람
  const [guideOpen, setGuideOpen] = useState(showGuide);
  const [tilt, setTilt] = useState<TiltState | null>(null);
  const [needsGyroTap, setNeedsGyroTap] = useState(false);
  // 스트림 준비 전(초기 로딩·전환 중) 셔터를 막아 빈 프레임 캡처를 방지
  const [ready, setReady] = useState(false);
  // 타이머 카운트다운 남은 초 (null = 카운트다운 아님)
  const [countdown, setCountdown] = useState<number | null>(null);

  // 카메라 시작/정지 (방향 전환 시 스트림 재시작)
  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    setReady(false);
    setCountdown(null); // 카메라 전환 시 진행 중이던 카운트다운 취소
    (async () => {
      try {
        stream = await startCamera(facing);
        if (cancelled) {
          stopCamera(stream);
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadeddata = () => setReady(true);
        }
      } catch (e) {
        setError(
          '카메라를 열 수 없습니다. 브라우저 카메라 권한을 허용해 주세요. ' +
            `(${e instanceof Error ? e.message : String(e)})`,
        );
      }
    })();
    return () => {
      cancelled = true;
      if (videoRef.current) {
        videoRef.current.onloadeddata = null;
      }
      stopCamera(stream);
    };
  }, [facing]);

  // 자이로 감시 (iOS는 별도 탭 필요)
  useEffect(() => {
    if (gyroNeedsPermission()) {
      setNeedsGyroTap(true);
      return;
    }
    return watchTilt(setTilt);
  }, []);

  // 카운트다운 진행: 1초마다 감소, 0이 되면 촬영. 화면 이탈 시 자동 정리.
  useEffect(() => {
    if (countdown === null) return;
    if (countdown <= 0) {
      setCountdown(null);
      if (videoRef.current) onShutter(videoRef.current);
      return;
    }
    const id = window.setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => window.clearTimeout(id);
  }, [countdown, onShutter]);

  const handleShutterClick = () => {
    if (countdown !== null) {
      setCountdown(null); // 카운트다운 중 재탭 = 취소
      return;
    }
    if (timerSec === 0) {
      if (videoRef.current) onShutter(videoRef.current);
      return;
    }
    setCountdown(timerSec);
  };

  const enableGyro = async () => {
    if (await requestGyroPermission()) {
      setNeedsGyroTap(false);
      watchTilt(setTilt); // 화면을 떠날 때 컴포넌트가 사라지므로 정리 생략 가능하지만,
      // 안전하게 unmount 시 정리되도록 상태로 두지 않고 이벤트만 등록
    }
  };

  if (error) {
    return (
      <div className="camera camera--error">
        <p>{error}</p>
        <button type="button" onClick={onBack}>
          뒤로
        </button>
      </div>
    );
  }

  return (
    <div className="camera">
      {/* 전면 카메라는 미리보기만 거울상 — 캡처(captureFromVideo)는 원본 프레임이라 반전 없음 */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={
          'camera__video' + (facing === 'user' ? ' camera__video--mirrored' : '')
        }
      />

      {/* 층위 2 — 정중앙 실루엣 가이드 (광각 가장자리 회피) + 기준물 위치 */}
      <div className="camera__overlay" aria-hidden="true">
        <svg
          className="camera__silhouette"
          viewBox="0 0 100 200"
          preserveAspectRatio="xMidYMid meet"
        >
          <circle cx="50" cy="14" r="12" />
          <path
            d="M44 27 L30 34 L18 78 L26 82 L34 52 L33 96 L38 186 L48 186
               L50 120 L52 186 L62 186 L67 96 L66 52 L74 82 L82 78 L70 34
               L56 27 Z"
          />
        </svg>
        <div className="camera__ref-guide">
          {mode === 'simple' ? '💳 카드를 여기(가슴 부근)에' : '🔳 마커를 여기(가슴 부근)에'}
        </div>
      </div>

      {/* 상단 바: 뒤로 + 안내 + 자이로 2축(좌우 수평·앞뒤 기울기) 표시 */}
      <div className="camera__top">
        <button type="button" className="camera__back" onClick={onBack}>
          ←
        </button>
        <span className="camera__hint">약 2m 거리, 전신을 프레임에 꽉 차게</span>
        {tilt && (
          <span className="camera__tilt-group">
            <span
              className={
                'camera__tilt ' +
                (Math.abs(tilt.rollDeg) <= TILT_TOLERANCE_DEG
                  ? 'camera__tilt--ok'
                  : 'camera__tilt--bad')
              }
            >
              {Math.abs(tilt.rollDeg) <= TILT_TOLERANCE_DEG ? '↔ 수평 OK' : '↔ 좌우 수평을'}
            </span>
            <span
              className={
                'camera__tilt ' +
                (Math.abs(tilt.pitchDeg) <= TILT_TOLERANCE_DEG
                  ? 'camera__tilt--ok'
                  : 'camera__tilt--bad')
              }
            >
              {Math.abs(tilt.pitchDeg) <= TILT_TOLERANCE_DEG ? '↕ 수직 OK' : '↕ 폰을 세워서'}
            </span>
          </span>
        )}
        {needsGyroTap && (
          <button type="button" className="camera__gyro-btn" onClick={enableGyro}>
            수직 가이드 켜기
          </button>
        )}
        <button
          type="button"
          className="camera__help"
          aria-label="촬영 방법 안내"
          onClick={() => setGuideOpen(true)}
        >
          ?
        </button>
      </div>

      {/* 층위 1 — 촬영 전 정적 안내 (세션 첫 진입 자동 표시, ❓로 재열람) */}
      {guideOpen && (
        <div className="camera-guide" role="dialog" aria-label="촬영 방법 안내">
          <h2 className="camera-guide__title">정확한 측정을 위한 촬영 방법</h2>
          <ul className="camera-guide__list">
            {GUIDE_ITEMS.map(({ icon, text }) => (
              <li key={icon}>
                <span className="camera-guide__icon">{icon}</span>
                {text(mode === 'simple' ? '카드' : '마커')}
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="camera-guide__confirm"
            onClick={() => {
              setGuideOpen(false);
              onDismissGuide();
            }}
          >
            확인했어요
          </button>
        </div>
      )}

      {/* 카운트다운 표시 */}
      {countdown !== null && countdown > 0 && (
        <div className="camera__countdown" aria-live="assertive">
          {countdown}
        </div>
      )}

      {/* 하단: 타이머 + 셔터 + 카메라 전환 */}
      <div className="camera__bottom">
        <button
          type="button"
          className="camera__timer"
          aria-label="셔터 타이머"
          onClick={onCycleTimer}
          disabled={countdown !== null}
        >
          ⏱ {timerSec === 0 ? '끔' : `${timerSec}초`}
        </button>
        <button
          type="button"
          className={
            'camera__shutter' +
            (countdown !== null ? ' camera__shutter--counting' : '')
          }
          aria-label={countdown !== null ? '카운트다운 취소' : '촬영'}
          disabled={!ready}
          onClick={handleShutterClick}
        />
        <button
          type="button"
          className="camera__flip"
          aria-label="카메라 전환"
          onClick={onToggleFacing}
        >
          🔄 {facing === 'environment' ? '전면' : '후면'}
        </button>
      </div>
    </div>
  );
}

export default CameraView;
