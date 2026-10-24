import { type FormEvent, useEffect, useRef, useState } from 'react';
import { useSystemCheck } from '@/hooks/queries/useToolQueries';
import { useI18n } from '@/i18n/I18nProvider';
import { API_BASE, ApiError } from '@/services/apiClient';
import { TOOL_ENDPOINTS } from '@/services/apiEndpoints/tool.endpoint';
import { buildAskBody } from './askContract';
import { ChatInput } from './ChatInput';
import { ChatSidebar } from './ChatSidebar';
import { ChatStream } from './ChatStream';
import { ChatStudioHeader } from './ChatStudioHeader';
import { InspectorDrawer } from './InspectorDrawer';
import type {
  ChatMessage,
  InspectorTab,
  PlaygroundParams,
  PromptPreset,
  RagSource,
  SeedDocument,
} from './types';
import styles from './ChatStudio.module.css';

const DEFAULT_PRESETS: PromptPreset[] = [
  {
    id: 'p1',
    category: 'Biểu phí & Vé',
    title: 'Biểu phí giữ xe máy qua đêm và ngày lễ',
    query: 'Biểu phí gửi xe máy theo lượt ban ngày, ban đêm và phụ thu ngày lễ tại bãi đỗ xe trung tâm được quy định như thế nào?',
  },
  {
    id: 'p2',
    category: 'Tranh chấp & Sự cố',
    title: 'Quy trình xử lý mất thẻ giữ xe',
    query: 'Khách hàng làm mất thẻ xe thì thủ tục xác minh phương tiện và mức bồi thường chi phí phát hành thẻ mới là bao nhiêu?',
  },
  {
    id: 'p3',
    category: 'Quy chế bãi đỗ',
    title: 'Thời hạn lưu đỗ tối đa và xử lý xe vô chủ',
    query: 'Thời gian lưu bãi tối đa cho xe gửi vé lượt là bao lâu? Sau bao lâu xe không có người nhận sẽ lập biên bản xử lý vi phạm?',
  },
  {
    id: 'p4',
    category: 'Phương tiện ưu tiên',
    title: 'Quy định xe cứu hỏa, cấp cứu và công vụ',
    query: 'Các loại xe ưu tiên nào được miễn phí vé gửi xe khi vào bãi đỗ theo quy chế hiện hành của tòa nhà?',
  },
];

export function ChatStudio() {
  const { t } = useI18n();
  // Tên model lấy từ /tools/system; chưa có thì "—", không tự đặt tên (ai bug-018).
  const systemQuery = useSystemCheck();
  const activeModelName = systemQuery.data?.llm_model || '—';

  // State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('citations');
  const [selectedCitation, setSelectedCitation] = useState<RagSource | null>(null);

  const [params, setParams] = useState<PlaygroundParams>({
    temperature: 0.1,
    maxTokens: 512,
    minSimilarity: 0.72,
    topK: 4,
    parkingLotId: '',
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  // Autoscroll khi có chunk mới (dùng optional chaining an toàn cho jsdom)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Phím tắt bàn phím
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K hoặc Cmd+K để focus ô chat
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      // Escape để đóng drawer hoặc dừng stream
      if (e.key === 'Escape') {
        if (isStreaming) {
          handleStopStreaming();
        } else if (inspectorOpen) {
          setInspectorOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isStreaming, inspectorOpen]);

  // Lấy tin nhắn trợ lý mới nhất
  const latestAssistantMessage = [...messages].reverse().find((m) => m.role === 'assistant') || null;

  // Gửi câu hỏi & SSE Streaming
  const handleSubmit = async (e?: FormEvent) => {
    e?.preventDefault();
    const query = inputQuery.trim();
    if (!query || isStreaming) return;

    const userMessage: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: query,
      at: new Date().toISOString(),
    };

    const botMessageId = `bot_${Date.now()}`;
    const botPlaceholder: ChatMessage = {
      id: botMessageId,
      role: 'assistant',
      content: '',
      at: new Date().toISOString(),
      isStreaming: true,
      ragSources: [],
    };

    setMessages((prev) => [...prev, userMessage, botPlaceholder]);
    setInputQuery('');
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const startTime = performance.now();
    let accumulatedContent = '';
    let ragSourcesExtracted: RagSource[] = [];
    let promptVersion = '';
    let latencyMs = 0;
    let inputTokens = 0;
    let outputTokens = 0;
    let speedTokPerSec = 0;
    let refused = false;
    let guardrailTriggered: string | undefined;
    let confidence: number | undefined;
    let turnId = '';

    try {
      const response = await fetch(`${API_BASE}${TOOL_ENDPOINTS.TRY_COPILOT_STREAM}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-Console-Request': '1',
        },
        body: JSON.stringify(buildAskBody(query, params)),
        signal: controller.signal,
      });

      if (!response.ok) {
        // Lỗi trả về theo envelope console ({message, code}); 422 của FastAPI chỉ có `detail`.
        const body = (await response.json().catch(() => null)) as { message?: string; code?: string } | null;
        const message =
          body?.message ?? (response.status === 422 ? t.errors.invalidData : t.errors.http(response.status));
        throw new ApiError(response.status, body?.code ?? `HTTP_${response.status}`, message, Boolean(body?.message));
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(':')) continue;

          if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.slice(5).trim();
            if (dataStr === '[DONE]') continue;

            try {
              const parsed = JSON.parse(dataStr);

              // Trường SSE theo console_tools_controller.try_copilot_stream.
              if (typeof parsed.token === 'string') accumulatedContent += parsed.token;
              if (Array.isArray(parsed.sources) && parsed.sources.length > 0) {
                ragSourcesExtracted = parsed.sources.map((title: string) => ({ title }));
              }
              if (parsed.refused) refused = true;
              if (parsed.guardrail_triggered) guardrailTriggered = parsed.guardrail_triggered;
              if (typeof parsed.confidence === 'number') confidence = parsed.confidence;
              if (parsed.turn_id) turnId = parsed.turn_id;

              if (parsed.prompt_version) promptVersion = parsed.prompt_version;
              if (parsed.latency_ms) latencyMs = parsed.latency_ms;
              if (parsed.input_tokens) inputTokens = parsed.input_tokens;
              if (parsed.output_tokens) outputTokens = parsed.output_tokens;
              if (parsed.speed_tok_s) speedTokPerSec = parsed.speed_tok_s;

              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botMessageId
                    ? {
                        ...m,
                        content: accumulatedContent,
                        ragSources: ragSourcesExtracted.length > 0 ? ragSourcesExtracted : m.ragSources,
                        promptVersion: promptVersion || m.promptVersion,
                        latencyMs: latencyMs || m.latencyMs,
                        inputTokens: inputTokens || m.inputTokens,
                        outputTokens: outputTokens || m.outputTokens,
                        speedTokPerSec: speedTokPerSec || m.speedTokPerSec,
                      }
                    : m,
                ),
              );
            } catch {
              // Bỏ qua lỗi parse chunk SSE
            }
          }
        }
      }

      // Kết thúc stream thành công
      const elapsedTotal = Math.round(performance.now() - startTime);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMessageId
            ? {
                ...m,
                content: accumulatedContent || t.studio.chatEmptyAnswer,
                isStreaming: false,
                status: refused ? 'REFUSED' : 'SUCCESS',
                guardrailTriggered,
                confidence,
                turnId: turnId || undefined,
                latencyMs: latencyMs || elapsedTotal,
                // Chỉ số do server đo; không có thì để trống, không ước lượng.
                speedTokPerSec: speedTokPerSec || undefined,
              }
            : m,
        ),
      );
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMessageId
              ? {
                  ...m,
                  content: `${accumulatedContent}\n\n*(${t.studio.chatStopped})*`,
                  isStreaming: false,
                }
              : m,
          ),
        );
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMessageId
              ? {
                  ...m,
                  content: t.studio.chatError(err instanceof Error ? err.message : t.errors.network),
                  isStreaming: false,
                  status: 'ERROR',
                }
              : m,
          ),
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopStreaming = () => {
    abortControllerRef.current?.abort();
  };

  const handleSelectPreset = (prompt: string) => {
    setInputQuery(prompt);
    inputRef.current?.focus();
  };

  const handleSelectCitation = (citation: RagSource) => {
    setSelectedCitation(citation);
    setInspectorTab('citations');
    setInspectorOpen(true);
  };

  const handleAskAboutDocument = (doc: SeedDocument) => {
    const prompt = `Cho tôi biết chi tiết về quy định: "${doc.title}". Văn bản này có những điều khoản then chốt nào và áp dụng ra sao?`;
    setInputQuery(prompt);
    inputRef.current?.focus();
  };

  const handleAskAboutDispute = (summary: string) => {
    setInputQuery(summary);
    inputRef.current?.focus();
  };

  const handleFeedback = (messageId: string, feedbackVal: 1 | -1) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, feedback: m.feedback === feedbackVal ? null : feedbackVal }
          : m,
      ),
    );
  };

  const handleNewChat = () => {
    if (isStreaming) handleStopStreaming();
    setMessages([]);
    setInputQuery('');
    setSelectedCitation(null);
    inputRef.current?.focus();
  };

  const handleExportMarkdown = () => {
    if (messages.length === 0) return;
    const dateStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    let md = `# IPLMS Copilot Chat Transcript\n*Ngày xuất: ${new Date().toLocaleString('vi-VN')}*\n\n---\n\n`;

    messages.forEach((m) => {
      if (m.role === 'user') {
        md += `### [User] Người hỏi (${new Date(m.at).toLocaleTimeString('vi-VN')})\n\n${m.content}\n\n`;
      } else {
        md += `### [Copilot] Copilot Studio (${new Date(m.at).toLocaleTimeString('vi-VN')})\n\n${m.content}\n\n`;
        if (m.ragSources && m.ragSources.length > 0) {
          md += `**Trích dẫn RAG:**\n`;
          m.ragSources.forEach((s) => {
            md += `- ${s.title}${s.score ? ` (Độ tương đồng: ${(s.score * 100).toFixed(0)}%)` : ''}\n`;
          });
          md += `\n`;
        }
        if (m.latencyMs || m.speedTokPerSec) {
          md += `*Chỉ số: ${m.latencyMs ? `${m.latencyMs}ms` : ''} ${m.speedTokPerSec ? `| ${m.speedTokPerSec} t/s` : ''}*\n\n`;
        }
      }
      md += `---\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `copilot-transcript-${dateStr}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={styles.studioWrapper}>
      {/* 1. Header */}
      <ChatStudioHeader
        model={activeModelName}
        isStreaming={isStreaming}
        sidebarOpen={sidebarOpen}
        inspectorOpen={inspectorOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onToggleInspector={() => setInspectorOpen((v) => !v)}
        onExportMarkdown={handleExportMarkdown}
        onNewChat={handleNewChat}
        hasMessages={messages.length > 0}
      />

      {/* 2. Workspace 3 cột */}
      <div className={styles.studioBody}>
        {/* Cột trái: Presets & History */}
        <ChatSidebar
          isOpen={sidebarOpen}
          presets={DEFAULT_PRESETS}
          onSelectPreset={handleSelectPreset}
          onNewChat={handleNewChat}
          onClearChat={handleNewChat}
          hasMessages={messages.length > 0}
          isStreaming={isStreaming}
        />

        {/* Cột giữa: Chat Stream & Input */}
        <main className={styles.chatCenter}>
          <ChatStream
            messages={messages}
            presets={DEFAULT_PRESETS}
            onSelectPreset={handleSelectPreset}
            onSelectCitation={handleSelectCitation}
            onFeedback={handleFeedback}
            messagesEndRef={messagesEndRef}
          />

          <ChatInput
            inputQuery={inputQuery}
            setInputQuery={setInputQuery}
            onSubmit={handleSubmit}
            isStreaming={isStreaming}
            onStopStreaming={handleStopStreaming}
            inputRef={inputRef}
          />
        </main>

        {/* Cột phải: Inspector Drawer */}
        <InspectorDrawer
          isOpen={inspectorOpen}
          onClose={() => setInspectorOpen(false)}
          activeTab={inspectorTab}
          setActiveTab={setInspectorTab}
          activeMessage={latestAssistantMessage}
          params={params}
          setParams={setParams}
          selectedCitation={selectedCitation}
          onAskAboutDocument={handleAskAboutDocument}
          onAskAboutDispute={handleAskAboutDispute}
        />
      </div>
    </div>
  );
}

export default ChatStudio;
