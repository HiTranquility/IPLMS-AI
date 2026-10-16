import { useState, type FormEvent } from 'react';
import type { Turn, Verdict } from '@/api/types';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextArea } from '@/components/common/Ui/form/Field';
import { useReviewTurn } from '@/hooks/useConsole';
import { VERDICT_LABEL } from './labels';
import styles from './CopilotLabPage.module.css';

const VERDICTS: Verdict[] = ['CORRECT', 'INCORRECT', 'UNSAFE'];

/** Chấm một lượt. Sai/không an toàn bắt buộc ghi chú — khớp luật ở copilot_lab_service. */
export function ReviewForm({ turn }: { turn: Turn }) {
  const review = useReviewTurn();
  const [verdict, setVerdict] = useState<Verdict>(turn.review?.verdict ?? 'CORRECT');
  const [note, setNote] = useState(turn.review?.note ?? '');
  const needsNote = verdict !== 'CORRECT' && note.trim().length < 3;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    review.mutate({ turnId: turn.turn_id, verdict, note: note.trim() });
  };

  return (
    <form className={styles.review} onSubmit={submit} aria-label="Chấm lượt trả lời">
      <fieldset className={styles.verdicts}>
        <legend className={styles.legend}>Kết luận</legend>
        {VERDICTS.map((value) => (
          <label key={value} className={styles.verdict}>
            <input type="radio" name="verdict" value={value} checked={verdict === value} onChange={() => setVerdict(value)} />
            {VERDICT_LABEL[value]}
          </label>
        ))}
      </fieldset>
      <TextArea
        label="Ghi chú"
        hint={verdict === 'CORRECT' ? 'Không bắt buộc.' : 'Bắt buộc: sai ở đâu, đúng ra phải là gì.'}
        maxLength={500}
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      {review.error && <ErrorBlock error={review.error} />}
      {review.isSuccess && <p className={styles.saved} role="status">Đã lưu kết quả chấm.</p>}
      <Button type="submit" variant="accent" loading={review.isPending} disabled={needsNote}>
        {turn.review ? 'Chấm lại' : 'Lưu kết quả'}
      </Button>
    </form>
  );
}
