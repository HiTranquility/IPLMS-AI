import { type FormEvent, type KeyboardEvent, type RefObject } from 'react';
import { Send, Square } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import styles from './ChatStudio.module.css';

export interface ChatInputProps {
  inputQuery: string;
  setInputQuery: (val: string) => void;
  onSubmit: (e: FormEvent) => void;
  isStreaming: boolean;
  onStopStreaming: () => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
}

export function ChatInput({
  inputQuery,
  setInputQuery,
  onSubmit,
  isStreaming,
  onStopStreaming,
  inputRef,
}: ChatInputProps) {
  const { t } = useI18n();

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && inputQuery.trim()) {
        onSubmit(e);
      }
    }
  };

  return (
    <footer className={styles.inputArea}>
      <form onSubmit={onSubmit} className={styles.inputForm}>
        <textarea
          ref={inputRef}
          className={styles.chatTextarea}
          placeholder={t.copilot.inputPlaceholder}
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={isStreaming}
          aria-label={t.copilot.inputPlaceholder}
        />

        <div className={styles.inputControls}>
          <div className={styles.inputHints}>
            <span>
              <kbd className={styles.kbd}>Enter</kbd> {t.copilot.send}
            </span>
            <span>·</span>
            <span>
              <kbd className={styles.kbd}>Shift+Enter</kbd> Xuống dòng
            </span>
          </div>

          <div className={styles.inputButtons}>
            {isStreaming ? (
              <button
                type="button"
                className={styles.stopBtn}
                onClick={onStopStreaming}
                aria-label={t.copilot.stop}
              >
                <Square size={14} fill="currentColor" />
                <span>{t.copilot.stop}</span>
              </button>
            ) : (
              <button
                type="submit"
                className={styles.sendBtn}
                disabled={!inputQuery.trim()}
                aria-label={t.copilot.send}
              >
                <Send size={14} />
                <span>{t.copilot.send}</span>
              </button>
            )}
          </div>
        </div>
      </form>
    </footer>
  );
}
