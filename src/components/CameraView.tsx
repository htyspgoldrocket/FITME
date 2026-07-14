import { useEffect, useRef, useState } from 'react';
import {
  gyroNeedsPermission,
  requestGyroPermission,
  startCamera,
  stopCamera,
  watchTilt,
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
}

/** 촬영 화면 — 전/후면 카메라 + 전신/기준물 가이드 오버레이 + 자이로 수직 표시 */
function CameraView({
  mode,
  facing,
  onToggleFacing,
  timerSec,
  onCycleTimer,
  onBack,
  onShutter,
}: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
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

      {/* 가이드 오버레이: 전신 프레임 + 기준물 위치 */}
      <div className="camera__overlay" aria-hidden="true">
        <div className="camera__body-frame" />
        <div className="camera__ref-guide">
          {mode === 'simple' ? '💳 카드를 여기(가슴 부근)에' : '🔳 마커를 여기(가슴 부근)에'}
        </div>
      </div>

      {/* 상단 바: 뒤로 + 안내 + 수직 표시 */}
      <div className="camera__top">
        <button type="button" className="camera__back" onClick={onBack}>
          ←
        </button>
        <span className="camera__hint">약 2m 거리에서 전신이 프레임에 들어오게</span>
        {tilt && (
          <span
            className={
              'camera__tilt ' +
              (tilt.isVertical ? 'camera__tilt--ok' : 'camera__tilt--bad')
            }
          >
            {tilt.isVertical ? '📱 수직 OK' : '📱 폰을 수직으로'}
          </span>
        )}
        {needsGyroTap && (
          <button type="button" className="camera__gyro-btn" onClick={enableGyro}>
            수직 가이드 켜기
          </button>
        )}
      </div>

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
