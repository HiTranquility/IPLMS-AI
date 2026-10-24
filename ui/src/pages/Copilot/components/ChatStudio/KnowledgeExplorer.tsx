import { type ChangeEvent, type FormEvent, useEffect, useState } from 'react';
import {
  BookOpen,
  Check,
  Copy,
  Database,
  FileText,
  FileUp,
  Filter,
  Layers,
  MessageSquare,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { useI18n } from '@/i18n/I18nProvider';
import { getKnowledgeSeeds } from '@/services/apiEndpoints/studio.endpoint';
import { ingestDraft } from '@/services/apiEndpoints/tool.endpoint';
import type { KnowledgeCategory, SeedDocument } from './types';
import styles from './ChatStudio.module.css';

export interface KnowledgeExplorerProps {
  onAskAboutDocument?: (doc: SeedDocument) => void;
  onInsertCitation?: (citationText: string) => void;
}

export function KnowledgeExplorer({ onAskAboutDocument, onInsertCitation }: KnowledgeExplorerProps) {
  const { t } = useI18n();
  const k = t.copilot.knowledge;
  const categoryLabels: Record<string, string> = {
    all: k.catAll,
    regulation: k.catRegulation,
    tariff: k.catTariff,
    fine_policy: k.catFine,
    ev_charging: k.catEv,
  };
  // Chỉ hiện văn bản server trả; API lỗi thì danh sách rỗng + báo lỗi, không thay bằng bộ mẫu (ai bug-018).
  const [documents, setDocuments] = useState<SeedDocument[]>([]);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<KnowledgeCategory>('all');
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [ingestOpen, setIngestOpen] = useState(false);

  // Ingestion form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [ingestCategory, setIngestCategory] = useState('regulation');
  const [lotScope, setLotScope] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<{ ok: boolean; msg: string } | null>(null);

  const loadDocuments = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      setDocuments(await getKnowledgeSeeds());
    } catch (err) {
      setDocuments([]);
      setLoadError(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  // Lọc danh sách theo Category & Search query
  const filteredDocuments = documents.filter((doc) => {
    const matchesCategory =
      selectedCategory === 'all' || doc.category.toLowerCase() === selectedCategory.toLowerCase();
    const query = searchQuery.trim().toLowerCase();
    const matchesQuery =
      !query ||
      doc.title.toLowerCase().includes(query) ||
      (doc.content ?? '').toLowerCase().includes(query) ||
      doc.source.toLowerCase().includes(query);
    return matchesCategory && matchesQuery;
  });

  const getCategoryCount = (cat: KnowledgeCategory) => {
    if (cat === 'all') return documents.length;
    return documents.filter((d) => d.category.toLowerCase() === cat.toLowerCase()).length;
  };

  const handleCopyCitation = (doc: SeedDocument) => {
    const text = `${k.citationText(doc.title, doc.source)}\n${doc.content ?? ''}`;
    navigator.clipboard?.writeText(text);
    setCopiedId(doc.id || doc.title);
    setTimeout(() => setCopiedId(null), 2000);
    onInsertCitation?.(text);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setIngestStatus(null);
    }
  };

  const handleSubmitIngestion = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setIngestStatus({ ok: false, msg: k.pickFile });
      return;
    }

    setIsIngesting(true);
    setIngestStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      // Server đòi UUID và giữ nguyên mã khi thử lại (tools_service.ingest_draft).
      formData.append('document_id', crypto.randomUUID());
      formData.append('category', ingestCategory);
      if (lotScope.trim()) {
        formData.append('parking_lot_id', lotScope.trim());
      }
      const result = await ingestDraft(formData);
      setIngestStatus({ ok: true, msg: t.studio.ingestOk(selectedFile.name) + (result.message ? ` ${result.message}` : '') });
      setSelectedFile(null);
      loadDocuments();
    } catch (err) {
      setIngestStatus({ ok: false, msg: err instanceof Error ? err.message : t.errors.network });
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div className={styles.knowledgeExplorerWrapper}>
      {/* 1. Header & Stats */}
      <div className={styles.keHeader}>
        <div className={styles.keTitleGroup}>
          <div className={styles.keIconBox}>
            <Database size={16} />
          </div>
          <div>
            <h4 className={styles.keTitle}>{k.title}</h4>
            <span className={styles.keSub}>
              {t.studio.knowledgeCount(documents.length)}
            </span>
          </div>
        </div>

        <div className={styles.keActions}>
          <button
            type="button"
            className={`${styles.keActionBtn} ${ingestOpen ? styles.keActionBtnActive : ''}`}
            onClick={() => setIngestOpen((v) => !v)}
            title={k.ingestTitle}
            aria-label={k.ingestAria}
          >
            <FileUp size={14} />
            <span>{k.ingestBtn}</span>
          </button>

          <button
            type="button"
            className={styles.keActionBtn}
            onClick={loadDocuments}
            disabled={isLoading}
            title={k.refreshTitle}
            aria-label={k.refreshAria}
          >
            <RefreshCw size={13} className={isLoading ? styles.spin : ''} />
          </button>
        </div>
      </div>

      {loadError !== null && <ErrorBlock error={loadError} onRetry={loadDocuments} />}

      {/* 2. Ingestion Card (Collapsible) */}
      {ingestOpen && (
        <form onSubmit={handleSubmitIngestion} className={styles.ingestCard}>
          <div className={styles.ingestHeader}>
            <span className={styles.ingestTitle}>
              <Layers size={14} /> {k.ingestHeader}
            </span>
            <button
              type="button"
              className={styles.keCloseBtn}
              onClick={() => setIngestOpen(false)}
              aria-label={k.closeIngest}
            >
              <X size={13} />
            </button>
          </div>

          <label className={styles.dropzone}>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              className={styles.hiddenInput}
              onChange={handleFileChange}
            />
            <FileText size={22} className={styles.dropzoneIcon} />
            <span className={styles.dropzoneLabel}>
              {selectedFile ? selectedFile.name : k.choosePrompt}
            </span>
            <span className={styles.dropzoneHint}>{k.fileHint}</span>
          </label>

          <div className={styles.ingestInputsGrid}>
            <div className={styles.ingestField}>
              <label htmlFor="ingest-category" className={styles.ingestLabel}>
                {k.category}
              </label>
              <select
                id="ingest-category"
                className={styles.selectInput}
                value={ingestCategory}
                onChange={(e) => setIngestCategory(e.target.value)}
              >
                <option value="regulation">{k.optRegulation}</option>
                <option value="tariff">{k.optTariff}</option>
                <option value="fine_policy">{k.optFine}</option>
                <option value="ev_charging">{k.optEv}</option>
              </select>
            </div>

            <div className={styles.ingestField}>
              <label htmlFor="ingest-scope" className={styles.ingestLabel}>
                {k.scope}
              </label>
              <input
                id="ingest-scope"
                type="text"
                placeholder={k.scopePlaceholder}
                className={styles.textInput}
                value={lotScope}
                onChange={(e) => setLotScope(e.target.value)}
              />
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={isIngesting || !selectedFile}
            className={styles.ingestSubmitBtn}
          >
            <Sparkles size={13} />
            <span>{isIngesting ? k.ingesting : k.ingestSubmit}</span>
          </Button>

          {ingestStatus && (
            <div
              className={`${styles.ingestStatusBanner} ${
                ingestStatus.ok ? styles.ingestStatusSuccess : styles.ingestStatusError
              }`}
            >
              {ingestStatus.msg}
            </div>
          )}
        </form>
      )}

      {/* 3. Search Bar */}
      <div className={styles.keSearchRow}>
        <div className={styles.searchBox}>
          <Search size={14} className={styles.searchIcon} />
          <input
            type="text"
            className={styles.searchInput}
            placeholder={k.searchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label={k.searchAria}
          />
          {searchQuery && (
            <button
              type="button"
              className={styles.clearSearchBtn}
              onClick={() => setSearchQuery('')}
              aria-label={k.clearSearch}
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* 4. Category Filter Pills */}
      <div className={styles.categoryPills}>
        <div className={styles.categoryPillsScroll}>
          {(['all', 'regulation', 'tariff', 'fine_policy', 'ev_charging'] as KnowledgeCategory[]).map(
            (cat) => {
              const count = getCategoryCount(cat);
              const isActive = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  type="button"
                  className={`${styles.catPill} ${isActive ? styles.catPillActive : ''}`}
                  onClick={() => setSelectedCategory(cat)}
                >
                  <span>{categoryLabels[cat]}</span>
                  <span className={`${styles.catPillCount} num`}>{count}</span>
                </button>
              );
            },
          )}
        </div>
      </div>

      {/* 5. Documents List */}
      <div className={styles.docsList}>
        {filteredDocuments.length > 0 ? (
          filteredDocuments.map((doc, idx) => {
            const docId = doc.id || `doc_${idx}`;
            const isExpanded = expandedDocId === docId;
            const isCopied = copiedId === docId || copiedId === doc.title;

            return (
              <article key={docId} className={styles.docCard}>
                <header className={styles.docCardHeader}>
                  <div className={styles.docHeaderTop}>
                    <span className={`${styles.docBadge} ${styles[`badge_${doc.category}`] || ''}`}>
                      {categoryLabels[doc.category] || doc.category}
                    </span>
                    {doc.parking_lot_id ? (
                      <span className={styles.lotScopeBadge}>{doc.parking_lot_id}</span>
                    ) : (
                      <span className={styles.systemScopeBadge}>{k.systemWide}</span>
                    )}
                  </div>
                  <h5 className={styles.docTitle}>{doc.title}</h5>
                </header>

                <div className={styles.docSourceRow}>
                  <BookOpen size={12} className={styles.docSourceIcon} />
                  <span className={styles.docSourceText}>{doc.source}</span>
                </div>

                <div className={`${styles.docContent} ${!isExpanded ? styles.docContentClamped : ''}`}>
                  <p>
                    {doc.content ||
                      t.studio.knowledgeDocMeta(
                        doc.chunk_count ?? 0,
                        doc.latest_version_no ?? 0,
                        doc.latest_status ?? '',
                        doc.published_version_no ?? 0,
                      )}
                  </p>
                </div>

                <footer className={styles.docCardFooter}>
                  <button
                    type="button"
                    className={styles.expandTextBtn}
                    onClick={() => setExpandedDocId(isExpanded ? null : docId)}
                  >
                    {isExpanded ? k.collapse : k.expand}
                  </button>

                  <div className={styles.docCardActions}>
                    <button
                      type="button"
                      className={styles.docActionBtn}
                      onClick={() => handleCopyCitation(doc)}
                      title={k.copyCitation}
                      aria-label={k.copyCitation}
                    >
                      {isCopied ? <Check size={12} className={styles.successColor} /> : <Copy size={12} />}
                      <span>{isCopied ? k.copied : k.cite}</span>
                    </button>

                    {onAskAboutDocument && (
                      <button
                        type="button"
                        className={`${styles.docActionBtn} ${styles.docActionAskBtn}`}
                        onClick={() => onAskAboutDocument(doc)}
                        title={k.askTitle}
                        aria-label={k.ask}
                      >
                        <MessageSquare size={12} />
                        <span>{k.ask}</span>
                      </button>
                    )}
                  </div>
                </footer>
              </article>
            );
          })
        ) : (
          <div className={styles.emptyKnowledgeState}>
            <Filter size={24} className={styles.emptyIcon} />
            <p className={styles.emptyText}>{k.noMatch}</p>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('all');
              }}
            >
              {k.clearFilters}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default KnowledgeExplorer;
