import { CheckCircle2, FileText, Keyboard, Sparkles } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { useSeedDemoBatch } from '@/hooks/mutations/useVisionMutations';
import styles from './LabelStudio.module.css';

interface LabelEmptyStudioProps {
  onSeeded?: () => void;
}

export function LabelEmptyStudio({ onSeeded }: LabelEmptyStudioProps) {
  const seedMutation = useSeedDemoBatch();

  const handleSeed = () => {
    seedMutation.mutate(undefined, {
      onSuccess: () => {
        onSeeded?.();
      },
    });
  };

  const demoPlates = [
    { plate: '51A-888.88', type: 'Ô tô cá nhân biển trắng (TP.HCM)', conf: '97%' },
    { plate: '29-B1 999.99', type: 'Xe máy 2 dòng biển vuông (Hà Nội)', conf: '88%' },
    { plate: '30E-123.45', type: 'Taxi / Vận tải biển vàng', conf: '93%' },
    { plate: '60-A 888.88', type: 'Xe điện cá nhân (Đồng Nai)', conf: '95%' },
    { plate: '43A-567.89', type: 'Biển mờ / Máy đọc nhầm 43A-567.80', conf: '64%' },
  ];

  return (
    <section className={styles.emptyStudio} aria-label="Trung tâm gán nhãn AI">
      <div className={styles.emptyHero}>
        <div className={styles.emptyIconCircle}>
          <CheckCircle2 size={28} aria-hidden />
        </div>
        <h2 className={styles.emptyTitle}>Hàng đợi A2 sẵn sàng làm việc</h2>
        <p className={styles.emptyDesc}>
          Hiện tại không còn ảnh chụp cổng nào đang chờ gán nhãn trong hàng đợi A2. Bạn có thể nạp ngay lô mẫu
          thực hành gồm 5 trường hợp biển số thực tế tại Việt Nam để kiểm thử luồng gán nhãn và phím tắt.
        </p>
      </div>

      {/* Lô mẫu thực hành 5 biển số */}
      <div className={styles.seedBatchCard}>
        <div className={styles.seedBatchHeader}>
          <div className={styles.seedBatchTitle}>
            <Sparkles size={16} aria-hidden />
            Lô mẫu thực hành đa dạng (5 biển số Việt Nam)
          </div>
          <Button
            variant="accent"
            size="md"
            loading={seedMutation.isPending}
            onClick={handleSeed}
            title="Nạp ngay 5 mẫu biển số thực hành vào hàng đợi"
          >
            <Sparkles size={14} aria-hidden />
            Nạp 5 mẫu thực hành vào hàng đợi
          </Button>
        </div>

        <div className={styles.seedPlateGrid}>
          {demoPlates.map((item) => (
            <div key={item.plate} className={styles.seedPlateCard}>
              <span className={styles.seedPlatePlate}>{item.plate}</span>
              <span className={styles.seedPlateMeta}>{item.type}</span>
              <span className={styles.seedPlateMeta}>Độ tin cậy máy: {item.conf}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 2 Cột: Quy chuẩn gán nhãn (SOP) & Phím tắt */}
      <div className={styles.emptySplitGrid}>
        <div className={styles.infoCard}>
          <div className={styles.infoCardTitle}>
            <FileText size={16} aria-hidden />
            Quy chuẩn gán nhãn biển số (SOP)
          </div>
          <ul className={styles.sopList}>
            <li>
              <strong>Biển xe máy 2 dòng:</strong> Dòng trên là mã địa phương + seri (VD: <code>29-B1</code>), dòng dưới là số đăng ký (VD: <code>999.99</code>). Định dạng chuẩn: <code>29-B1 999.99</code>.
            </li>
            <li>
              <strong>Ảnh hỏng (UNUSABLE):</strong> Đánh dấu khi biển bị che khuất &gt;30%, chói đèn lóa hoàn toàn, hoặc góc chụp biến dạng không thể đọc được bằng mắt thường.
            </li>
            <li>
              <strong>Nguyên tắc 4 mắt (ADR-0048):</strong> Nhãn sau khi bạn xác nhận hoặc chỉnh sửa sẽ chuyển sang hàng đợi kiểm duyệt để AI Reviewer độc lập phê duyệt trước khi đưa vào tập huấn luyện.
            </li>
          </ul>
        </div>

        <div className={styles.infoCard}>
          <div className={styles.infoCardTitle}>
            <Keyboard size={16} aria-hidden />
            Phím tắt thao tác nhanh
          </div>
          <div className={styles.shortcutGrid}>
            <div className={styles.shortcutItem}>
              <span>Xác nhận đúng</span>
              <kbd className={styles.kbd}>1</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>Sửa biển số</span>
              <kbd className={styles.kbd}>2</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>Đánh dấu ảnh hỏng</span>
              <kbd className={styles.kbd}>3</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>Đảo màu ảnh</span>
              <kbd className={styles.kbd}>I</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>Tăng tương phản</span>
              <kbd className={styles.kbd}>C</kbd>
            </div>
            <div className={styles.shortcutItem}>
              <span>Khôi phục ảnh gốc</span>
              <kbd className={styles.kbd}>0</kbd>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default LabelEmptyStudio;
