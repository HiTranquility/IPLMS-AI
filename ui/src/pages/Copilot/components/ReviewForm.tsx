import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextArea } from '@/components/common/Ui/form/Field';
import { useReviewTurn } from '@/hooks/mutations/useCopilotMutations';
import { useI18n } from '@/i18n/I18nProvider';
import type { Turn, Verdict } from '@/types/copilot';
import styles from './ReviewForm.module.css';

const VERDICTS: Verdict[] = ['CORRECT', 'INCORRECT', 'UNSAFE'];

export interface ReviewFormProps {
  turn: Turn;
}

/** Chấm một lượt. Sai/không an toàn bắt buộc ghi chú — khớp luật ở copilot_lab_service. */
export function ReviewForm({ turn }: ReviewFormProps) {
  const { t } = useI18n();
  const review = useReviewTurn();
  const [verdict, setVerdict] = useState<Verdict>(turn.review?.verdict ?? 'CORRECT');
  const [note, setNote] = useState(turn.review?.note ?? '');
  const needsNote = verdict !== 'CORRECT' && note.trim().length < 3;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    review.mutate({ turnId: turn.turn_id, verdict, note: note.trim() });
  };

  return (
    <form className={styles.review} onSubmit={submit} aria-label={t.copilot.formLabel}>
      <fieldset className={styles.verdicts}>
        <legend className={styles.legend}>{t.copilot.verdictLegend}</legend>
        {VERDICTS.map((value) => (
          <label key={value} className={styles.verdict}>
            <input type="radio" name="verdict" value={value} checked={verdict === value} onChange={() => setVerdict(value)} />
            {t.copilot.verdict[value]}
          </label>
        ))}
      </fieldset>
      <TextArea
        label={t.copilot.note}
        hint={verdict === 'CORRECT' ? t.copilot.noteOptional : t.copilot.noteRequired}
        maxLength={500}
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      {review.error && <ErrorBlock error={review.error} />}
      {review.isSuccess && <p className={styles.saved} role="status">{t.copilot.saved}</p>}
      <Button type="submit" variant="accent" loading={review.isPending} disabled={needsNote}>
        {turn.review ? t.copilot.rereview : t.copilot.save}
      </Button>
    </form>
  );
}

export default ReviewForm;
