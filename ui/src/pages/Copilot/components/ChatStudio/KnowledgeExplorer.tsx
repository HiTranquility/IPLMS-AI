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
import { DEFAULT_SEED_DOCUMENTS } from './defaultSeeds';
import type { KnowledgeCategory, SeedDocument } from './types';
import styles from './ChatStudio.module.css';

export interface KnowledgeExplorerProps {
  onAskAboutDocument?: (doc: SeedDocument) => void;
  onInsertCitation?: (citationText: string) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  all: 'Tất cả',
  regulation: 'Quy định',
  tariff: 'Biểu phí',
  fine_policy: 'Xử phạt',
  ev_charging: 'Trạm sạc EV',
};

export function KnowledgeExplorer({ onAskAboutDocument, onInsertCitation }: KnowledgeExplorerProps) {
  const [documents, setDocuments] = useState<SeedDocument[]>(DEFAULT_SEED_DOCUMENTS);
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

  // Thử tải từ API backend nếu có
  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const apiBase = window.location.pathname.startsWith('/console') ? '/console/api' : '/api';
      const res = await fetch(`${apiBase}/knowledge/seeds`);
      if (res.ok) {
        const data = await res.json();
        const items = data.items || (Array.isArray(data) ? data : null);
        if (items && items.length > 0) {
          setDocuments(items);
        }
      }
    } catch {
      // Nếu API offline thì dùng data mặc định từ seed json
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
      doc.content.toLowerCase().includes(query) ||
      doc.source.toLowerCase().includes(query);
    return matchesCategory && matchesQuery;
  });

  const getCategoryCount = (cat: KnowledgeCategory) => {
    if (cat === 'all') return documents.length;
    return documents.filter((d) => d.category.toLowerCase() === cat.toLowerCase()).length;
  };

  const handleCopyCitation = (doc: SeedDocument) => {
    const text = `[Trích dẫn: ${doc.title} - Nguồn: ${doc.source}]\n${doc.content}`;
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
      setIngestStatus({ ok: false, msg: 'Vui lòng chọn tệp PDF, DOCX hoặc TXT!' });
      return;
    }

    setIsIngesting(true);
    setIngestStatus(null);

    try {
      const apiBase = window.location.pathname.startsWith('/console') ? '/console/api' : '/api';
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('document_id', `doc_${Date.now()}`);
      formData.append('category', ingestCategory);
      if (lotScope.trim()) {
        formData.append('parking_lot_id', lotScope.trim());
      }

      const res = await fetch(`${apiBase}/tools/knowledge`, {
        method: 'POST',
        headers: {
          'X-Console-Request': '1',
        },
        body: formData,
      });

      if (res.ok) {
        setIngestStatus({
          ok: true,
          msg: `Phân tích & vector hoá thành công: ${selectedFile.name}`,
        });
        setSelectedFile(null);
        loadDocuments();
      } else {
        const errorData = await res.json().catch(() => ({}));
        setIngestStatus({
          ok: false,
          msg: errorData.message || `Lỗi tải lên (${res.status})`,
        });
      }
    } catch (err: any) {
      setIngestStatus({
        ok: false,
        msg: `Không thể kết nối máy chủ nạp tri thức: ${err.message || 'Lỗi mạng'}`,
      });
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
            <h4 className={styles.keTitle}>Kho Tri Thức Quy Chế</h4>
            <span className={styles.keSub}>
              {documents.length} văn bản lưu trữ • <code>pgvector: Sẵn sàng</code>
            </span>
          </div>
        </div>

        <div className={styles.keActions}>
          <button
            type="button"
            className={`${styles.keActionBtn} ${ingestOpen ? styles.keActionBtnActive : ''}`}
            onClick={() => setIngestOpen((v) => !v)}
            title="Nạp tài liệu mới vào cơ sở tri thức"
            aria-label="Nạp tài liệu"
          >
            <FileUp size={14} />
            <span>Nạp văn bản</span>
          </button>

          <button
            type="button"
            className={styles.keActionBtn}
            onClick={loadDocuments}
            disabled={isLoading}
            title="Làm mới danh sách"
            aria-label="Làm mới"
          >
            <RefreshCw size={13} className={isLoading ? styles.spin : ''} />
          </button>
        </div>
      </div>

      {/* 2. Ingestion Card (Collapsible) */}
      {ingestOpen && (
        <form onSubmit={handleSubmitIngestion} className={styles.ingestCard}>
          <div className={styles.ingestHeader}>
            <span className={styles.ingestTitle}>
              <Layers size={14} /> Nạp & Vector Hóa Văn Bản Quy Chế
            </span>
            <button
              type="button"
              className={styles.keCloseBtn}
              onClick={() => setIngestOpen(false)}
              aria-label="Đóng biểu mẫu nạp"
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
              {selectedFile ? selectedFile.name : 'Chọn tệp PDF, DOCX hoặc TXT để nạp'}
            </span>
            <span className={styles.dropzoneHint}>Dung lượng tối đa 8MB • pgvector HNSW indexing</span>
          </label>

          <div className={styles.ingestInputsGrid}>
            <div className={styles.ingestField}>
              <label htmlFor="ingest-category" className={styles.ingestLabel}>
                Phân loại
              </label>
              <select
                id="ingest-category"
                className={styles.selectInput}
                value={ingestCategory}
                onChange={(e) => setIngestCategory(e.target.value)}
              >
                <option value="regulation">Quy định / Quy chế</option>
                <option value="tariff">Biểu phí gửi xe</option>
                <option value="fine_policy">Chính sách xử phạt</option>
                <option value="ev_charging">Trạm sạc xe điện EV</option>
              </select>
            </div>

            <div className={styles.ingestField}>
              <label htmlFor="ingest-scope" className={styles.ingestLabel}>
                Phạm vi áp dụng
              </label>
              <input
                id="ingest-scope"
                type="text"
                placeholder="Trống = Toàn hệ thống"
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
            <span>{isIngesting ? 'Đang trích xuất & vector hóa...' : 'Phân tích & Nạp vào pgvector'}</span>
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
            placeholder="Tìm kiếm quy chế, mức phí, điều khoản..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Tìm kiếm quy chế"
          />
          {searchQuery && (
            <button
              type="button"
              className={styles.clearSearchBtn}
              onClick={() => setSearchQuery('')}
              aria-label="Xóa từ khóa tìm kiếm"
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
                  <span>{CATEGORY_LABELS[cat]}</span>
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
                      {CATEGORY_LABELS[doc.category] || doc.category}
                    </span>
                    {doc.parking_lot_id ? (
                      <span className={styles.lotScopeBadge}>{doc.parking_lot_id}</span>
                    ) : (
                      <span className={styles.systemScopeBadge}>Toàn hệ thống</span>
                    )}
                  </div>
                  <h5 className={styles.docTitle}>{doc.title}</h5>
                </header>

                <div className={styles.docSourceRow}>
                  <BookOpen size={12} className={styles.docSourceIcon} />
                  <span className={styles.docSourceText}>{doc.source}</span>
                </div>

                <div className={`${styles.docContent} ${!isExpanded ? styles.docContentClamped : ''}`}>
                  <p>{doc.content}</p>
                </div>

                <footer className={styles.docCardFooter}>
                  <button
                    type="button"
                    className={styles.expandTextBtn}
                    onClick={() => setExpandedDocId(isExpanded ? null : docId)}
                  >
                    {isExpanded ? 'Thu gọn' : 'Xem toàn văn'}
                  </button>

                  <div className={styles.docCardActions}>
                    <button
                      type="button"
                      className={styles.docActionBtn}
                      onClick={() => handleCopyCitation(doc)}
                      title="Sao chép trích dẫn"
                      aria-label="Sao chép trích dẫn"
                    >
                      {isCopied ? <Check size={12} className={styles.successColor} /> : <Copy size={12} />}
                      <span>{isCopied ? 'Đã chép' : 'Trích dẫn'}</span>
                    </button>

                    {onAskAboutDocument && (
                      <button
                        type="button"
                        className={`${styles.docActionBtn} ${styles.docActionAskBtn}`}
                        onClick={() => onAskAboutDocument(doc)}
                        title="Hỏi Copilot về điều khoản này"
                        aria-label="Hỏi Copilot"
                      >
                        <MessageSquare size={12} />
                        <span>Hỏi Copilot</span>
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
            <p className={styles.emptyText}>Không tìm thấy tài liệu quy chế phù hợp từ khóa.</p>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('all');
              }}
            >
              Xóa bộ lọc
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default KnowledgeExplorer;
