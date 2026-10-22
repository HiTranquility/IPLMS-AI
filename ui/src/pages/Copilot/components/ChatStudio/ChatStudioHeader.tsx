import { Cpu, Download, PanelLeft, PanelRight, Plus } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './ChatStudio.module.css';

export interface ChatStudioHeaderProps {
  model: string;
  isStreaming: boolean;
  sidebarOpen: boolean;
  inspectorOpen: boolean;
  onToggleSidebar: () => void;
  onToggleInspector: () => void;
  onExportMarkdown: () => void;
  onNewChat: () => void;
  hasMessages: boolean;
}

export function ChatStudioHeader({
  model,
  isStreaming,
  sidebarOpen,
  inspectorOpen,
  onToggleSidebar,
  onToggleInspector,
  onExportMarkdown,
  onNewChat,
  hasMessages,
}: ChatStudioHeaderProps) {
  const { t } = useI18n();

  return (
    <header className={styles.studioHeader}>
      <div className={styles.studioTitleGroup}>
        <button
          type="button"
          className={styles.headerToggleBtn}
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Đóng thanh bên' : 'Mở thanh bên'}
          title={sidebarOpen ? 'Đóng thanh bên' : 'Mở thanh bên'}
        >
          <PanelLeft size={16} />
        </button>

        <div className={styles.modelBadge}>
          <span className={isStreaming ? styles.statusDotStreaming : styles.statusDot} />
          <Cpu size={14} />
          <span>{model}</span>
        </div>
      </div>

      <div className={styles.headerActions}>
        {hasMessages && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onExportMarkdown}
            aria-label="Xuất Markdown"
            title="Tải toàn bộ hội thoại dưới dạng Markdown"
          >
            <Download size={14} />
            <span>Xuất .md</span>
          </Button>
        )}

        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={onNewChat}
          disabled={isStreaming}
          aria-label={t.copilot.newChat}
        >
          <Plus size={14} />
          <span>{t.copilot.newChat}</span>
        </Button>

        <button
          type="button"
          className={`${styles.headerToggleBtn} ${inspectorOpen ? styles.headerToggleBtnActive : ''}`}
          onClick={onToggleInspector}
          aria-label={inspectorOpen ? 'Đóng ngăn kéo kiểm định' : 'Mở ngăn kéo kiểm định'}
          title={inspectorOpen ? 'Đóng ngăn kéo kiểm định' : 'Mở ngăn kéo kiểm định'}
        >
          <PanelRight size={16} />
        </button>
      </div>
    </header>
  );
}
