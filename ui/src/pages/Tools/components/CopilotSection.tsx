import { Send } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextArea, TextField } from '@/components/common/Ui/form/Field';
import { useTryCopilot } from '@/hooks/mutations/useToolMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtPercent } from '@/utils/format';
import styles from '../ToolsPage.module.css';

export function CopilotSection() {
  const { t } = useI18n();
  const ask = useTryCopilot();
  const [query, setQuery] = useState('');
  const [lot, setLot] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask.mutate({ query: query.trim(), parkingLotId: lot.trim() });
  };

  return (
    <section className={styles.panel} aria-labelledby="copilot-title">
      <h2 id="copilot-title" className={styles.title}>{t.tools.copilotTitle}</h2>
      <p className={styles.note}>{t.tools.copilotNote.before}<span className={styles.mono}>console_try</span>{t.tools.copilotNote.after}</p>
      <form className={styles.form} onSubmit={submit}>
        <TextArea label={t.tools.question} required maxLength={2000} rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
        <TextField label={t.tools.lot} hint={t.tools.lotHint} maxLength={128} value={lot} onChange={(e) => setLot(e.target.value)} />
        <Button type="submit" loading={ask.isPending} disabled={!query.trim()}>
          <Send size={16} aria-hidden />
          {t.tools.send}
        </Button>
      </form>
      {ask.error && <ErrorBlock error={ask.error} />}
      {ask.data && (
        <div className={styles.answer} role="status">
          <p className={styles.answerText}>{ask.data.answer}</p>
          <p className={styles.note}>
            {t.tools.confidence(fmtPercent(ask.data.confidence))} · {t.tools.prompt} <span className={styles.mono}>{ask.data.prompt_version}</span> · {t.tools.turn}{' '}
            <span className={styles.mono}>{ask.data.turn_id}</span>
          </p>
          {ask.data.sources.length > 0 && (
            <div className={styles.sources}>
              {ask.data.sources.map((s) => <Badge key={s}>{s}</Badge>)}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default CopilotSection;
