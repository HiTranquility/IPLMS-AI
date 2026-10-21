import { Send } from 'lucide-react';
import { useState, useRef, type FormEvent } from 'react';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { TextArea, TextField } from '@/components/common/Ui/form/Field';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtPercent } from '@/utils/format';
import styles from '../ToolsPage.module.css';

interface StreamState {
  answer: string;
  isStreaming: boolean;
  confidence?: number;
  sources: string[];
  promptVersion?: string;
  turnId?: string;
  latencyMs?: number;
  guardrailTriggered?: string;
  error?: string;
}

export function CopilotSection() {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [lot, setLot] = useState('');
  const [streamData, setStreamData] = useState<StreamState | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setStreamData({
      answer: '',
      isStreaming: true,
      sources: [],
    });

    try {
      const response = await fetch('/console/api/tools/copilot/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Console-Request': '1',
        },
        credentials: 'include',
        body: JSON.stringify({
          query: query.trim(),
          parking_lot_id: lot.trim() || undefined,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Lỗi máy chủ (${response.status})`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Không đọc được stream từ máy chủ.');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const chunk = JSON.parse(trimmed.slice(6));
              setStreamData((prev) => {
                if (!prev) return null;
                const newAnswer = prev.answer + (chunk.token || '');
                return {
                  ...prev,
                  answer: newAnswer,
                  isStreaming: !chunk.is_finished,
                  confidence: chunk.confidence ?? prev.confidence,
                  sources: chunk.sources?.length ? chunk.sources : prev.sources,
                  promptVersion: chunk.prompt_version ?? prev.promptVersion,
                  turnId: chunk.turn_id ?? prev.turnId,
                  latencyMs: chunk.latency_ms ?? prev.latencyMs,
                  guardrailTriggered: chunk.guardrail_triggered ?? prev.guardrailTriggered,
                };
              });
            } catch {
              // Ignore malformed chunk
            }
          }
        }
      }

      setStreamData((prev) => prev ? { ...prev, isStreaming: false } : null);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      setStreamData((prev) => ({
        answer: prev?.answer || '',
        isStreaming: false,
        sources: prev?.sources || [],
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  };

  return (
    <section className={styles.panel} aria-labelledby="copilot-title">
      <h2 id="copilot-title" className={styles.title}>{t.tools.copilotTitle}</h2>
      <p className={styles.note}>{t.tools.copilotNote.before}<span className={styles.mono}>console_try</span>{t.tools.copilotNote.after}</p>
      <form className={styles.form} onSubmit={submit}>
        <TextArea label={t.tools.question} required maxLength={2000} rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
        <TextField label={t.tools.lot} hint={t.tools.lotHint} maxLength={128} value={lot} onChange={(e) => setLot(e.target.value)} />
        <Button type="submit" loading={streamData?.isStreaming} disabled={!query.trim()}>
          <Send size={16} aria-hidden />
          {streamData?.isStreaming ? 'Đang stream...' : t.tools.send}
        </Button>
      </form>
      {streamData?.error && <ErrorBlock error={new Error(streamData.error)} />}
      {streamData && (
        <div className={styles.answer} role="status">
          <p className={styles.answerText}>
            {streamData.answer}
            {streamData.isStreaming && <span className="animate-pulse font-mono"> ▋</span>}
          </p>
          {!streamData.isStreaming && (
            <p className={styles.note}>
              {streamData.confidence !== undefined && (
                <>
                  {t.tools.confidence(fmtPercent(streamData.confidence))} ·{' '}
                </>
              )}
              {streamData.promptVersion && (
                <>
                  {t.tools.prompt} <span className={styles.mono}>{streamData.promptVersion}</span> ·{' '}
                </>
              )}
              {streamData.turnId && (
                <>
                  {t.tools.turn} <span className={styles.mono}>{streamData.turnId}</span> ·{' '}
                </>
              )}
              {streamData.latencyMs !== undefined && (
                <span>{Math.round(streamData.latencyMs)}ms</span>
              )}
              {streamData.guardrailTriggered && (
                <Badge tone="danger">Guard: {streamData.guardrailTriggered}</Badge>
              )}
            </p>
          )}
          {streamData.sources.length > 0 && (
            <div className={styles.sources}>
              {streamData.sources.map((s) => <Badge key={s}>{s}</Badge>)}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default CopilotSection;
