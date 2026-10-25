import {
  Database,
  FileText,
  FileUp,
  RefreshCw,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import { useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { useDeleteKnowledgeDocument, useIngestDraft } from '@/hooks/mutations/useToolMutations';
import { useKnowledgeDocuments } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { ingestDraft } from '@/services/apiEndpoints/tool.endpoint';
import type { SeedDocument } from '@/types/tool';
import { fmtDateTime, fmtInt, fmtMs } from '@/utils/format';
import styles from '../ToolsPage.module.css';

const newDocumentId = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : '');

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export function IngestSection() {
  const { t } = useI18n();
  const ingest = useIngestDraft();
  const deleteMutation = useDeleteKnowledgeDocument();
  const docsQuery = useKnowledgeDocuments();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documentId, setDocumentId] = useState(newDocumentId);
  const [category, setCategory] = useState('regulation');
  const [lot, setLot] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedCatFilter, setSelectedCatFilter] = useState<string>('all');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Trạng thái nạp hàng loạt (Batch Queue)
  const [isBatchIngesting, setIsBatchIngesting] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; name: string } | null>(null);
  const [batchResult, setBatchResult] = useState<{ ok: number; fail: number } | null>(null);
  const [batchError, setBatchError] = useState<unknown | null>(null);

  // Xoá sạch mọi trạng thái lỗi/kết quả cũ khi người dùng thay đổi file hoặc tham số
  const resetStaleState = () => {
    ingest.reset();
    setBatchResult(null);
    setBatchError(null);
    setBatchProgress(null);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    resetStaleState();
    const dropped = Array.from(e.dataTransfer.files || []);
    if (dropped.length > 0) {
      setFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name));
        const newFiles = dropped.filter((f) => !existingNames.has(f.name));
        return [...prev, ...newFiles];
      });
    }
  };

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    resetStaleState();
    const selected = Array.from(e.target.files || []);
    if (selected.length > 0) {
      setFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name));
        const newFiles = selected.filter((f) => !existingNames.has(f.name));
        return [...prev, ...newFiles];
      });
    }
  };

  const removeFile = (index: number) => {
    resetStaleState();
    setFiles((prev) => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const clearAllFiles = () => {
    resetStaleState();
    setFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (files.length === 0) return;
    resetStaleState();

    // Trường hợp 1 tệp: dùng React Query mutation chuẩn để tương thích test
    if (files.length === 1) {
      const form = new FormData();
      form.set('file', files[0]);
      form.set('document_id', documentId.trim());
      form.set('category', category.trim());
      if (lot.trim()) form.set('parking_lot_id', lot.trim());

      ingest.mutate(form, {
        onSuccess: () => {
          setFiles([]);
          if (fileInputRef.current) fileInputRef.current.value = '';
          setDocumentId(newDocumentId());
          void docsQuery.refetch();
        },
      });
      return;
    }

    // Trường hợp nhiều tệp: nạp tuần tự từng tệp theo hàng đợi (Batch Queue)
    setIsBatchIngesting(true);
    let successCount = 0;
    let failCount = 0;
    const remainingFiles: File[] = [];

    for (let i = 0; i < files.length; i++) {
      const currentFile = files[i];
      setBatchProgress({ current: i + 1, total: files.length, name: currentFile.name });

      const form = new FormData();
      form.set('file', currentFile);
      form.set('document_id', i === 0 ? documentId.trim() : newDocumentId());
      form.set('category', category.trim());
      if (lot.trim()) form.set('parking_lot_id', lot.trim());

      try {
        await ingestDraft(form);
        successCount++;
      } catch (err) {
        failCount++;
        remainingFiles.push(currentFile);
        setBatchError(err);
      }
    }

    setIsBatchIngesting(false);
    setBatchProgress(null);
    setBatchResult({ ok: successCount, fail: failCount });
    setFiles(remainingFiles);
    setDocumentId(newDocumentId());
    void docsQuery.refetch();
  };

  const handleDelete = (docId: string) => {
    deleteMutation.mutate({ documentId: docId }, {
      onSettled: () => setConfirmDeleteId(null),
    });
  };

  const docs = docsQuery.data ?? [];
  const filteredDocs = selectedCatFilter === 'all'
    ? docs
    : docs.filter((d: SeedDocument) => d.category === selectedCatFilter);

  const isSubmitting = ingest.isPending || isBatchIngesting;

  return (
    <section className={styles.panel} aria-labelledby="ingest-title">
      <h2 id="ingest-title" className={styles.title}>{t.tools.ingestTitle}</h2>
      <p className={styles.note}>{t.tools.ingestNote}</p>

      <form className={styles.form} onSubmit={submit}>
        <TextField
          label={t.tools.documentId}
          required
          pattern="[0-9a-fA-F-]{36}"
          value={documentId}
          onChange={(e) => {
            resetStaleState();
            setDocumentId(e.target.value);
          }}
        />

        {/* Dropzone Container */}
        <div className={styles.dropzoneContainer}>
          <label htmlFor="knowledge-file-input" className={styles.dropzoneLabel}>
            {t.tools.file}
          </label>
          <input
            id="knowledge-file-input"
            ref={fileInputRef}
            type="file"
            multiple
            required={files.length === 0}
            aria-label={t.tools.file}
            accept=".pdf,.docx,.txt,.md,.markdown"
            onChange={onFileChange}
            className={styles.srOnly}
          />
          <div
            className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ''}`}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                fileInputRef.current?.click();
              }
            }}
          >
            <UploadCloud size={32} className={styles.dropzoneIcon} aria-hidden />
            <p className={styles.dropzonePrompt}>{t.tools.dropPrompt}</p>
            <p className={styles.dropzoneFormats}>{t.tools.dropFormats}</p>
          </div>

          {/* Danh sách tệp trong hàng đợi */}
          {files.length > 0 && (
            <div className={styles.fileList}>
              <div className={styles.fileQueueHeader}>
                <span className={styles.fileQueueTitle}>
                  {files.length === 1 ? t.tools.fileSelected : t.tools.filesSelected(files.length)}
                </span>
                {files.length > 1 && (
                  <button type="button" className={styles.clearQueueBtn} onClick={clearAllFiles}>
                    {t.tools.clearAllFiles}
                  </button>
                )}
              </div>

              {files.map((f, idx) => (
                <div key={`${f.name}-${idx}`} className={styles.fileBadge}>
                  <div className={styles.fileBadgeInfo}>
                    <FileText size={16} aria-hidden />
                    <span className={styles.fileName}>{f.name}</span>
                    <span className={styles.fileSize}>({formatFileSize(f.size)})</span>
                  </div>
                  <button
                    type="button"
                    className={styles.removeFileBtn}
                    onClick={() => removeFile(idx)}
                    aria-label={t.tools.removeFile}
                    title={t.tools.removeFile}
                    disabled={isSubmitting}
                  >
                    <X size={16} aria-hidden />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <SelectField
          label={t.tools.category}
          value={category}
          onChange={(e) => {
            resetStaleState();
            setCategory(e.target.value);
          }}
        >
          <option value="regulation">{t.tools.catRegulation}</option>
          <option value="tariff">{t.tools.catTariff}</option>
          <option value="fine_policy">{t.tools.catFine}</option>
          <option value="ev_charging">{t.tools.catEv}</option>
        </SelectField>

        <TextField
          label={t.tools.lot}
          hint={t.tools.lotHint}
          maxLength={128}
          value={lot}
          onChange={(e) => {
            resetStaleState();
            setLot(e.target.value);
          }}
        />

        {batchProgress && (
          <div className={styles.batchProgressBar}>
            <RefreshCw size={14} className={styles.spinning} aria-hidden />
            <span>{t.tools.batchIngestProgress(batchProgress.current, batchProgress.total, batchProgress.name)}</span>
          </div>
        )}

        <div className={styles.actions}>
          <Button type="submit" loading={isSubmitting} disabled={files.length === 0}>
            <FileUp size={16} aria-hidden />
            {files.length > 1 ? t.tools.ingestAll(files.length) : t.tools.ingest}
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              resetStaleState();
              setDocumentId(newDocumentId());
            }}
          >
            {t.tools.newId}
          </Button>
        </div>
      </form>

      {/* Lỗi nạp đơn lẻ */}
      {ingest.error ? <ErrorBlock error={ingest.error} /> : null}

      {/* Lỗi nạp theo lô */}
      {batchError ? <ErrorBlock error={batchError} /> : null}

      {/* Kết quả nạp đơn lẻ */}
      {ingest.data && (
        <p className={styles.note} role="status">
          {t.tools.ingested(ingest.data.version_no, fmtInt(ingest.data.chunk_count), fmtMs(ingest.data.duration_ms))}
        </p>
      )}

      {/* Kết quả nạp theo lô */}
      {batchResult && (
        <p className={batchResult.fail === 0 ? styles.note : styles.note} role="status">
          {batchResult.fail === 0
            ? t.tools.batchIngestSuccess(batchResult.ok)
            : t.tools.batchIngestPartial(batchResult.ok, batchResult.fail)}
        </p>
      )}

      {/* ── Knowledge Document Management List ── */}
      <div className={styles.docManagement}>
        <div className={styles.docHeader}>
          <div className={styles.docTitleWrap}>
            <Database size={16} aria-hidden />
            <h3 className={styles.title}>{t.tools.docsListTitle}</h3>
            <span className={styles.docCountBadge}>{docs.length}</span>
          </div>

          <div className={styles.catFilterBar}>
            {['all', 'regulation', 'tariff', 'fine_policy', 'ev_charging'].map((cat) => (
              <button
                key={cat}
                type="button"
                className={`${styles.catFilterBtn} ${selectedCatFilter === cat ? styles.catFilterBtnActive : ''}`}
                onClick={() => setSelectedCatFilter(cat)}
              >
                {cat === 'all'
                  ? t.tools.tabAll
                  : cat === 'regulation'
                  ? t.tools.catRegulation.split(' ')[0]
                  : cat === 'tariff'
                  ? t.tools.catTariff.split(' ')[0]
                  : cat === 'fine_policy'
                  ? t.tools.catFine.split(' ')[0]
                  : t.tools.catEv.split(' ')[0]}
              </button>
            ))}
            <button
              type="button"
              className={styles.catFilterBtn}
              onClick={() => void docsQuery.refetch()}
              title={t.tools.refreshStatus}
            >
              <RefreshCw size={12} aria-hidden />
            </button>
          </div>
        </div>

        <p className={styles.note}>{t.tools.docsListNote}</p>

        {docsQuery.isPending && <Loading />}
        {docsQuery.error && <ErrorBlock error={docsQuery.error} onRetry={() => void docsQuery.refetch()} />}

        {deleteMutation.error && <ErrorBlock error={deleteMutation.error} />}

        {docsQuery.data && (
          <div className={styles.docTableWrapper}>
            {filteredDocs.length === 0 ? (
              <p className={styles.emptyDocs}>{t.tools.noDocs}</p>
            ) : (
              <table className={styles.docTable}>
                <thead>
                  <tr>
                    <th className={styles.docTh}>{t.tools.colTitle}</th>
                    <th className={styles.docTh}>{t.tools.colCategory}</th>
                    <th className={styles.docTh}>{t.tools.colChunks}</th>
                    <th className={styles.docTh}>{t.tools.colVersion}</th>
                    <th className={styles.docTh}>{t.tools.colStatus}</th>
                    <th className={styles.docTh}>{t.tools.colUpdated}</th>
                    <th className={styles.docTh}>{t.tools.colActions}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocs.map((doc: SeedDocument) => {
                    const isPublished = doc.latest_status === 'PUBLISHED';
                    const docId = doc.id || '';
                    const isConfirming = confirmDeleteId === docId;

                    return (
                      <tr key={docId || doc.title} className={styles.docRow}>
                        <td className={styles.docTd}>
                          <div className={styles.docNameCell}>
                            <FileText size={14} color="var(--color-accent)" aria-hidden />
                            <span title={doc.title}>{doc.title}</span>
                          </div>
                        </td>
                        <td className={styles.docTd}>
                          <span className={styles.badgeCategory}>{doc.category}</span>
                        </td>
                        <td className={styles.docTd}>{fmtInt(doc.chunk_count || 0)}</td>
                        <td className={styles.docTd}>v{doc.latest_version_no || 1}</td>
                        <td className={styles.docTd}>
                          <span
                            className={`${styles.badgeStatus} ${
                              isPublished ? styles.statusPublished : styles.statusDraft
                            }`}
                          >
                            {doc.latest_status || 'DRAFT'}
                          </span>
                        </td>
                        <td className={styles.docTd}>{doc.updated_at ? fmtDateTime(doc.updated_at) : '—'}</td>
                        <td className={styles.docTd}>
                          {isConfirming ? (
                            <div className={styles.confirmWrap}>
                              <button
                                type="button"
                                className={styles.confirmBtn}
                                onClick={() => handleDelete(docId)}
                                disabled={deleteMutation.isPending}
                              >
                                {deleteMutation.isPending ? t.tools.deleting : t.tools.deleteDoc}
                              </button>
                              <button
                                type="button"
                                className={styles.cancelBtn}
                                onClick={() => setConfirmDeleteId(null)}
                                disabled={deleteMutation.isPending}
                              >
                                {t.tools.close}
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              className={styles.delBtn}
                              onClick={() => setConfirmDeleteId(docId)}
                              aria-label={`${t.tools.deleteDoc} ${doc.title}`}
                            >
                              <Trash2 size={13} aria-hidden />
                              <span>{t.tools.deleteDoc}</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default IngestSection;
