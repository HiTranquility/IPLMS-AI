import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/common/Ui/button/Button';
import { useI18n } from '@/i18n/I18nProvider';
import type { PromptPreset } from './types';
import styles from './ChatStudio.module.css';

export interface ChatSidebarProps {
  isOpen: boolean;
  presets: PromptPreset[];
  onSelectPreset: (prompt: string) => void;
  onNewChat: () => void;
  onClearChat: () => void;
  hasMessages: boolean;
  isStreaming: boolean;
}

export function ChatSidebar({
  isOpen,
  presets,
  onSelectPreset,
  onNewChat,
  onClearChat,
  hasMessages,
  isStreaming,
}: ChatSidebarProps) {
  const { t } = useI18n();

  return (
    <aside className={`${styles.sidebar} ${!isOpen ? styles.sidebarClosed : ''}`} aria-hidden={!isOpen}>
      <div className={styles.sidebarTop}>
        <Button
          type="button"
          variant="primary"
          onClick={onNewChat}
          disabled={isStreaming}
          className={styles.newChatFullBtn}
        >
          <Plus size={16} />
          <span>{t.copilot.newChat}</span>
        </Button>
      </div>

      <div className={styles.presetSection}>
        <div className={styles.sectionHeading}>{t.copilot.presetsTitle}</div>
        <div className={styles.presetList}>
          {presets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={styles.presetCard}
              onClick={() => onSelectPreset(preset.query)}
              disabled={isStreaming}
            >
              <span className={styles.presetCategory}>{preset.category}</span>
              <span className={styles.presetTitle}>{preset.title}</span>
            </button>
          ))}
        </div>
      </div>

      {hasMessages && (
        <div className={styles.sidebarFooter}>
          <button
            type="button"
            className={styles.clearChatBtn}
            onClick={onClearChat}
            disabled={isStreaming}
          >
            <Trash2 size={14} />
            <span>{t.copilot.clearChat}</span>
          </button>
        </div>
      )}
    </aside>
  );
}
