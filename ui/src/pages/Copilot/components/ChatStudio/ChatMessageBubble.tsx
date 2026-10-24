import { useState } from 'react';
import { Bot, Check, Copy, ExternalLink, ThumbsDown, ThumbsUp, User } from 'lucide-react';
import { FormattedAnswer } from '@/components/common/Ui/data-display/FormattedAnswer';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt, fmtMs } from '@/utils/format';
import type { ChatMessage, RagSource } from './types';
import styles from './ChatStudio.module.css';

export interface ChatMessageBubbleProps {
  message: ChatMessage;
  onSelectCitation?: (citation: RagSource) => void;
  onFeedback?: (messageId: string, feedback: 1 | -1) => void;
}

export function ChatMessageBubble({
  message,
  onSelectCitation,
  onFeedback,
}: ChatMessageBubbleProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className={`${styles.messageRow} ${isUser ? styles.messageRowUser : styles.messageRowBot}`}>
      <div className={`${styles.avatar} ${isUser ? styles.avatarUser : styles.avatarBot}`} aria-hidden="true">
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className={styles.messageContentBox}>
        <div className={styles.messageBubble}>
          {isUser ? (
            <p className={styles.userText}>{message.content}</p>
          ) : (
            <>
              {message.content ? (
                <FormattedAnswer content={message.content} isStreaming={message.isStreaming} />
              ) : (
                <p className={styles.thinkingHint}>{t.copilot.thinking}</p>
              )}

              {/* Trích dẫn RAG */}
              {message.ragSources && message.ragSources.length > 0 && (
                <div className={styles.citationsBlock}>
                  {message.ragSources.map((source, idx) => (
                    <button
                      key={source.chunkId || idx}
                      type="button"
                      className={styles.citationTag}
                      onClick={() => onSelectCitation?.(source)}
                      title={t.copilot.citationView(source.title)}
                    >
                      <ExternalLink size={12} />
                      <span className={styles.citationTitle}>{source.title}</span>
                      {source.score != null && (
                        <span className={`${styles.citationScore} num`}>
                          {(source.score * 100).toFixed(0)}%
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Thanh thông tin dưới câu trả lời của Bot */}
        {!isUser && message.content && (
          <div className={styles.messageMeta}>
            <div className={styles.metaStats}>
              {message.latencyMs != null && (
                <span className="num" title={t.copilot.latency}>
                  {fmtMs(message.latencyMs)}
                </span>
              )}
              {message.speedTokPerSec != null && (
                <span className="num" title={t.copilot.speedTitle}>
                  {message.speedTokPerSec} t/s
                </span>
              )}
              {message.outputTokens != null && (
                <span className="num" title={t.copilot.outputTokensTitle}>
                  {fmtInt(message.outputTokens)} tok
                </span>
              )}
            </div>

            <div className={styles.metaActions}>
              <button
                type="button"
                className={styles.iconBtn}
                onClick={handleCopy}
                aria-label={copied ? t.copilot.copied : t.copilot.copyAnswer}
                title={copied ? t.copilot.copied : t.copilot.copyAnswer}
              >
                {copied ? <Check size={14} className={styles.checkIcon} /> : <Copy size={14} />}
              </button>

              <button
                type="button"
                className={`${styles.iconBtn} ${message.feedback === 1 ? styles.feedbackActiveUp : ''}`}
                onClick={() => onFeedback?.(message.id, 1)}
                aria-label={t.copilot.feedbackUp}
                title={t.copilot.feedbackUp}
              >
                <ThumbsUp size={14} />
              </button>

              <button
                type="button"
                className={`${styles.iconBtn} ${message.feedback === -1 ? styles.feedbackActiveDown : ''}`}
                onClick={() => onFeedback?.(message.id, -1)}
                aria-label={t.copilot.feedbackDown}
                title={t.copilot.feedbackDown}
              >
                <ThumbsDown size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
