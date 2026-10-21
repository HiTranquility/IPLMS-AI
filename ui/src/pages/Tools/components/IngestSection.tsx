import { FileUp } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextField } from '@/components/common/Ui/form/Field';
import { useIngestDraft } from '@/hooks/mutations/useToolMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt, fmtMs } from '@/utils/format';
import styles from '../ToolsPage.module.css';

const newDocumentId = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : '');

export function IngestSection() {
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

export default IngestSection;
