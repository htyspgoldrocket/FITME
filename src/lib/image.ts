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
    // TODO(Phase 2-7): 다중 프레임(frames) 캡처는 전략 3 구현 시 추가
  };
}

/** 미리보기 <img>용 data URL 복원 */
export function toDataUrl(img: CapturedImage): string {
  return `data:${img.mimeType};base64,${img.base64}`;
}
