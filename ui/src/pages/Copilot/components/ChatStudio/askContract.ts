import type { PlaygroundParams } from './types';

/**
 * Hợp đồng body POST /tools/copilot/stream (ai bug-017). Giữ khớp với
 * app/api/rest/routes/console_tools_controller.py (ASK_BODY_FIELDS, AskIn): AskIn cấm
 * trường lạ (extra="forbid"), nên gửi thừa một khoá là nhận 422.
 */
export const ASK_BODY_FIELDS = ['query', 'parking_lot_id', 'min_similarity', 'top_k', 'temperature'] as const;

export type AskBody = {
  query: string;
  parking_lot_id: string | null;
  min_similarity: number;
  top_k: number;
  temperature: number;
};

export function buildAskBody(query: string, params: PlaygroundParams): AskBody {
  return {
    query,
    parking_lot_id: params.parkingLotId.trim() || null,
    min_similarity: params.minSimilarity,
    top_k: params.topK,
    temperature: params.temperature,
  };
}
