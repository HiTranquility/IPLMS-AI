import { CheckCircle2, CircleSlash, FileUp, Send } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { TextArea, TextField } from '@/components/common/Ui/form/Field';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/useConsole';
import { useI18n } from '@/i18n/I18nProvider';
import { useIngestDraft, useSystemCheck, useTryCopilot } from '@/hooks/useTools';
import { fmtInt, fmtMs, fmtPercent } from '@/utils/format';
import styles from './ToolsPage.module.css';

function SystemSection() {
  const { t } = useI18n();
  const check = useSystemCheck();
  return (
    <section className={styles.panel} aria-labelledby="system-title">
      <h2 id="system-title" className={styles.title}>{t.tools.systemTitle}</h2>
      <p className={styles.note}>{t.tools.systemNote}</p>
      {check.isPending && <Loading />}
      {check.error && <ErrorBlock error={check.error} onRetry={() => void check.refetch()} />}
      {check.data && (
        <>
          <ul className={styles.checks}>
            {check.data.checks.map((c) => (
              <li key={c.key} className={styles.check}>
                {c.ok ? <CheckCircle2 size={16} className={styles.ok} aria-hidden /> : <CircleSlash size={16} className={styles.missing} aria-hidden />}
                <span>{t.tools.checks[c.key] ?? c.label}</span>
                <span className="visually-hidden">{c.ok ? t.tools.configured : t.tools.notConfigured}</span>
              </li>
            ))}
          </ul>
          <p className={styles.note}>
            {t.tools.llmModel} <span className={styles.mono}>{check.data.llm_model}</span> ·{' '}
            {t.tools.telemetry(check.data.telemetry_enabled, fmtInt(check.data.telemetry_retention_days))} ·{' '}
            {t.tools.a2Retention(fmtInt(check.data.vision_retention_days))} · {t.tools.visionDevice} <span className={styles.mono}>{check.data.vision_device}</span>
          </p>
        </>
      )}
    </section>
  );
}

function CopilotSection() {
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

const newDocumentId = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : '');

function IngestSection() {
  const { t } = useI18n();
  const ingest = useIngestDraft();
  const [documentId, setDocumentId] = useState(newDocumentId);
  const [lot, setLot] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.set('file', file);
    form.set('document_id', documentId.trim());
    if (lot.trim()) form.set('parking_lot_id', lot.trim());
    ingest.mutate(form);
  };

  return (
    <section className={styles.panel} aria-labelledby="ingest-title">
      <h2 id="ingest-title" className={styles.title}>{t.tools.ingestTitle}</h2>
      <p className={styles.note}>{t.tools.ingestNote}</p>
      <form className={styles.form} onSubmit={submit}>
        <TextField label={t.tools.documentId} required pattern="[0-9a-fA-F-]{36}" value={documentId} onChange={(e) => setDocumentId(e.target.value)} />
        <TextField label={t.tools.file} type="file" required accept=".pdf,.docx,.txt,.md,.markdown" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <TextField label={t.tools.lot} hint={t.tools.lotHint} maxLength={128} value={lot} onChange={(e) => setLot(e.target.value)} />
        <div className={styles.actions}>
          <Button type="submit" loading={ingest.isPending} disabled={!file}>
            <FileUp size={16} aria-hidden />
            {t.tools.ingest}
          </Button>
          <Button variant="ghost" onClick={() => setDocumentId(newDocumentId())}>{t.tools.newId}</Button>
        </div>
      </form>
      {ingest.error && <ErrorBlock error={ingest.error} />}
      {ingest.data && (
        <p className={styles.note} role="status">
          {t.tools.ingested(ingest.data.version_no, fmtInt(ingest.data.chunk_count), fmtMs(ingest.data.duration_ms))}
        </p>
      )}
    </section>
  );
}

export function ToolsPage() {
  const { t } = useI18n();
  const canTry = useCan('ai:prompt:edit');
  return (
    <>
      <PageHeader
        title={t.tools.title}
        description={t.tools.desc}
      />
      <div className={styles.layout}>
        <SystemSection />
        {canTry && <CopilotSection />}
        {canTry && <IngestSection />}
      </div>
    </>
  );
}
