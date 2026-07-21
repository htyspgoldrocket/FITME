import { useEffect, useRef } from 'react';
import type { AnalyzeResponse, CapturedImage, FitScore } from '../types';

interface FitHeatmapProps {
  /** 합성 이미지 (base64, data: 프리픽스 제외) */
  imageBase64: string;
  /** 랜드마크 좌표 기준 원본 사진 (width/height로 스케일 배율 계산) */
  originalImage: CapturedImage;
  landmarks: NonNullable<AnalyzeResponse['landmarks']>;
  scores: FitScore[];
}

const STATUS_COLOR: Record<string, string> = {
  tight: 'rgba(220, 38, 38, 0.45)',
  good: 'rgba(16, 185, 129, 0.35)',
  loose: 'rgba(59, 130, 246, 0.42)',
};

const PART_LABEL: Record<string, string> = {
  chest: '가슴',
  waist: '허리',
  hip: '엉덩이',
  shoulder: '어깨',
};

const BAND_HALF_HEIGHT_RATIO = 0.025; // 이미지 높이의 2.5%를 위아래 밴드 반높이로

/**
 * 핏 히트맵 오버레이 (5-3d) — 합성 이미지 위에 부위별 색상 밴드 + 수치 라벨.
 *
 * 좌표는 원본 촬영 사진(originalImage) 기준 픽셀이고, 합성 이미지는 종횡비를
 * 유지한 채 리사이즈되므로(5-3b에서 확인), (합성 이미지 실제 크기 / 원본 크기)
 * 배율로 스케일링해 위치를 맞춘다.
 *
 * ⚠️ 합성 자체가 치수를 반영하지 못하는 외관용 근사이므로(07-20 결정), 밴드는
 * "몸 위의 대략적 위치 안내"이지 정밀 실측 표시가 아니다 — 수치 라벨이 진짜 정보.
 */
function FitHeatmap({ imageBase64, originalImage, landmarks, scores }: FitHeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);

      const scaleX = img.naturalWidth / originalImage.width;
      const scaleY = img.naturalHeight / originalImage.height;
      const bandHalfHeight = img.naturalHeight * BAND_HALF_HEIGHT_RATIO;
      const fontSize = Math.round(img.naturalHeight * 0.026);

      for (const score of scores) {
        const lm = landmarks[score.part as keyof typeof landmarks];
        if (!lm) continue; // 랜드마크 없는 부위(정의 불일치 등)는 오버레이 생략

        const x1 = lm.leftX * scaleX;
        const x2 = lm.rightX * scaleX;
        const y = lm.y * scaleY;
        const color = STATUS_COLOR[score.status] ?? STATUS_COLOR.good;

        ctx.fillStyle = color;
        ctx.fillRect(
          Math.min(x1, x2),
          y - bandHalfHeight,
          Math.abs(x2 - x1),
          bandHalfHeight * 2,
        );

        const sign = score.diff_cm > 0 ? '+' : '';
        const label = `${PART_LABEL[score.part] ?? score.part} ${sign}${score.diff_cm.toFixed(1)}cm`;
        const midX = (x1 + x2) / 2;
        const labelY = y + bandHalfHeight + fontSize;

        ctx.font = `bold ${fontSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.lineWidth = 3;
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.strokeText(label, midX, labelY);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, midX, labelY);
      }
    };
    img.src = `data:image/jpeg;base64,${imageBase64}`;
  }, [imageBase64, originalImage, landmarks, scores]);

  return <canvas ref={canvasRef} className="fit__synth-img fit__heatmap" />;
}

export default FitHeatmap;
