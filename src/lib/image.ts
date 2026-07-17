// ============================================================
// 이미지 캡처 & 리사이즈 (Phase 1)
// - 라이브 비디오 프레임을 Canvas에 그려 캡처한다.
//   이 방식은 파일 업로드와 달리 EXIF 메타데이터가 아예 없고,
//   Canvas에 보이는 그대로 그려지므로 회전 보정이 필요 없다 → rotation은 항상 0.
// - 너비 1080px 기준 리사이즈 + JPEG 85% (그룹 B-8: 이미지 과대 전송 방지)
// ============================================================

import type { CapturedImage } from '../types';

export const TARGET_WIDTH = 1080;
const JPEG_QUALITY = 0.85;

/**
 * 현재 비디오 프레임을 캡처해 CapturedImage로 만든다.
 * @throws 비디오가 아직 재생 전이거나 Canvas 컨텍스트를 못 얻으면 Error
 */
export function captureFromVideo(video: HTMLVideoElement): CapturedImage {
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (!vw || !vh) {
    throw new Error('비디오가 아직 준비되지 않았습니다. 잠시 후 다시 시도하세요.');
  }

  const scale = TARGET_WIDTH / vw;
  const width = TARGET_WIDTH;
  const height = Math.round(vh * scale);

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas 2D 컨텍스트를 얻지 못했습니다.');
  }
  ctx.drawImage(video, 0, 0, width, height);

  const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
  const base64 = dataUrl.split(',')[1];
  if (!base64) {
    throw new Error('이미지 인코딩에 실패했습니다.');
  }

  return {
    base64,
    width,
    height,
    mimeType: 'image/jpeg',
    rotation: 0, // 비디오 프레임 캡처는 EXIF가 없으므로 항상 정방향
  };
}

// ===== 다중 프레임 캡처 (전략 3, 2-8e) =====

/** 기본 프레임 수 — 2-7 검증으로 7 확정 (3→5→7 프레임에서 7/8 항목 편차 ≤2cm) */
export const DEFAULT_FRAME_COUNT = 7;
/** 프레임 간격 — 7장 × 350ms ≈ 2.1초 (CLAUDE.md 전략 3: "2~3초간 캡처") */
const FRAME_INTERVAL_MS = 350;

/**
 * 약 2초에 걸쳐 여러 프레임을 캡처한다. 첫 프레임이 대표 이미지(base64,
 * 미리보기·기준물 검출용)가 되고, frames에 전체가 담겨 /analyze의
 * 다중 프레임 중앙값 측정에 쓰인다. 캡처 동안 사용자는 정지 상태여야 한다.
 */
export async function captureFramesFromVideo(
  video: HTMLVideoElement,
  frameCount = DEFAULT_FRAME_COUNT,
  intervalMs = FRAME_INTERVAL_MS,
): Promise<CapturedImage> {
  const first = captureFromVideo(video);
  const frames = [first.base64];
  for (let i = 1; i < frameCount; i += 1) {
    await new Promise((r) => setTimeout(r, intervalMs));
    frames.push(captureFromVideo(video).base64);
  }
  return { ...first, frames };
}

/** 미리보기 <img>용 data URL 복원 */
export function toDataUrl(img: CapturedImage): string {
  return `data:${img.mimeType};base64,${img.base64}`;
}
