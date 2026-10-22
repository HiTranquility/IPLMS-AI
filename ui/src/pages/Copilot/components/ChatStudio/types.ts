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

export interface SeedDocument {
  id?: string;
  category: 'regulation' | 'tariff' | 'fine_policy' | 'ev_charging' | string;
  title: string;
  content: string;
  source: string;
  parking_lot_id?: string | null;
}

export interface DisputeStep {
  step: number;
  node: string;
  status: 'COMPLETED' | 'RUNNING' | 'AWAITING_STAFF_SIGN_OFF' | 'FAILED' | 'PENDING';
  description: string;
  data: Record<string, any>;
}

export interface DisputeSimulationResult {
  success: boolean;
  dispute_id: string;
  workflow: string;
  nodes_traversed: number;
  steps: DisputeStep[];
  final_status: string;
}

export interface DisputeSimulationPayload {
  dispute_id: string;
  claimed_amount: number;
  claim_reason: string;
  has_checkin_snapshot: boolean;
  has_checkout_snapshot: boolean;
}

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
      minSimilarity: 0.75,
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
      minSimilarity: 0.68,
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
      minSimilarity: 0.72,
    },
  },
];
