// ============================================================
// 카메라 & 자이로 유틸 (Phase 1)
// - 후면 카메라: facingMode "environment" + enumerateDevices 폴백 (그룹 B-2)
// - 자이로: 기기 수직 여부 실시간 감시 (전략 1 — 촬영 각도 가이드)
// ============================================================

/** 카메라 방향 — environment: 후면(기본), user: 전면 */
export type CameraFacing = 'environment' | 'user';

const FACING_LABEL_PATTERN: Record<CameraFacing, RegExp> = {
  environment: /back|rear|environment/i,
  user: /front|user|face/i,
};

/**
 * 지정한 방향의 카메라 스트림을 연다.
 * facingMode 실패 시 enumerateDevices로 라벨을 보고 해당 방향 장치를 찾아 재시도.
 * 주의: 전면 카메라도 스트림 자체는 거울상이 아니다 — 미리보기 반전은 UI(CSS)에서만
 * 처리하고, 캡처 이미지는 원본 그대로 둔다 (ArUco 마커는 좌우 반전 시 검출 불가).
 */
export async function startCamera(
  facing: CameraFacing = 'environment',
): Promise<MediaStream> {
  const base: MediaStreamConstraints = {
    audio: false,
    video: {
      facingMode: { ideal: facing },
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    },
  };

  try {
    return await navigator.mediaDevices.getUserMedia(base);
  } catch {
    // 폴백: 장치 목록에서 라벨로 해당 방향 카메라를 직접 지정
    const devices = await navigator.mediaDevices.enumerateDevices();
    const match = devices.find(
      (d) => d.kind === 'videoinput' && FACING_LABEL_PATTERN[facing].test(d.label),
    );
    if (!match) {
      // 해당 방향을 못 찾으면 아무 카메라나 (PC 개발 환경 등)
      return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }
    return navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { deviceId: { exact: match.deviceId } },
    });
  }
}

export function stopCamera(stream: MediaStream | null): void {
  stream?.getTracks().forEach((t) => t.stop());
}

// ===== 자이로 (기기 수직 표시) =====

export interface TiltState {
  /** 앞뒤 기울기 편차(도). 폰을 세워 든 상태(beta≈90)가 0. */
  pitchDeg: number;
  /** 좌우 기울기(도). 0이 수평. */
  rollDeg: number;
  /** 수직 허용 범위(±7°) 안인지 */
  isVertical: boolean;
}

interface DeviceOrientationEventiOS extends DeviceOrientationEvent {
  requestPermission?: () => Promise<'granted' | 'denied'>;
}

/** iOS 13+는 자이로 접근에 명시적 권한이 필요하다 (사용자 탭 안에서 호출할 것). */
export function gyroNeedsPermission(): boolean {
  const ctor = window.DeviceOrientationEvent as unknown as
    | DeviceOrientationEventiOS
    | undefined;
  return typeof ctor?.requestPermission === 'function';
}

export async function requestGyroPermission(): Promise<boolean> {
  const ctor = window.DeviceOrientationEvent as unknown as
    | DeviceOrientationEventiOS
    | undefined;
  if (typeof ctor?.requestPermission !== 'function') return true;
  try {
    return (await ctor.requestPermission()) === 'granted';
  } catch {
    return false;
  }
}

/** 수직 허용 범위(±도) — 층위 2 자이로 표시(2-8c)도 이 값을 단일 출처로 사용 */
export const VERTICAL_TOLERANCE_DEG = 7;

/** 기울기 감시 시작. 반환된 함수를 호출하면 감시를 중단한다. */
export function watchTilt(onTilt: (t: TiltState) => void): () => void {
  const handler = (e: DeviceOrientationEvent) => {
    if (e.beta === null || e.gamma === null) return;
    const pitchDeg = e.beta - 90; // 세워 든 상태가 0이 되도록
    const rollDeg = e.gamma;
    onTilt({
      pitchDeg,
      rollDeg,
      isVertical:
        Math.abs(pitchDeg) <= VERTICAL_TOLERANCE_DEG &&
        Math.abs(rollDeg) <= VERTICAL_TOLERANCE_DEG,
    });
  };
  window.addEventListener('deviceorientation', handler);
  return () => window.removeEventListener('deviceorientation', handler);
}
