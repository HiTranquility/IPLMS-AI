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
}
