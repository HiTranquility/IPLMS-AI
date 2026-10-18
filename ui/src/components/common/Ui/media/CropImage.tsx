import { ImageOff } from 'lucide-react';
import { useState } from 'react';
import { API_BASE } from '@/api/client';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './CropImage.module.css';

/** Ảnh cắt biển số lấy từ DB console (cùng nguồn, không cache). Lỗi tải thì nói rõ, không để ô trống. */
export function CropImage({ captureId, size = 'md' }: { captureId: string; size?: 'sm' | 'md' | 'lg' }) {
  const { t } = useI18n();
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span className={`${styles.frame} ${styles[size]} ${styles.failed}`} role="img" aria-label={t.crop.failed}>
        <ImageOff size={18} aria-hidden />
      </span>
    );
  }
  return (
    <img
      className={`${styles.frame} ${styles[size]}`}
      src={`${API_BASE}/vision/samples/${captureId}/crop`}
      alt={t.crop.alt}
      onError={() => setFailed(true)}
    />
  );
}
