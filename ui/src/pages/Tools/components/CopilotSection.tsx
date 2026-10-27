import { BarChart2, Clock, Layers, Send, Sparkles, Zap } from 'lucide-react';
import { useState, useRef, type FormEvent } from 'react';
import { PARKING_LOTS, resolveLotLabel } from '@/constants/parkingLots';
import { Button } from '@/components/common/Ui/button/Button';
import { Badge } from '@/components/common/Ui/data-display/Badge';
import { ErrorBlock } from '@/components/common/Ui/feedback/LoadState';
import { SelectField, TextArea, TextField } from '@/components/common/Ui/form/Field';
import { useI18n } from '@/i18n/I18nProvider';
import { fmtPercent } from '@/utils/format';
import { FormattedAnswer } from '@/components/common/Ui/data-display/FormattedAnswer';
import { API_BASE } from '@/services/apiClient';
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
  inputTokens?: number;
  outputTokens?: number;
  speedTokPerSec?: number;
  contextTokens?: number;
  contextLimit?: number;
  liveSpeed?: number;
  liveTokens?: number;
}

export function CopilotSection() {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const [lotMode, setLotMode] = useState('');
  const [customLot, setCustomLot] = useState('');
  const [lot, setLot] = useState('');
  const [streamData, setStreamData] = useState<StreamState | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleLotSelect = (val: string) => {
    setLotMode(val);
    if (val !== '__custom__') {
      setLot(val);
    } else {
      setLot(customLot);
    }
  };

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
      liveSpeed: 0,
      liveTokens: 0,
    });

    const streamStart = performance.now();
    let tokenChunksReceived = 0;

    try {
      const response = await fetch(`${API_BASE}/tools/copilot/stream`, {
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
        throw new Error(t.tools.serverError(response.status));
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error(t.tools.noStream);

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
              if (chunk.token) {
                tokenChunksReceived += 1;
              }
              const elapsedSec = (performance.now() - streamStart) / 1000;
              const liveSpeed = elapsedSec > 0.05 ? Math.round((tokenChunksReceived / elapsedSec) * 10) / 10 : 0;

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
                  inputTokens: chunk.input_tokens ?? prev.inputTokens,
                  outputTokens: chunk.output_tokens ?? prev.outputTokens,
                  speedTokPerSec: chunk.speed_tok_s ?? prev.speedTokPerSec,
                  contextTokens: chunk.context_tokens ?? prev.contextTokens,
                  contextLimit: chunk.context_limit ?? prev.contextLimit,
                  liveSpeed,
                  liveTokens: tokenChunksReceived,
                };
              });
            } catch {
              // Ignore malformed chunk
            }
          }
        }
      }

      setStreamData((prev) => (prev ? { ...prev, isStreaming: false } : null));
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

      {/* Gợi ý câu hỏi thực tế 1-click */}
      <div className={styles.quickPromptsBar} role="region" aria-label={t.copilot.quickPrompts}>
        <button
          type="button"
          className={styles.quickPromptBtn}
          onClick={() => setQuery(t.tools.quickPreset1)}
        >
          <Sparkles size={12} className={styles.sparkleIcon} />
          <span>{t.tools.quickPreset1}</span>
        </button>
        <button
          type="button"
          className={styles.quickPromptBtn}
          onClick={() => setQuery(t.tools.quickPreset2)}
        >
          <Sparkles size={12} className={styles.sparkleIcon} />
          <span>{t.tools.quickPreset2}</span>
        </button>
        <button
          type="button"
          className={styles.quickPromptBtn}
          onClick={() => setQuery(t.tools.quickPreset3)}
        >
          <Sparkles size={12} className={styles.sparkleIcon} />
          <span>{t.tools.quickPreset3}</span>
        </button>
      </div>

      <form className={styles.form} onSubmit={submit}>
        <TextArea label={t.tools.question} required maxLength={2000} rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />

        {/* Dropdown chọn bãi xe chuẩn hóa thay vì gõ text thủ công */}
        <SelectField
          label={t.tools.lot}
          hint={t.tools.lotHint}
          value={lotMode}
          onChange={(e) => handleLotSelect(e.target.value)}
        >
          <option value="">{t.tools.lotAll}</option>
          {PARKING_LOTS.map((lot) => (
            <option key={lot.id} value={lot.id}>
              {resolveLotLabel(lot, t)}
            </option>
          ))}
          <option value="__custom__">{t.tools.lotCustom}</option>
        </SelectField>

        {lotMode === '__custom__' && (
          <TextField
            label={t.tools.lotCustom}
            placeholder={t.tools.customLotPlaceholder}
            maxLength={128}
            value={customLot}
            onChange={(e) => {
              setCustomLot(e.target.value);
              setLot(e.target.value);
            }}
          />
        )}

        <Button type="submit" loading={streamData?.isStreaming} disabled={!query.trim()}>
          <Send size={16} aria-hidden />
          {streamData?.isStreaming ? t.tools.streaming : t.tools.send}
        </Button>
      </form>
      {streamData?.error && <ErrorBlock error={new Error(streamData.error)} />}
      {streamData && (
        <div className={styles.answer} role="status">
          <FormattedAnswer
            content={streamData.answer}
            isStreaming={streamData.isStreaming}
          />

          {/* Live speed counter while streaming (LM Studio / llama.cpp style) */}
          {streamData.isStreaming && (
            <div className={styles.liveTicker} role="status" aria-live="polite">
              <span className="animate-spin text-[10px]">⚙</span>
              <span>⚡ {streamData.liveSpeed || 0} tok/s</span>
              <span>·</span>
              <span>~{streamData.liveTokens || 0} tokens</span>
              <span>·</span>
              <span>{t.tools.thinking}</span>
            </div>
          )}

          {/* Full LM Studio style metrics bar when completed */}
          {!streamData.isStreaming && (
            <div className={styles.metricsBar}>
              {streamData.speedTokPerSec !== undefined && (
                <span className={styles.speedBadge} title={t.tools.speedTitle}>
                  <Zap size={12} aria-hidden /> {streamData.speedTokPerSec} tok/s
                </span>
              )}
              {streamData.inputTokens !== undefined && streamData.outputTokens !== undefined && (
                <span className={styles.tokensBadge} title={t.tools.tokensTitle}>
                  <BarChart2 size={12} aria-hidden /> {streamData.inputTokens}p + {streamData.outputTokens}g = {streamData.inputTokens + streamData.outputTokens} tok
                </span>
              )}
              {streamData.contextTokens !== undefined && (
                <span className={styles.contextBadge} title={t.tools.contextTitle}>
                  <Layers size={12} aria-hidden /> Context: {streamData.contextTokens.toLocaleString()}
                  {/* Chỉ hiện giới hạn cửa sổ khi server báo — không đoán 4096. */}
                  {streamData.contextLimit
                    ? ` / ${streamData.contextLimit.toLocaleString()} (${Math.round((streamData.contextTokens / streamData.contextLimit) * 100)}%)`
                    : ''}
                </span>
              )}
              {streamData.latencyMs !== undefined && (
                <span><Clock size={12} aria-hidden /> {Math.round(streamData.latencyMs)}ms</span>
              )}
              {streamData.confidence !== undefined && (
                <span>{t.tools.confidence(fmtPercent(streamData.confidence))}</span>
              )}
              {streamData.promptVersion && (
                <span>{t.tools.prompt} <span className={styles.mono}>{streamData.promptVersion}</span></span>
              )}
              {streamData.turnId && (
                <span>{t.tools.turn} <span className={styles.mono}>{streamData.turnId.slice(0, 8)}</span></span>
              )}
              {streamData.guardrailTriggered && (
                <Badge tone="danger">Guard: {streamData.guardrailTriggered}</Badge>
              )}
            </div>
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
