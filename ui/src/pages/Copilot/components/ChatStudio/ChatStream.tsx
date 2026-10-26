import { type RefObject } from 'react';
import { Bot, Sparkles } from 'lucide-react';
import { useI18n } from '@/i18n/I18nProvider';
import { ChatMessageBubble } from './ChatMessageBubble';
import type { ChatMessage, PromptPreset, RagSource } from './types';
import styles from './ChatStudio.module.css';

export interface ChatStreamProps {
  messages: ChatMessage[];
  presets: PromptPreset[];
  onSelectPreset: (prompt: string) => void;
  onSelectCitation?: (citation: RagSource) => void;
  onFeedback?: (messageId: string, feedback: 1 | -1) => void;
  onRegenerate?: (messageId: string) => void;
  messagesEndRef: RefObject<HTMLDivElement | null>;
}

export function ChatStream({
  messages,
  presets,
  onSelectPreset,
  onSelectCitation,
  onFeedback,
  onRegenerate,
  messagesEndRef,
}: ChatStreamProps) {
  const { t } = useI18n();

  return (
    <div className={styles.messagesContainer} role="log" aria-live="polite">
      {messages.length === 0 ? (
        <div className={styles.heroWelcome}>
          <div className={styles.heroIcon}>
            <Bot size={28} />
          </div>
          <h2 className={styles.heroTitle}>{t.copilot.welcomeTitle}</h2>
          <p className={styles.heroDesc}>{t.copilot.welcomeDesc}</p>

          <div className={styles.heroPresets}>
            {presets.slice(0, 3).map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={styles.heroPresetBtn}
                onClick={() => onSelectPreset(preset.query)}
              >
                <Sparkles size={12} className={styles.sparkleIcon} />
                <span>{preset.title}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <>
          {messages.map((msg) => (
            <ChatMessageBubble
              key={msg.id}
              message={msg}
              onSelectCitation={onSelectCitation}
              onFeedback={onFeedback}
              onRegenerate={onRegenerate}
            />
          ))}
          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
}
