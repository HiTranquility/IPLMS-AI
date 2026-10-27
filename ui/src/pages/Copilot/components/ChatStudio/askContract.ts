import type { PlaygroundParams } from './types';

/**
 * Hợp đồng body POST /tools/copilot/stream (ai bug-017). Giữ khớp với
 * app/api/rest/routes/console_tools_controller.py (ASK_BODY_FIELDS, AskIn): AskIn cấm
 * trường lạ (extra="forbid"), nên gửi thừa một khoá là nhận 422.
 */
export const ASK_BODY_FIELDS = ['query', 'parking_lot_id', 'min_similarity', 'top_k', 'temperature', 'history'] as const;

export type ChatHistoryItem = {
  role: 'user' | 'assistant';
  content: string;
};

export type AskBody = {
  query: string;
  parking_lot_id: string | null;
  min_similarity: number;
  top_k: number;
  temperature: number;
  history: ChatHistoryItem[] | null;
};

export function buildAskBody(query: string, params: PlaygroundParams, history?: ChatHistoryItem[]): AskBody {
  return {
    query,
    parking_lot_id: params.parkingLotId.trim() || null,
    min_similarity: params.minSimilarity,
    top_k: params.topK,
    temperature: params.temperature,
    history: history && history.length > 0 ? history : null,
  };
}
