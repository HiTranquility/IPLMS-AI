import { Check, X } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { CropImage } from '@/components/common/Ui/media/CropImage';
import { useDecideLabel } from '@/hooks/mutations/useVisionMutations';
import { useI18n } from '@/i18n/I18nProvider';
import type { ReviewItem } from '@/types/vision';
import { DASH, fmtDateTime, fmtPercent } from '@/utils/format';
import styles from '../ReviewPage.module.css';

function proposed(item: ReviewItem): string {
  if (item.label.verdict === 'CORRECTED') return item.label.plate_text;
  if (item.label.verdict === 'CORRECT') return item.confirmed_plate;
  return DASH;
}

export function renderPlateDiff(
  gate: string,
  machine: string,
  diffTitle: (machine: string, gate: string) => string,
) {
  if (!gate || !machine) return <span>{machine || gate || DASH}</span>;
  const maxLen = Math.max(gate.length, machine.length);
  const elements = [];
  for (let i = 0; i < maxLen; i++) {
    const c1 = gate[i] || '';
    const c2 = machine[i] || '';
    if (c1 === c2) {
      elements.push(<span key={i}>{c2}</span>);
    } else {
      elements.push(
        <span
          key={i}
          style={{
            color: 'var(--color-danger)',
            background: 'var(--color-danger-soft)',
            padding: '0 2px',
            borderRadius: '2px',
            fontWeight: 700,
          }}
          title={diffTitle(c2, c1)}
        >
          {c2 || '␣'}
        </span>,
      );
    }
  }
  return elements;
}

export interface ReviewRowProps {
  item: ReviewItem;
}

export function ReviewRow({ item }: ReviewRowProps) {
  const { t } = useI18n();
  const decide = useDecideLabel();
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState('');

  const isExactMatch = item.machine_plate && item.confirmed_plate && item.machine_plate === item.confirmed_plate;

  return (
    <li className={styles.reviewCard}>
      <div className={styles.imageCol}>
        <CropImage captureId={item.capture_id} size="md" />
      </div>

      <div className={styles.reviewBody}>
        <div className={styles.plateRow}>
          <Badge tone={item.label.verdict === 'UNUSABLE' ? 'danger' : 'accent'}>
            {t.vision.verdict[item.label.verdict]}
          </Badge>
          <span className={styles.plate}>{proposed(item)}</span>
          {isExactMatch && <Badge tone="success">{t.review.exactBadge}</Badge>}
        </div>

        {item.label.quality_flags && item.label.quality_flags.length > 0 && (
          <div className={styles.plateRow} aria-label={t.label.flagsTitle}>
            {item.label.quality_flags.map((flag) => (
              <Badge key={flag} tone="neutral">
                {t.label.flags[flag]}
              </Badge>
            ))}
          </div>
        )}

        <div className={styles.comparisonRow}>
          <span>
            {t.review.machine}{' '}
            <span className={styles.plateDiffBox}>
              {renderPlateDiff(item.confirmed_plate, item.machine_plate, t.review.charDiff)}
            </span>{' '}
            ({fmtPercent(item.machine_confidence)})
          </span>
          <span>·</span>
          <span>
            {t.review.gateConfirmed}{' '}
            {item.confirmed_plate ? (
              <span className={styles.plateDiffBox}>{item.confirmed_plate}</span>
            ) : (
              <span title={t.review.gateEmptyHint}>{t.review.gateEmpty}</span>
            )}
          </span>
        </div>

        <p className={styles.metaInfo}>
          {t.review.labeledBy(item.label.labeler, fmtDateTime(item.label.created_at))}
        </p>

        {decide.error && <ErrorBlock error={decide.error} />}

        {rejecting && (
          <form
            className={styles.rejectForm}
            onSubmit={(event) => {
              event.preventDefault();
              decide.mutate({ labelId: item.label.id, decision: 'REJECTED', note: note.trim() });
            }}
          >
            <TextField
              label={t.review.whyReject}
              required
              minLength={3}
              maxLength={500}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <div className={styles.rejectButtons}>
              <Button
                type="submit"
                variant="danger"
                size="sm"
                loading={decide.isPending}
                disabled={note.trim().length < 3}
              >
                {t.review.reject}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setRejecting(false)}>
                {t.review.cancel}
              </Button>
            </div>
          </form>
        )}
      </div>

      {!rejecting && (
        <div className={styles.actionsCol}>
          <div className={styles.buttonGroup}>
            <Button
              size="sm"
              loading={decide.isPending}
              onClick={() => decide.mutate({ labelId: item.label.id, decision: 'APPROVED', note: '' })}
            >
              <Check size={14} aria-hidden />
              {t.common.approve}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setRejecting(true)}>
              <X size={14} aria-hidden />
              {t.review.rejectOpen}
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}

export default ReviewRow;
