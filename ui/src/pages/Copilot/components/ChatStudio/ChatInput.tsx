import { type FormEvent, type KeyboardEvent, type RefObject, useEffect } from 'react';
import { MapPin, Send, Sparkles, Square } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import type { PromptPreset } from './types';
import styles from './ChatStudio.module.css';

export interface ChatInputProps {
  inputQuery: string;
  setInputQuery: (val: string) => void;
  onSubmit: (e?: FormEvent) => void;
  isStreaming: boolean;
  onStopStreaming: () => void;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  presets?: PromptPreset[];
  onSelectPreset?: (prompt: string) => void;
  parkingLotId?: string;
  onChangeParkingLotId?: (lotId: string) => void;
  lastUserQuery?: string;
}

export function ChatInput({
  inputQuery,
  setInputQuery,
  onSubmit,
  isStreaming,
  onStopStreaming,
  inputRef,
  presets = [],
  onSelectPreset,
  parkingLotId = '',
  onChangeParkingLotId,
  lastUserQuery = '',
}: ChatInputProps) {
  const { t } = useI18n();

  // Auto-resize chiều cao textarea theo nội dung gõ (từ 44px đến 160px)
  useEffect(() => {
    const el = inputRef.current;
    if (el) {
      el.style.height = 'auto';
      const newHeight = Math.min(Math.max(el.scrollHeight, 44), 160);
      el.style.height = `${newHeight}px`;
    }
  }, [inputQuery, inputRef]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Phím Mũi tên lên (ArrowUp) khi ô nhập rỗng: tải lại câu hỏi gần nhất của người dùng
    if (e.key === 'ArrowUp' && !inputQuery.trim() && lastUserQuery && !isStreaming) {
      e.preventDefault();
      setInputQuery(lastUserQuery);
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && inputQuery.trim()) {
        onSubmit(e);
      }
    }
  };

  return (
    <footer className={styles.inputArea}>
      {/* Thanh ngữ cảnh bãi xe & gợi ý câu hỏi nhanh (Quick Prompts Bar) */}
      <div className={styles.inputTopBar}>
        {onChangeParkingLotId && (
          <div className={styles.lotContextPill} title={t.copilot.lotContext}>
            <MapPin size={13} className={styles.lotIcon} />
            <select
              className={styles.lotSelect}
              value={parkingLotId}
              onChange={(e) => onChangeParkingLotId(e.target.value)}
              aria-label={t.copilot.lotContext}
            >
              <option value="">{t.copilot.allLots}</option>
              <option value="lot_vincom_center">{t.copilot.lotVincomDongKhoi}</option>
              <option value="lot_central_01">{t.copilot.lotCentral}</option>
              <option value="lot_west_gate">{t.copilot.lotWestGate}</option>
            </select>
          </div>
        )}

        {presets.length > 0 && onSelectPreset && (
          <div className={styles.quickPromptScroll} role="region" aria-label={t.copilot.quickPrompts}>
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={styles.quickPromptChip}
                onClick={() => onSelectPreset(preset.query)}
                title={preset.query}
              >
                <Sparkles size={11} className={styles.chipSparkle} />
                <span>{preset.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>

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
              <kbd className={styles.kbd}>Shift+Enter</kbd> {t.copilot.newLine}
            </span>
            {lastUserQuery && (
              <>
                <span>·</span>
                <span>
                  <kbd className={styles.kbd}>↑</kbd> {t.copilot.lastPrompt}
                </span>
              </>
            )}
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
