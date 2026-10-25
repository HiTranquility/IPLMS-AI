export type MessageRole = 'user' | 'assistant';

export interface RagSource {
  title: string;
  score?: number;
  chunkId?: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  at: string;
  status?: 'SUCCESS' | 'REFUSED' | 'NO_CONTEXT' | 'ERROR';
  sources?: string[];
  ragSources?: RagSource[];
  confidence?: number;
  promptVersion?: string;
  turnId?: string;
  latencyMs?: number;
  speedTokPerSec?: number;
  inputTokens?: number;
  outputTokens?: number;
  feedback?: 1 | -1 | null;
  guardrailTriggered?: string;
  isStreaming?: boolean;
  reviewVerdict?: 'CORRECT' | 'INCORRECT' | 'UNSAFE';
  promotedToEval?: boolean;
  userQuery?: string;
}

export interface PromptPreset {
  id: string;
  title: string;
  category: string;
  query: string;
  icon?: string;
}

export interface PlaygroundParams {
  temperature: number;
  maxTokens: number;
  minSimilarity: number;
  topK: number;
  parkingLotId: string;
  modelProfileId?: string;
}

export type InspectorTab = 'citations' | 'knowledge' | 'dispute' | 'telemetry' | 'params';

export type KnowledgeCategory = 'all' | 'regulation' | 'tariff' | 'fine_policy' | 'ev_charging';

// Kiểu dữ liệu trao đổi với API studio nằm ở tầng types (dùng chung với services).
export type {
  DisputeSimulationPayload,
  DisputeSimulationResult,
  DisputeStep,
  SeedDocument,
} from '@/types/tool';

export interface ModelProfilePreset {
  id: string;
  name: string;
  model: string;
  description: string;
  recommendedFor: string;
  params: {
    temperature: number;
    topK: number;
    maxTokens: number;
    minSimilarity: number;
  };
}

export const MODEL_PROFILES: ModelProfilePreset[] = [
  {
    id: 'gemma-2b',
    name: 'Gemma 2B',
    model: 'gemma:2b',
    description: 'Tra cứu nhanh quy chế cơ bản',
    recommendedFor: 'Tra cứu nhanh quy chế cơ bản, độ trễ cực thấp',
    params: {
      temperature: 0.1,
      topK: 3,
      maxTokens: 512,
      minSimilarity: 0.35,
    },
  },
  {
    id: 'llama3-8b',
    name: 'Llama 3 8B',
    model: 'llama3:8b',
    description: 'Suy luận chuyên sâu tranh chấp thẻ',
    recommendedFor: 'Suy luận chuyên sâu tranh chấp thẻ, đối chiếu logic phức tạp',
    params: {
      temperature: 0.2,
      topK: 5,
      maxTokens: 1024,
      minSimilarity: 0.35,
    },
  },
  {
    id: 'qwen2.5-7b',
    name: 'Qwen 2.5 7B',
    model: 'qwen2.5:7b',
    description: 'Xử lý song ngữ đa dạng biểu phí',
    recommendedFor: 'Xử lý song ngữ đa dạng biểu phí, bảng giá bậc thang',
    params: {
      temperature: 0.15,
      topK: 4,
      maxTokens: 768,
      minSimilarity: 0.40,
    },
  },
];
