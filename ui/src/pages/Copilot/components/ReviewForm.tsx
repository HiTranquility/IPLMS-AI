import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Check, ShieldAlert, X } from 'lucide-react';
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
  const noteRef = useRef<HTMLTextAreaElement | null>(null);
  const needsNote = verdict !== 'CORRECT' && note.trim().length < 3;

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (needsNote) return;
    review.mutate({ turnId: turn.turn_id, verdict, note: note.trim() });
  };

  // Xử lý phím tắt nhanh 1 (Đúng), 2 (Sai), 3 (Nguy hại) - an toàn không ăn phím bổ trợ (BUG-10)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;
      if (review.isPending) return;

      const activeEl = document.activeElement as HTMLElement | null;
      const tag = activeEl?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      // Không tự động ghi đè nếu lượt chat đã được chấm điểm trước đó
      if (turn.review?.verdict) return;

      if (e.key === '1') {
        e.preventDefault();
        setVerdict('CORRECT');
        review.mutate({ turnId: turn.turn_id, verdict: 'CORRECT', note: note.trim() });
      } else if (e.key === '2') {
        e.preventDefault();
        setVerdict('INCORRECT');
        noteRef.current?.focus();
      } else if (e.key === '3') {
        e.preventDefault();
        setVerdict('UNSAFE');
        noteRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [turn.turn_id, turn.review?.verdict, note, review]);

  const handle1ClickCorrect = () => {
    setVerdict('CORRECT');
    review.mutate({ turnId: turn.turn_id, verdict: 'CORRECT', note: note.trim() });
  };

  const handle1ClickIncorrect = () => {
    setVerdict('INCORRECT');
    noteRef.current?.focus();
  };

  const handle1ClickUnsafe = () => {
    setVerdict('UNSAFE');
    noteRef.current?.focus();
  };

  const handleAppendTag = (tag: string) => {
    setNote((prev) => (prev ? `${prev}, ${tag}` : tag));
    noteRef.current?.focus();
  };

  return (
    <form className={styles.review} onSubmit={submit} aria-label={t.copilot.formLabel}>
      {/* Thanh 1-click Verdict buttons & Hotkeys */}
      <div className={styles.quickVerdictRow}>
        <button
          type="button"
          className={`${styles.quickVerdictBtn} ${styles.quickVerdictCorrect} ${verdict === 'CORRECT' ? styles.quickVerdictActive : ''}`}
          onClick={handle1ClickCorrect}
          disabled={review.isPending}
        >
          <Check size={14} />
          <span>{t.copilot.quickVerdict1}</span>
        </button>

        <button
          type="button"
          className={`${styles.quickVerdictBtn} ${styles.quickVerdictIncorrect} ${verdict === 'INCORRECT' ? styles.quickVerdictActive : ''}`}
          onClick={handle1ClickIncorrect}
          disabled={review.isPending}
        >
          <X size={14} />
          <span>{t.copilot.quickVerdict2}</span>
        </button>

        <button
          type="button"
          className={`${styles.quickVerdictBtn} ${styles.quickVerdictUnsafe} ${verdict === 'UNSAFE' ? styles.quickVerdictActive : ''}`}
          onClick={handle1ClickUnsafe}
          disabled={review.isPending}
        >
          <ShieldAlert size={14} />
          <span>{t.copilot.quickVerdict3}</span>
        </button>
      </div>

      <div className={styles.hotkeyHintRow}>
        <span className={styles.hotkeyHintText}>{t.copilot.hotkeyHint}</span>
      </div>

      {/* Radio options tiêu chuẩn */}
      <fieldset className={styles.verdicts}>
        <legend className={styles.legend}>{t.copilot.verdictLegend}</legend>
        {VERDICTS.map((value) => (
          <label key={value} className={styles.verdict}>
            <input
              type="radio"
              name="verdict"
              value={value}
              checked={verdict === value}
              onChange={() => setVerdict(value)}
            />
            {t.copilot.verdict[value]}
          </label>
        ))}
      </fieldset>

      {/* Gắn nhanh lý do từ chối (Quick Tags) khi kết luận không phải là Đúng */}
      {verdict !== 'CORRECT' && (
        <div className={styles.tagChipsBar}>
          <span className={styles.tagHintLabel}>{t.copilot.quickTagHint}</span>
          <button
            type="button"
            className={styles.tagChip}
            onClick={() => handleAppendTag(t.copilot.tagFee)}
          >
            {t.copilot.tagFee}
          </button>
          <button
            type="button"
            className={styles.tagChip}
            onClick={() => handleAppendTag(t.copilot.tagSource)}
          >
            {t.copilot.tagSource}
          </button>
          <button
            type="button"
            className={styles.tagChip}
            onClick={() => handleAppendTag(t.copilot.tagHallucination)}
          >
            {t.copilot.tagHallucination}
          </button>
          <button
            type="button"
            className={styles.tagChip}
            onClick={() => handleAppendTag(t.copilot.tagScope)}
          >
            {t.copilot.tagScope}
          </button>
          <button
            type="button"
            className={styles.tagChip}
            onClick={() => handleAppendTag(t.copilot.tagProcedure)}
          >
            {t.copilot.tagProcedure}
          </button>
        </div>
      )}

      <TextArea
        ref={noteRef}
        label={t.copilot.note}
        hint={verdict === 'CORRECT' ? t.copilot.noteOptional : t.copilot.noteRequired}
        maxLength={500}
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />

      {review.error && <ErrorBlock error={review.error} />}
      {review.isSuccess && (
        <p className={styles.saved} role="status">
          {t.copilot.saved}
        </p>
      )}

      <Button type="submit" variant="accent" loading={review.isPending} disabled={needsNote}>
        {turn.review ? t.copilot.rereview : t.copilot.save}
      </Button>
    </form>
  );
}

export default ReviewForm;
