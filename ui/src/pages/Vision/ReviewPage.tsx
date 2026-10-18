import { ClipboardCheck } from 'lucide-react';
import { useState } from 'react';
import type { ReviewItem } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { CropImage } from '@/components/common/Ui/media/CropImage';
import { PageHeader } from '@/components/layout/PageHeader';
import { useDecideLabel, useReviewQueue } from '@/hooks/useVision';
import { DASH, fmtDateTime, fmtPercent } from '@/utils/format';
import { VERDICT_LABEL } from './labels';
import styles from './vision.module.css';

function proposed(item: ReviewItem): string {
  if (item.label.verdict === 'CORRECTED') return item.label.plate_text;
  if (item.label.verdict === 'CORRECT') return item.confirmed_plate;
  return DASH;
}

function ReviewRow({ item }: { item: ReviewItem }) {
  const decide = useDecideLabel();
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState('');

  return (
    <li className={styles.reviewRow}>
      <CropImage captureId={item.capture_id} size="md" />
      <div className={styles.reviewBody}>
        <p>
          <Badge tone={item.label.verdict === 'UNUSABLE' ? 'danger' : 'accent'}>{VERDICT_LABEL[item.label.verdict]}</Badge>{' '}
          <span className={styles.plate}>{proposed(item)}</span>
        </p>
        <p className={styles.note}>
          Máy đọc <span className={styles.mono}>{item.machine_plate || DASH}</span> ({fmtPercent(item.machine_confidence)}) · cổng xác nhận{' '}
          <span className={styles.mono}>{item.confirmed_plate || DASH}</span>
        </p>
        <p className={styles.note}>Gán bởi {item.label.labeler} · {fmtDateTime(item.label.created_at)}</p>
        {decide.error && <ErrorBlock error={decide.error} />}
        {rejecting ? (
          <form
            className={styles.inline}
            onSubmit={(event) => {
              event.preventDefault();
              decide.mutate({ labelId: item.label.id, decision: 'REJECTED', note: note.trim() });
            }}
          >
            <TextField label="Vì sao trả lại" required minLength={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
            <Button type="submit" variant="danger" size="sm" loading={decide.isPending} disabled={note.trim().length < 3}>Trả lại</Button>
            <Button size="sm" variant="ghost" onClick={() => setRejecting(false)}>Huỷ</Button>
          </form>
        ) : (
          <div className={styles.actions}>
            <Button size="sm" loading={decide.isPending} onClick={() => decide.mutate({ labelId: item.label.id, decision: 'APPROVED', note: '' })}>
              Duyệt
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setRejecting(true)}>Trả lại…</Button>
          </div>
        )}
      </div>
    </li>
  );
}

export function ReviewPage() {
  const queue = useReviewQueue();

  return (
    <>
      <PageHeader
        title="Duyệt nhãn"
        description="Bốn mắt: nhãn của bạn không hiện ở đây và hệ thống chặn tự duyệt. Chỉ nhãn đã duyệt mới vào snapshot."
      />
      {queue.isPending && <Loading />}
      {queue.error && <ErrorBlock error={queue.error} onRetry={() => void queue.refetch()} />}
      {queue.data?.length === 0 && <EmptyState icon={<ClipboardCheck size={28} />} title="Không có nhãn nào chờ duyệt" />}
      {queue.data && queue.data.length > 0 && (
        <ul className={styles.reviewList} aria-label="Nhãn chờ duyệt">
          {queue.data.map((item) => <ReviewRow key={item.label.id} item={item} />)}
        </ul>
      )}
    </>
  );
}
