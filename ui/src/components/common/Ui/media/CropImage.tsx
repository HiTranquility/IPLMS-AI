import { ImageOff } from 'lucide-react';
import { useState } from 'react';
import { API_BASE } from '@/api/client';
import styles from './CropImage.module.css';

/** Ảnh cắt biển số lấy từ DB console (cùng nguồn, không cache). Lỗi tải thì nói rõ, không để ô trống. */
export function CropImage({ captureId, size = 'md' }: { captureId: string; size?: 'sm' | 'md' | 'lg' }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span className={`${styles.frame} ${styles[size]} ${styles.failed}`} role="img" aria-label="Không tải được ảnh cắt">
        <ImageOff size={18} aria-hidden />
      </span>
    );
  }
  return (
    <img
      className={`${styles.frame} ${styles[size]}`}
      src={`${API_BASE}/vision/samples/${captureId}/crop`}
      alt="Ảnh cắt biển số"
      onError={() => setFailed(true)}
    />
  );
}
