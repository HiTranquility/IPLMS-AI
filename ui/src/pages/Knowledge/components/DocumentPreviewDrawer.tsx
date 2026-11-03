import { Check, Copy, FileText, Layers, Search, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { EmptyState } from '@/components/common/Ui/feedback/EmptyState';
import { ErrorBlock, Loading } from '@/components/common/Ui/feedback/LoadState';
import { useDocumentChunks } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import type { SeedDocument } from '@/types/tool';
import { fmtDateTime } from '@/utils/format';
import styles from './DocumentPreviewDrawer.module.css';

export interface DocumentPreviewDrawerProps {
  document: SeedDocument | null;
  onClose: () => void;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function DocumentPreviewDrawer({ document, onClose }: DocumentPreviewDrawerProps) {
  const { t } = useI18n();
  const kp = t.knowledgePage;
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedOrdinal, setCopiedOrdinal] = useState<number | null>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const docId = document?.id || document?.document_id || '';
  const parkingLotId = document?.parking_lot_id || undefined;
  const isOpen = Boolean(document);

  const { data, isLoading, error, refetch } = useDocumentChunks(docId, parkingLotId);

  // AUDIT-007 B5: Lưu trigger element khi mở, chuyển focus vào nút đóng, giữ focus trong drawer (Tab) và trả focus khi đóng
  useEffect(() => {
    if (!isOpen) return;
    const triggerEl =
      globalThis.document.activeElement instanceof HTMLElement
        ? globalThis.document.activeElement
        : null;
    closeBtnRef.current?.focus();

    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCloseRef.current();
        return;
      }
      if (e.key === 'Tab' && drawerRef.current) {
        const focusable = Array.from(drawerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && globalThis.document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && globalThis.document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      triggerEl?.focus();
    };
  }, [isOpen]);

  if (!document) return null;

  const chunks = data?.chunks || [];
  const filteredChunks = chunks.filter((c) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return c.section_title.toLowerCase().includes(term) || c.content.toLowerCase().includes(term);
  });

  const handleCopyChunk = async (ordinal: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedOrdinal(ordinal);
      setTimeout(() => setCopiedOrdinal(null), 2000);
    } catch {
      // Bỏ qua lỗi copy nếu clipboard API bị hạn chế
    }
  };

  const statusTone = document.latest_status === 'PUBLISHED' ? 'success' : 'warning';

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <aside
        ref={drawerRef}
        className={styles.drawer}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-doc-title"
      >
        <header className={styles.header}>
          <div className={styles.headerInfo}>
            <div className={styles.titleRow}>
              <h2 id="preview-doc-title" className={styles.title}>
                {document.title || document.source || kp.defaultDocTitle}
              </h2>
              <Badge tone={statusTone}>{document.latest_status || 'DRAFT'}</Badge>
              {data && <Badge tone="neutral">v{data.version_no}</Badge>}
            </div>
            <div className={styles.metaRow}>
              <span className={styles.metaItem}>
                <span>{kp.previewDocId}</span>
                <code className={styles.codeId}>{docId}</code>
              </span>
              <span className={styles.metaItem}>
                <Layers size={13} aria-hidden />
                <span>
                  {data?.total ?? document.chunk_count} {kp.colChunks.toLowerCase()}
                </span>
              </span>
              {document.updated_at && (
                <span className={styles.metaItem}>
                  <span>{fmtDateTime(document.updated_at)}</span>
                </span>
              )}
            </div>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            className={styles.closeBtn}
            onClick={onClose}
            aria-label={kp.closeDrawerAria}
          >
            <X size={20} />
          </button>
        </header>

        <div className={styles.filterBar}>
          <div className={styles.searchInputWrapper}>
            <Search size={15} className={styles.searchIcon} aria-hidden />
            <input
              type="text"
              className={styles.searchInput}
              placeholder={kp.searchChunksPlaceholder}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className={styles.body}>
          {isLoading && <Loading label={kp.loadingChunks} />}
          {error && !document.content && <ErrorBlock error={error} onRetry={() => void refetch()} />}

          {!isLoading && (!error || document.content) && filteredChunks.length === 0 && (
            document.content ? (
              <article className={styles.chunkCard}>
                <div className={styles.chunkHeader}>
                  <div className={styles.chunkHeaderLeft}>
                    <span className={styles.ordinalBadge}>{kp.chunkOrdinal(1)}</span>
                    <span className={styles.chunkTitle}>
                      {document.title || kp.defaultChunkTitle}
                    </span>
                  </div>
                  <div className={styles.chunkHeaderRight}>
                    <span className={styles.charCount}>{kp.chunkLength(document.content.length)}</span>
                    <button
                      type="button"
                      className={styles.copyBtn}
                      onClick={() => void handleCopyChunk(0, document.content || '')}
                    >
                      {copiedOrdinal === 0 ? (
                        <>
                          <Check size={12} className={styles.copiedIcon} />
                          <span>{kp.copied}</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} />
                          <span>{kp.copyChunk}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
                <pre className={styles.chunkContent}>{document.content}</pre>
              </article>
            ) : (
              <EmptyState
                icon={<FileText size={32} />}
                title={kp.emptyChunksTitle}
                description={searchTerm ? kp.noChunksFound : kp.emptyChunksDesc}
              />
            )
          )}

          {!isLoading &&
            !error &&
            filteredChunks.map((chunk) => (
              <article key={chunk.ordinal} className={styles.chunkCard}>
                <div className={styles.chunkHeader}>
                  <div className={styles.chunkHeaderLeft}>
                    <span className={styles.ordinalBadge}>{kp.chunkOrdinal(chunk.ordinal + 1)}</span>
                    <span className={styles.chunkTitle} title={chunk.section_title}>
                      {chunk.section_title || kp.defaultChunkTitle}
                    </span>
                  </div>
                  <div className={styles.chunkHeaderRight}>
                    <span className={styles.charCount}>{kp.chunkLength(chunk.content.length)}</span>
                    <button
                      type="button"
                      className={styles.copyBtn}
                      onClick={() => void handleCopyChunk(chunk.ordinal, chunk.content)}
                    >
                      {copiedOrdinal === chunk.ordinal ? (
                        <>
                          <Check size={12} className={styles.copiedIcon} />
                          <span>{kp.copied}</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} />
                          <span>{kp.copyChunk}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
                <pre className={styles.chunkContent}>{chunk.content}</pre>
              </article>
            ))}
        </div>
      </aside>
    </div>
  );
}
