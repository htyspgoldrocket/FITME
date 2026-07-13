import { toDataUrl } from '../lib/image';
import type { CapturedImage, MeasurementMode } from '../types';

interface PhotoPreviewProps {
  image: CapturedImage;
  mode: MeasurementMode;
  onRetake: () => void;
  onConfirm: () => void;
}

/** 촬영 결과 미리보기 — 재촬영 또는 사용 결정 */
function PhotoPreview({ image, mode, onRetake, onConfirm }: PhotoPreviewProps) {
  return (
    <div className="preview">
      <img src={toDataUrl(image)} alt="촬영된 사진" className="preview__img" />

      <div className="preview__info">
        <span>
          {mode === 'simple' ? '🟢 간편 모드' : '🔵 정밀 모드'} ·{' '}
          {image.width}×{image.height}px
        </span>
        <span>기준물({mode === 'simple' ? '카드' : '마커'})이 선명하게 보이나요?</span>
      </div>

      <div className="preview__actions">
        <button type="button" className="preview__btn" onClick={onRetake}>
          다시 촬영
        </button>
        <button
          type="button"
          className="preview__btn preview__btn--primary"
          onClick={onConfirm}
        >
          이 사진 사용
        </button>
      </div>
    </div>
  );
}

export default PhotoPreview;
