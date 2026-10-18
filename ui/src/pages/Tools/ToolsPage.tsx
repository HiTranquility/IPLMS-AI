import { CheckCircle2, CircleSlash, FileUp, Send } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { TextArea, TextField } from '@/components/common/Ui/form/Field';
import { PageHeader } from '@/components/layout/PageHeader';
import { useCan } from '@/hooks/useConsole';
import { useIngestDraft, useSystemCheck, useTryCopilot } from '@/hooks/useTools';
import { fmtInt, fmtMs, fmtPercent } from '@/utils/format';
import styles from './ToolsPage.module.css';

function SystemSection() {
  const check = useSystemCheck();
  return (
    <section className={styles.panel} aria-labelledby="system-title">
      <h2 id="system-title" className={styles.title}>Cấu hình process console</h2>
      <p className={styles.note}>Chỉ báo đã cấu hình hay chưa — không bao giờ hiện giá trị khoá hay URL.</p>
      {check.isPending && <Loading />}
      {check.error && <ErrorBlock error={check.error} onRetry={() => void check.refetch()} />}
      {check.data && (
        <>
          <ul className={styles.checks}>
            {check.data.checks.map((c) => (
              <li key={c.key} className={styles.check}>
                {c.ok ? <CheckCircle2 size={16} className={styles.ok} aria-hidden /> : <CircleSlash size={16} className={styles.missing} aria-hidden />}
                <span>{c.label}</span>
                <span className="visually-hidden">{c.ok ? 'đã cấu hình' : 'chưa cấu hình'}</span>
              </li>
            ))}
          </ul>
          <p className={styles.note}>
            Model LLM <span className={styles.mono}>{check.data.llm_model}</span> · telemetry {check.data.telemetry_enabled ? 'bật' : 'tắt'} (giữ {fmtInt(check.data.telemetry_retention_days)} ngày) · ảnh A2 giữ {fmtInt(check.data.vision_retention_days)} ngày · Vision chạy trên <span className={styles.mono}>{check.data.vision_device}</span>
          </p>
        </>
      )}
    </section>
  );
}

function CopilotSection() {
  const ask = useTryCopilot();
  const [query, setQuery] = useState('');
  const [lot, setLot] = useState('');

  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask.mutate({ query: query.trim(), parkingLotId: lot.trim() });
  };

  return (
    <section className={styles.panel} aria-labelledby="copilot-title">
      <h2 id="copilot-title" className={styles.title}>Hỏi thử Copilot</h2>
      <p className={styles.note}>Chạy pipeline RAG có guard ngay trong process console. Lượt thử ghi telemetry với task <span className={styles.mono}>console_try</span>: thấy trong Copilot Lab, không tính vào số mức dùng sản phẩm.</p>
      <form className={styles.form} onSubmit={submit}>
        <TextArea label="Câu hỏi" required maxLength={2000} rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
        <TextField label="Mã bãi" hint="Để trống: quy chế chung." maxLength={128} value={lot} onChange={(e) => setLot(e.target.value)} />
        <Button type="submit" loading={ask.isPending} disabled={!query.trim()}>
          <Send size={16} aria-hidden />
          Gửi câu hỏi
        </Button>
      </form>
      {ask.error && <ErrorBlock error={ask.error} />}
      {ask.data && (
        <div className={styles.answer} role="status">
          <p className={styles.answerText}>{ask.data.answer}</p>
          <p className={styles.note}>
            Độ tin cậy {fmtPercent(ask.data.confidence)} · prompt <span className={styles.mono}>{ask.data.prompt_version}</span> · lượt <span className={styles.mono}>{ask.data.turn_id}</span>
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
      <h2 id="ingest-title" className={styles.title}>Nạp bản nháp tri thức</h2>
      <p className={styles.note}>Chỉ tạo bản nháp. Xuất bản vẫn qua cổng đánh giá ở trang Kho tri thức của platform. Thử lại thì giữ nguyên mã tài liệu để không tạo tài liệu trùng.</p>
      <form className={styles.form} onSubmit={submit}>
        <TextField label="Mã tài liệu (UUID)" required pattern="[0-9a-fA-F-]{36}" value={documentId} onChange={(e) => setDocumentId(e.target.value)} />
        <TextField label="Tệp PDF, DOCX, TXT hoặc MD (tối đa 8 MB)" type="file" required accept=".pdf,.docx,.txt,.md,.markdown" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <TextField label="Mã bãi" hint="Để trống: quy chế chung." maxLength={128} value={lot} onChange={(e) => setLot(e.target.value)} />
        <div className={styles.actions}>
          <Button type="submit" loading={ingest.isPending} disabled={!file}>
            <FileUp size={16} aria-hidden />
            Nạp bản nháp
          </Button>
          <Button variant="ghost" onClick={() => setDocumentId(newDocumentId())}>Tạo mã mới</Button>
        </div>
      </form>
      {ingest.error && <ErrorBlock error={ingest.error} />}
      {ingest.data && (
        <p className={styles.note} role="status">
          Đã tạo bản nháp v{ingest.data.version_no}: {fmtInt(ingest.data.chunk_count)} đoạn trong {fmtMs(ingest.data.duration_ms)}.
        </p>
      )}
    </section>
  );
}

export function ToolsPage() {
  const canTry = useCan('ai:prompt:edit');
  return (
    <>
      <PageHeader
        title="Công cụ thử"
        description="Thay trang dev /dashboard cũ của process inference (IPLMS ADR-0050). Mọi thao tác chạy trong process console, có quyền và nhật ký."
      />
      <div className={styles.layout}>
        <SystemSection />
        {canTry && <CopilotSection />}
        {canTry && <IngestSection />}
      </div>
    </>
  );
}
