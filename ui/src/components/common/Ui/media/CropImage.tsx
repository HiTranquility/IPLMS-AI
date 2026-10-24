import { ImageOff } from 'lucide-react';
import { useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import { VISION_ENDPOINTS } from '@/services/apiEndpoints/vision.endpoint';
import styles from './CropImage.module.css';

export interface CropImageProps {
  captureId: string;
  size?: 'sm' | 'md' | 'lg';
  src?: string;
}

/** Ảnh cắt biển số lấy từ DB console (cùng nguồn, không cache). Lỗi tải thì nói rõ, không để ô trống. */
export function CropImage({ captureId, size = 'md', src }: CropImageProps) {
  const { t } = useI18n();
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span className={`${styles.frame} ${styles[size]} ${styles.failed}`} role="img" aria-label={t.crop.failed}>
        <ImageOff size={18} aria-hidden />
        {size !== 'sm' && <span aria-hidden>{t.crop.failed}</span>}
      </span>
    );
  }
  return (
    <img
      className={`${styles.frame} ${styles[size]}`}
      src={src ?? VISION_ENDPOINTS.SAMPLE_CROP(captureId)}
      alt={t.crop.alt}
      onError={() => setFailed(true)}
    />
  );
}

export default CropImage;
