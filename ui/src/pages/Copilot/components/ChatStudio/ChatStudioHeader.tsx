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
          aria-label={sidebarOpen ? t.copilot.sidebarClose : t.copilot.sidebarOpen}
          title={sidebarOpen ? t.copilot.sidebarClose : t.copilot.sidebarOpen}
        >
          <PanelLeft size={16} />
        </button>

        <div className={styles.modelBadge} title={t.copilot.configuredModel(model)}>
          <span className={isStreaming ? styles.statusDotStreaming : styles.statusDot} />
          <Cpu size={14} aria-hidden />
          <span aria-hidden>{model}</span>
          <span className="visually-hidden">{t.copilot.configuredModel(model)}</span>
        </div>
      </div>

      <div className={styles.headerActions}>
        {hasMessages && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onExportMarkdown}
            aria-label={t.copilot.exportMd}
            title={t.copilot.exportMdTitle}
          >
            <Download size={14} />
            <span>{t.copilot.exportMdShort}</span>
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
          aria-label={inspectorOpen ? t.copilot.inspectorClose : t.copilot.inspectorOpen}
          title={inspectorOpen ? t.copilot.inspectorClose : t.copilot.inspectorOpen}
        >
          <PanelRight size={16} />
        </button>
      </div>
    </header>
  );
}
