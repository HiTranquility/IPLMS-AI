import { useState } from 'react';
import { Bot, Check, Copy, ExternalLink, FlaskConical, RotateCcw, ThumbsDown, ThumbsUp, User } from 'lucide-react';
import { FormattedAnswer } from '@/components/common/Ui/data-display/FormattedAnswer';
import { useReviewTurn } from '@/hooks/mutations/useCopilotMutations';
import { usePromoteTurnToEval } from '@/hooks/mutations/useToolMutations';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtInt, fmtMs } from '@/utils/format';
import type { ChatMessage, RagSource } from './types';
import styles from './ChatStudio.module.css';

export interface ChatMessageBubbleProps {
  message: ChatMessage;
  onSelectCitation?: (citation: RagSource) => void;
  onFeedback?: (messageId: string, feedback: 1 | -1) => void;
  onRegenerate?: (messageId: string) => void;
}

export function ChatMessageBubble({
  message,
  onSelectCitation,
  onFeedback,
  onRegenerate,
}: ChatMessageBubbleProps) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const [showRejectNote, setShowRejectNote] = useState(false);
  const [rejectNote, setRejectNote] = useState('');
  const [showPromoteBox, setShowPromoteBox] = useState(false);
  const [promoteQuery, setPromoteQuery] = useState(message.userQuery || message.content || '');
  const [promoteBehavior, setPromoteBehavior] = useState<'ANSWER' | 'REFUSE'>('ANSWER');
  const [promoteCategory, setPromoteCategory] = useState<string>('regression');
  const [promoteNote, setPromoteNote] = useState('');

  const reviewMutation = useReviewTurn();
  const promoteEval = usePromoteTurnToEval();

  const isUser = message.role === 'user';
  const hasTurn = Boolean(message.turnId);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleQuickReview = (verdict: 'CORRECT' | 'INCORRECT', noteText = '') => {
    if (!message.turnId) return;
    reviewMutation.mutate(
      { turnId: message.turnId, verdict, note: noteText },
      {
        onSuccess: () => {
          setShowRejectNote(false);
          setRejectNote('');
        },
      },
    );
  };

  const handleTogglePromote = () => {
    setPromoteQuery((message.userQuery || message.content || '').slice(0, 500));
    setShowPromoteBox((v) => !v);
    setShowRejectNote(false);
  };

  const handleConfirmPromote = () => {
    if (!message.turnId || !promoteQuery.trim()) return;
    promoteEval.mutate(
      {
        turnId: message.turnId,
        query: promoteQuery.trim().slice(0, 500),
        expected_behavior: promoteBehavior,
        category: promoteCategory,
        note: promoteNote.trim() || 'Promoted from Chat Studio',
      },
      {
        onSuccess: () => {
          setShowPromoteBox(false);
        },
      },
    );
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

        {/* Form xác nhận đưa vào Eval (S4 / SUGGESTION-005) */}
        {showPromoteBox && hasTurn && (
          <div className={styles.quickRejectBox} role="region" aria-label={t.copilot.promoteTitle}>
            <div className={styles.quickTagLabel} style={{ fontWeight: 600, color: "var(--color-primary)" }}>
              {t.copilot.promoteTitle}
            </div>

            <div>
              <span className={styles.quickTagLabel}>{t.copilot.promoteQuery}</span>
              <input
                type="text"
                className={styles.quickRejectInput}
                style={{ width: "100%", marginTop: "2px" }}
                aria-label={t.copilot.promoteQuery}
                value={promoteQuery}
                onChange={(e) => setPromoteQuery(e.target.value)}
                placeholder={t.copilot.promoteQuery}
                maxLength={500}
              />
            </div>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <div style={{ flex: "1", minWidth: "120px" }}>
                <span className={styles.quickTagLabel}>{t.copilot.promoteExpected}</span>
                <select
                  className={styles.quickRejectInput}
                  style={{ width: "100%", marginTop: "2px" }}
                  aria-label={t.copilot.promoteExpected}
                  value={promoteBehavior}
                  onChange={(e) => setPromoteBehavior(e.target.value as "ANSWER" | "REFUSE")}
                >
                  <option value="ANSWER">{t.copilot.promoteAnswer}</option>
                  <option value="REFUSE">{t.copilot.promoteRefuse}</option>
                </select>
              </div>

              <div style={{ flex: "1", minWidth: "150px" }}>
                <span className={styles.quickTagLabel}>{t.copilot.promoteCategory}</span>
                <select
                  className={styles.quickRejectInput}
                  style={{ width: "100%", marginTop: "2px" }}
                  aria-label={t.copilot.promoteCategory}
                  value={promoteCategory}
                  onChange={(e) => setPromoteCategory(e.target.value)}
                >
                  <option value="regression">{t.copilot.promoteCatRegression}</option>
                  <option value="edge_case">{t.copilot.promoteCatEdgeCase}</option>
                  <option value="factual_grounding">{t.copilot.promoteCatGrounding}</option>
                  <option value="safety">{t.copilot.promoteCatSafety}</option>
                </select>
              </div>
            </div>

            <div>
              <span className={styles.quickTagLabel}>{t.copilot.promoteNote}</span>
              <input
                type="text"
                className={styles.quickRejectInput}
                style={{ width: "100%", marginTop: "2px" }}
                placeholder={t.copilot.promoteNotePlaceholder}
                aria-label={t.copilot.promoteNote}
                value={promoteNote}
                onChange={(e) => setPromoteNote(e.target.value)}
                maxLength={255}
              />
            </div>

            <div className={styles.quickRejectActions} style={{ justifyContent: "flex-end", marginTop: "4px" }}>
              <button
                type="button"
                className={styles.quickRejectCancelBtn}
                style={{ padding: "3px 8px", fontSize: "var(--text-xs)" }}
                onClick={() => setShowPromoteBox(false)}
              >
                {t.copilot.cancel}
              </button>
              <button
                type="button"
                className={styles.quickRejectSubmitBtn}
                disabled={!promoteQuery.trim() || promoteEval.isPending}
                onClick={handleConfirmPromote}
              >
                {promoteEval.isPending ? "..." : t.copilot.promoteConfirm}
              </button>
            </div>
          </div>
        )}

        {/* Form nhập lý do nhanh khi người dùng từ chối câu trả lời trong Chat Studio */}
        {showRejectNote && hasTurn && (
          <div className={styles.quickRejectBox}>
            <div className={styles.quickTagsList}>
              <span className={styles.quickTagLabel}>{t.copilot.quickTagHint}</span>
              <button
                type="button"
                className={styles.quickReasonTag}
                onClick={() => setRejectNote(t.copilot.tagFee)}
              >
                {t.copilot.tagFee}
              </button>
              <button
                type="button"
                className={styles.quickReasonTag}
                onClick={() => setRejectNote(t.copilot.tagSource)}
              >
                {t.copilot.tagSource}
              </button>
              <button
                type="button"
                className={styles.quickReasonTag}
                onClick={() => setRejectNote(t.copilot.tagHallucination)}
              >
                {t.copilot.tagHallucination}
              </button>
              <button
                type="button"
                className={styles.quickReasonTag}
                onClick={() => setRejectNote(t.copilot.tagScope)}
              >
                {t.copilot.tagScope}
              </button>
            </div>
            <div className={styles.quickRejectActions}>
              <input
                type="text"
                className={styles.quickRejectInput}
                placeholder={t.copilot.noteRequired}
                value={rejectNote}
                onChange={(e) => setRejectNote(e.target.value)}
              />
              <button
                type="button"
                className={styles.quickRejectSubmitBtn}
                disabled={rejectNote.trim().length < 3 || reviewMutation.isPending}
                onClick={() => handleQuickReview('INCORRECT', rejectNote.trim())}
              >
                {t.copilot.save}
              </button>
              <button
                type="button"
                className={styles.quickRejectCancelBtn}
                aria-label={t.copilot.cancel}
                onClick={() => setShowRejectNote(false)}
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Thanh thông tin & hành động dưới câu trả lời của Bot */}
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
              {/* Nút Thử lại / Tạo lại câu trả lời */}
              {onRegenerate && !message.isStreaming && (
                <button
                  type="button"
                  className={styles.iconBtn}
                  onClick={() => onRegenerate(message.id)}
                  aria-label={t.copilot.regenerate}
                  title={t.copilot.regenerate}
                >
                  <RotateCcw size={14} />
                </button>
              )}

              {/* Nút Đưa vào Eval trực tiếp từ bubble */}
              {hasTurn && !message.isStreaming && (
                <button
                  type="button"
                  className={`${styles.iconBtn} ${promoteEval.isSuccess ? styles.btnSuccess : ''} ${showPromoteBox ? styles.feedbackActiveUp : ''}`}
                  onClick={handleTogglePromote}
                  disabled={promoteEval.isPending || promoteEval.isSuccess}
                  aria-label={promoteEval.isSuccess ? t.copilot.quickPromoteDone : t.copilot.quickPromoteEval}
                  title={promoteEval.isSuccess ? t.copilot.quickPromoteDone : t.copilot.quickPromoteEval}
                >
                  <FlaskConical size={14} />
                </button>
              )}

              {/* Nút Sao chép */}
              <button
                type="button"
                className={styles.iconBtn}
                onClick={handleCopy}
                aria-label={copied ? t.copilot.copied : t.copilot.copyAnswer}
                title={copied ? t.copilot.copied : t.copilot.copyAnswer}
              >
                {copied ? <Check size={14} className={styles.checkIcon} /> : <Copy size={14} />}
              </button>

              {/* Nút Phản hồi & Đánh giá nhanh */}
              {hasTurn && !message.isStreaming ? (
                <>
                  <button
                    type="button"
                    className={`${styles.iconBtn} ${reviewMutation.isSuccess && !showRejectNote ? styles.feedbackActiveUp : ''}`}
                    onClick={() => handleQuickReview('CORRECT')}
                    disabled={reviewMutation.isPending}
                    aria-label={t.copilot.quickReviewCorrect}
                    title={t.copilot.quickReviewCorrect}
                  >
                    <ThumbsUp size={14} />
                  </button>

                  <button
                    type="button"
                    className={`${styles.iconBtn} ${showRejectNote ? styles.feedbackActiveDown : ''}`}
                    onClick={() => setShowRejectNote((v) => !v)}
                    disabled={reviewMutation.isPending}
                    aria-label={t.copilot.quickReviewIncorrect}
                    title={t.copilot.quickReviewIncorrect}
                  >
                    <ThumbsDown size={14} />
                  </button>
                </>
              ) : (
                <>
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
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
