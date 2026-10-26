import {
  BookOpen,
  Database,
  Eye,
  FileText,
  FileUp,
  Layers,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import { useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextField } from '@/components/common/Ui/form/Field';
import { PageHeader } from '@/components/layout/PageHeader';
import { useDeleteKnowledgeDocument, useIngestDraft } from '@/hooks/mutations/useToolMutations';
import { useKnowledgeDocuments } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { ingestDraft } from '@/services/apiEndpoints/tool.endpoint';
import type { SeedDocument } from '@/types/tool';
import { fmtDateTime, fmtInt, fmtMs } from '@/utils/format';
import { DocumentPreviewDrawer } from './components/DocumentPreviewDrawer';
import styles from './KnowledgePage.module.css';

const newDocumentId = () => (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : '');

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export function KnowledgePage() {
  const { t } = useI18n();
  const kp = t.knowledgePage;
  const ingest = useIngestDraft();
  const deleteMutation = useDeleteKnowledgeDocument();
  const docsQuery = useKnowledgeDocuments();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [documentId, setDocumentId] = useState(newDocumentId);
  const [category, setCategory] = useState('regulation');
  const [lot, setLot] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCatFilter, setSelectedCatFilter] = useState('all');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<SeedDocument | null>(null);

  // Batch queue state
  const [isBatchIngesting, setIsBatchIngesting] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; name: string } | null>(null);
  const [batchResult, setBatchResult] = useState<{ ok: number; fail: number } | null>(null);
  const [batchError, setBatchError] = useState<unknown | null>(null);

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

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (files.length === 0 || isBatchIngesting) return;

    if (files.length === 1) {
      const form = new FormData();
      form.append('document_id', documentId);
      form.append('category', category);
      if (lot.trim()) form.append('parking_lot_id', lot.trim());
      form.append('file', files[0]);
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

    // Nạp hàng loạt
    setIsBatchIngesting(true);
    setBatchError(null);
    setBatchResult(null);
    let okCount = 0;
    let failCount = 0;

    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      setBatchProgress({ current: i + 1, total: files.length, name: f.name });
      const form = new FormData();
      form.append('document_id', newDocumentId());
      form.append('category', category);
      if (lot.trim()) form.append('parking_lot_id', lot.trim());
      form.append('file', f);

      try {
        await ingestDraft(form);
        okCount++;
      } catch (err) {
        failCount++;
        setBatchError(err);
      }
    }

    setIsBatchIngesting(false);
    setBatchProgress(null);
    setBatchResult({ ok: okCount, fail: failCount });
    if (okCount > 0) {
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setDocumentId(newDocumentId());
      void docsQuery.refetch();
    }
  };

  const handleDelete = (docId: string) => {
    deleteMutation.mutate(
      { documentId: docId },
      {
        onSuccess: () => {
          setConfirmDeleteId(null);
          if (previewDoc?.id === docId || previewDoc?.document_id === docId) {
            setPreviewDoc(null);
          }
          void docsQuery.refetch();
        },
      },
    );
  };

  const docs = docsQuery.data || [];
  const totalChunks = docs.reduce((acc, d) => acc + (d.chunk_count || 0), 0);

  const filteredDocs = docs.filter((d) => {
    const matchesCat = selectedCatFilter === 'all' || d.category === selectedCatFilter;
    const name = (d.title || d.source || '').toLowerCase();
    const id = (d.id || d.document_id || '').toLowerCase();
    const term = searchTerm.toLowerCase();
    const matchesSearch = !term || name.includes(term) || id.includes(term);
    return matchesCat && matchesSearch;
  });

  const categories = [
    { value: 'regulation', label: t.tools.catRegulation },
    { value: 'tariff', label: t.tools.catTariff },
    { value: 'fine_policy', label: t.tools.catFine },
    { value: 'dispute_resolution', label: kp.catDispute },
  ];

  return (
    <div className={styles.pageContainer}>
      <PageHeader
        title={kp.title}
        description={kp.desc}
        actions={
          <Button
            variant="secondary"
            onClick={() => void docsQuery.refetch()}
            loading={docsQuery.isFetching}
          >
            <RefreshCw size={15} style={{ marginRight: '0.4rem', verticalAlign: 'middle' }} />
            {t.tools.refreshStatus}
          </Button>
        }
      />

      {/* Stats Counter Bar */}
      <section className={styles.statsGrid} aria-label={kp.statsAria}>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>
            <FileText size={22} aria-hidden />
          </div>
          <div className={styles.statDetails}>
            <span className={styles.statLabel}>{kp.statsDocs}</span>
            <p className={styles.statValue}>{fmtInt(docs.length)}</p>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#10b981' }}>
            <Layers size={22} aria-hidden />
          </div>
          <div className={styles.statDetails}>
            <span className={styles.statLabel}>{kp.statsChunks}</span>
            <p className={styles.statValue}>{fmtInt(totalChunks)}</p>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon} style={{ background: 'rgba(245, 158, 11, 0.12)', color: '#f59e0b' }}>
            <Database size={22} aria-hidden />
          </div>
          <div className={styles.statDetails}>
            <span className={styles.statLabel}>{kp.statDbVector}</span>
            <p className={styles.statValue} style={{ fontSize: '1.05rem', color: '#10b981' }}>
              pgvector (768 dims)
            </p>
          </div>
        </div>
      </section>

      {/* Main Layout: Left Upload Form & Right Documents Table */}
      <div className={styles.layoutGrid}>
        {/* Upload Column */}
        <section className={styles.uploadCard}>
          <h2 className={styles.sectionTitle}>
            <UploadCloud size={18} aria-hidden />
            <span>{kp.uploadTitle}</span>
          </h2>
          <p className={styles.sectionDesc}>{kp.uploadDesc}</p>

          <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
            <TextField
              label={t.tools.documentId}
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              required
            />

            {/* Drag & Drop Dropzone */}
            <div
              className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ''}`}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
            >
              <FileUp size={28} className={styles.dropzoneIcon} aria-hidden />
              <span className={styles.dropzoneText}>{kp.dropzonePlaceholder}</span>
              <span className={styles.dropzoneSubtext}>{kp.dropzoneHint}</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md,.markdown"
                multiple
                style={{ display: 'none' }}
                onChange={onFileChange}
                aria-label={t.tools.file}
              />
            </div>

            {/* Selected File Chips */}
            {files.length > 0 && (
              <div className={styles.fileChipList}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {kp.filesSelected(files.length)}
                  </span>
                  <button
                    type="button"
                    onClick={clearAllFiles}
                    style={{ background: 'transparent', border: 'none', color: '#ef4444', fontSize: '0.75rem', cursor: 'pointer' }}
                  >
                    {kp.clearAll}
                  </button>
                </div>
                {files.map((file, idx) => (
                  <div key={`${file.name}-${idx}`} className={styles.fileChip}>
                    <div className={styles.fileChipName} title={file.name}>
                      <FileText size={14} color="#60a5fa" />
                      <span>{file.name}</span>
                      <span style={{ fontSize: '0.7rem', color: '#64748b' }}>({formatFileSize(file.size)})</span>
                    </div>
                    <button
                      type="button"
                      className={styles.removeFileBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(idx);
                      }}
                      aria-label={kp.removeFileAria(file.name)}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <SelectField
              label={t.tools.category}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {categories.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </SelectField>

            <TextField
              label={t.tools.lot}
              value={lot}
              onChange={(e) => setLot(e.target.value)}
              placeholder={kp.lotScopePlaceholder}
            />

            {/* Batch Progress Bar */}
            {isBatchIngesting && batchProgress && (
              <div className={styles.progressContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.775rem', color: '#94a3b8' }}>
                  <span>{kp.batchIngesting(batchProgress.name)}</span>
                  <span>{batchProgress.current}/{batchProgress.total}</span>
                </div>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${(batchProgress.current / batchProgress.total) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Messages & Error States */}
            {ingest.error && <ErrorBlock error={ingest.error} />}
            {Boolean(batchError) && <ErrorBlock error={batchError} />}

            {ingest.data && (
              <div style={{ padding: '0.75rem', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#34d399', fontSize: '0.825rem' }}>
                ✓ {kp.singleSuccess(ingest.data.version_no, ingest.data.chunk_count, fmtMs(ingest.data.duration_ms))}
              </div>
            )}

            {batchResult && (
              <div style={{ padding: '0.75rem', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', color: '#60a5fa', fontSize: '0.825rem' }}>
                {kp.batchSummary(batchResult.ok, batchResult.fail)}
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
              <Button
                type="submit"
                variant="primary"
                loading={ingest.isPending || isBatchIngesting}
                disabled={files.length === 0}
              >
                {files.length > 1 ? kp.btnBatchIngest(files.length) : t.tools.ingest}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setDocumentId(newDocumentId());
                  resetStaleState();
                }}
              >
                {t.tools.newId}
              </Button>
            </div>
          </form>
        </section>

        {/* Documents Management Table Column */}
        <section className={styles.tableCard}>
          <div className={styles.tableControls}>
            <h2 className={styles.sectionTitle}>
              <BookOpen size={18} aria-hidden />
              <span>{kp.docListTitle}</span>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 'normal' }}>
                {kp.totalDocsCount(filteredDocs.length)}
              </span>
            </h2>

            <div style={{ display: 'flex', gap: '0.75rem', flex: 1, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <div className={styles.searchBox}>
                <Search size={15} color="#64748b" aria-hidden />
                <input
                  type="text"
                  placeholder={kp.searchPlaceholder}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>

              <select
                value={selectedCatFilter}
                onChange={(e) => setSelectedCatFilter(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid var(--border-color, #2a2e3d)',
                  borderRadius: '6px',
                  color: 'var(--text-primary, #f1f5f9)',
                  padding: '0.4rem 0.6rem',
                  fontSize: '0.825rem',
                }}
              >
                <option value="all">{kp.filterAll}</option>
                <option value="regulation">{t.tools.catRegulation}</option>
                <option value="tariff">{t.tools.catTariff}</option>
                <option value="fine_policy">{t.tools.catFine}</option>
                <option value="dispute_resolution">{kp.catDispute}</option>
              </select>
            </div>
          </div>

          {docsQuery.isPending && <Loading label={kp.loadingDocs} />}
          {docsQuery.error && <ErrorBlock error={docsQuery.error} onRetry={() => void docsQuery.refetch()} />}

          {!docsQuery.isPending && !docsQuery.error && filteredDocs.length === 0 && (
            <EmptyState
              icon={<Database size={32} />}
              title={kp.noDocs}
              description={searchTerm ? kp.emptyFilterDesc : kp.emptyNoDocsDesc}
            />
          )}

          {!docsQuery.isPending && !docsQuery.error && filteredDocs.length > 0 && (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>{kp.colName}</th>
                    <th>{kp.colCategory}</th>
                    <th>{kp.colChunks}</th>
                    <th>{kp.colVersion}</th>
                    <th>{kp.colStatus}</th>
                    <th>{kp.colUpdated}</th>
                    <th>{kp.colActions}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocs.map((doc) => {
                    const id = doc.id || doc.document_id || '';
                    const isConfirming = confirmDeleteId === id;
                    const statusTone = doc.latest_status === 'PUBLISHED' ? 'success' : 'warning';

                    return (
                      <tr key={id}>
                        <td>
                          <div className={styles.docTitleCell}>
                            <button
                              type="button"
                              className={styles.docTitle}
                              onClick={() => setPreviewDoc(doc)}
                              style={{ background: 'transparent', border: 'none', padding: 0, textAlign: 'left' }}
                            >
                              {doc.title || doc.source}
                            </button>
                            <span className={styles.docId} title={id}>
                              {id}
                            </span>
                          </div>
                        </td>
                        <td>
                          <Badge tone="neutral">{doc.category}</Badge>
                        </td>
                        <td>
                          <span style={{ fontWeight: 600 }}>{fmtInt(doc.chunk_count)}</span>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>v{doc.latest_version_no || 1}</span>
                        </td>
                        <td>
                          <Badge tone={statusTone}>{doc.latest_status || 'DRAFT'}</Badge>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.8rem', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                            {doc.updated_at ? fmtDateTime(doc.updated_at) : '—'}
                          </span>
                        </td>
                        <td>
                          <div className={styles.actionCell}>
                            <button
                              type="button"
                              className={styles.previewBtn}
                              onClick={() => setPreviewDoc(doc)}
                              title={kp.btnPreviewTitle}
                            >
                              <Eye size={13} aria-hidden />
                              <span>{kp.btnPreview}</span>
                            </button>

                            {isConfirming ? (
                              <div style={{ display: 'inline-flex', gap: '0.3rem', alignItems: 'center' }}>
                                <Button
                                  variant="danger"
                                  onClick={() => handleDelete(id)}
                                  loading={deleteMutation.isPending}
                                >
                                  {kp.confirmBtn}
                                </Button>
                                <Button
                                  variant="secondary"
                                  onClick={() => setConfirmDeleteId(null)}
                                >
                                  {kp.cancelBtn}
                                </Button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                className={styles.deleteBtn}
                                onClick={() => setConfirmDeleteId(id)}
                                title={kp.btnDelete}
                                aria-label={kp.deleteDocAria(doc.title || doc.source)}
                              >
                                <Trash2 size={13} aria-hidden />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* Document Chunks Slide-Over Preview Drawer */}
      <DocumentPreviewDrawer
        document={previewDoc}
        onClose={() => setPreviewDoc(null)}
      />
    </div>
  );
}

export default KnowledgePage;
