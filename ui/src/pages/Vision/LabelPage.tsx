import { Tags } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { LabelVerdict, VisionSample } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { CropImage } from '@/components/common/Ui/media/CropImage';
import { PageHeader } from '@/components/layout/PageHeader';
import { useAddLabel, useLabelQueue } from '@/hooks/useVision';
import { DASH, fmtPercent } from '@/utils/format';
import { REASON_LABEL } from './labels';
import styles from './vision.module.css';

function LabelForm({ sample, remaining }: { sample: VisionSample; remaining: number }) {
  const add = useAddLabel();
  const [correcting, setCorrecting] = useState(false);
  const [plate, setPlate] = useState('');
  const plateRef = useRef<HTMLInputElement>(null);

  const send = (verdict: LabelVerdict) => add.mutate({ captureId: sample.capture_id, verdict, plateText: verdict === 'CORRECTED' ? plate : '' });

  // Phím tắt giống trang gán nhãn của moderator (platform): 1 đúng · 2 sửa · 3 hỏng.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (add.isPending || target?.closest('input, textarea, select')) return;
      if (event.key === '1') send('CORRECT');
      if (event.key === '2') setCorrecting(true);
      if (event.key === '3') send('UNUSABLE');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  useEffect(() => {
    if (correcting) plateRef.current?.focus();
  }, [correcting]);

  const submitCorrection = (event: FormEvent) => {
    event.preventDefault();
    send('CORRECTED');
  };

  return (
    <section className={styles.labelCard} aria-label="Mẫu đang gán">
      <CropImage captureId={sample.capture_id} size="lg" />
      <dl className={styles.facts}>
        <dt>Biển xác nhận ở cổng</dt><dd className={styles.plate}>{sample.confirmed_plate || DASH}</dd>
        <dt>Máy đọc</dt><dd className={styles.mono}>{sample.machine_plate || DASH} · {fmtPercent(sample.machine_confidence)}</dd>
        <dt>Lý do chọn</dt>
        <dd className={styles.badges}>
          {sample.human_corrected && <Badge tone="accent">Nhân viên đã sửa</Badge>}
          {sample.selection_reasons.map((r) => <Badge key={r}>{REASON_LABEL[r] ?? r}</Badge>)}
        </dd>
      </dl>
      <p className={styles.question}>Biển xác nhận ở cổng có đúng với ảnh không?</p>
      <div className={styles.actions}>
        <Button onClick={() => send('CORRECT')} loading={add.isPending && add.variables?.verdict === 'CORRECT'}>
          Đúng <kbd className={styles.kbd}>1</kbd>
        </Button>
        <Button variant="secondary" onClick={() => setCorrecting(true)}>
          Sửa biển <kbd className={styles.kbd}>2</kbd>
        </Button>
        <Button variant="secondary" onClick={() => send('UNUSABLE')} loading={add.isPending && add.variables?.verdict === 'UNUSABLE'}>
          Ảnh hỏng <kbd className={styles.kbd}>3</kbd>
        </Button>
      </div>
      {correcting && (
        <form className={styles.inline} onSubmit={submitCorrection}>
          <TextField ref={plateRef} label="Biển đúng" required minLength={4} maxLength={20} value={plate} onChange={(e) => setPlate(e.target.value.toUpperCase())} />
          <Button type="submit" variant="accent" loading={add.isPending}>Lưu biển sửa</Button>
        </form>
      )}
      {add.error && <ErrorBlock error={add.error} />}
      <p className={styles.note}>Còn {remaining} mẫu trong lượt tải này. Nhãn của bạn chờ một người khác duyệt mới vào dataset.</p>
    </section>
  );
}

export function LabelPage() {
  const queue = useLabelQueue();
  const current = queue.data?.[0];

  return (
    <>
      <PageHeader
        title="Gán nhãn chuyên sâu"
        description="Ảnh cắt nhận từ backend (kênh A2), ưu tiên mẫu nhân viên đã sửa và mẫu máy kém tự tin. Nhãn ở đây là nhãn train của console, không ghi ngược về backend."
      />
      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}
      {queue.isSuccess && !current && (
        <EmptyState icon={<Tags size={28} />} title="Hết mẫu cần gán" description="Mẫu mới đến theo chu kỳ xuất của backend. Mẫu bạn đã gán sẽ không quay lại hàng của bạn." />
      )}
      {current && <LabelForm key={current.capture_id} sample={current} remaining={queue.data!.length} />}
    </>
  );
}
