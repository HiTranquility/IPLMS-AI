import { apiClient } from '../apiClient';
import type {
  AnprRecognizeResult,
  DisputeSimulationPayload,
  DisputeSimulationResult,
  SeedDocument,
  VerifyMatchResult,
} from '@/types/tool';

/**
 * Đường API của các studio thử (ai bug-018). Tới 2026-10-24 console CHƯA gắn các route
 * này (`app/console_main.py` chỉ có `console_router`), nên gọi sẽ nhận 404 và UI báo lỗi
 * thay vì tự bịa kết quả. Khi backend thêm route thì UI dùng được ngay, không sửa gì.
 */
export const STUDIO_ENDPOINTS = {
  DISPUTE_SIMULATE: '/copilot/dispute-workflow/simulate',
  KNOWLEDGE_SEEDS: '/knowledge/seeds',
  ANPR_RECOGNIZE: '/anpr/recognize',
  VERIFY_MATCH: '/vision/verify-match',
} as const;

export const simulateDispute = (payload: DisputeSimulationPayload): Promise<DisputeSimulationResult> =>
  apiClient.postOne<DisputeSimulationResult>(STUDIO_ENDPOINTS.DISPUTE_SIMULATE, payload);

export const getKnowledgeSeeds = (): Promise<SeedDocument[]> =>
  apiClient.get<SeedDocument>(STUDIO_ENDPOINTS.KNOWLEDGE_SEEDS);

export const recognizePlate = (form: FormData): Promise<AnprRecognizeResult> =>
  apiClient.postOne<AnprRecognizeResult>(STUDIO_ENDPOINTS.ANPR_RECOGNIZE, form);

export const verifyMatch = (body: Record<string, unknown>): Promise<VerifyMatchResult> =>
  apiClient.postOne<VerifyMatchResult>(STUDIO_ENDPOINTS.VERIFY_MATCH, body);

export const studioApi = {
  simulateDispute,
  knowledgeSeeds: getKnowledgeSeeds,
  recognizePlate,
  verifyMatch,
};
