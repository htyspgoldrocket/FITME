import { useEffect, useRef, useState } from 'react';
import {
  gyroNeedsPermission,
  requestGyroPermission,
  startRearCamera,
  stopCamera,
  watchTilt,
  type TiltState,
} from '../lib/camera';
import type { MeasurementMode } from '../types';

interface CameraViewProps {
  mode: MeasurementMode;
  onBack: () => void;
  /** 촬영 버튼 탭 시 현재 비디오 프레임 전달 — 캡처 파이프라인은 Step 1-6 */
  onShutter: (video: HTMLVideoElement) => void;
}

/** 촬영 화면 — 후면 카메라 + 전신/기준물 가이드 오버레이 + 자이로 수직 표시 */
function CameraView({ mode, onBack, onShutter }: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [tilt, setTilt] = useState<TiltState | null>(null);
  const [needsGyroTap, setNeedsGyroTap] = useState(false);

  // 카메라 시작/정지
  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    (async () => {
      try {
        stream = await startRearCamera();
        if (cancelled) {
          stopCamera(stream);
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
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
      stopCamera(stream);
    };
  }, []);

  // 자이로 감시 (iOS는 별도 탭 필요)
  useEffect(() => {
    if (gyroNeedsPermission()) {
      setNeedsGyroTap(true);
      return;
    }
    return watchTilt(setTilt);
  }, []);

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
      <video ref={videoRef} autoPlay playsInline muted className="camera__video" />

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

      {/* 하단: 셔터 */}
      <div className="camera__bottom">
        <button
          type="button"
          className="camera__shutter"
          aria-label="촬영"
          onClick={() => videoRef.current && onShutter(videoRef.current)}
        />
      </div>
    </div>
  );
}

export default CameraView;
