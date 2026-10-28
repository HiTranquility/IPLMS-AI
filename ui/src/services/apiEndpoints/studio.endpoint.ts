import { apiClient } from '../apiClient';
import type {
  AnprClipResult,
  AnprRecognizeResult,
  DisputeSimulationPayload,
  DisputeSimulationResult,
  SeedDocument,
  VerifyMatchResult,
} from '@/types/tool';

/**
 * Đường API của các studio thử (ai bug-018). ANPR, đối chiếu xe và danh sách tri thức là
 * route thật của console (`console_tools_controller`, chạy service ngay trong process
 * console). Mô phỏng tranh chấp CHƯA có route trên console (workflow LangGraph chưa có
 * bộ nạp bằng chứng thật — ai ISSUE-001), gọi sẽ nhận 404 và UI báo lỗi, không tự bịa.
 */
export const STUDIO_ENDPOINTS = {
  DISPUTE_SIMULATE: '/copilot/dispute-workflow/simulate',
  KNOWLEDGE_DOCUMENTS: '/tools/knowledge/documents',
  ANPR_RECOGNIZE: '/tools/anpr/recognize',
  ANPR_RECOGNIZE_CLIP: '/tools/anpr/recognize-clip',
  VERIFY_MATCH: '/tools/vision/verify-match',
} as const;

export const simulateDispute = (payload: DisputeSimulationPayload): Promise<DisputeSimulationResult> =>
  apiClient.postOne<DisputeSimulationResult>(STUDIO_ENDPOINTS.DISPUTE_SIMULATE, payload);

export const getKnowledgeSeeds = (): Promise<SeedDocument[]> =>
  apiClient.get<SeedDocument>(STUDIO_ENDPOINTS.KNOWLEDGE_DOCUMENTS);

export const recognizePlate = (form: FormData): Promise<AnprRecognizeResult> =>
  apiClient.postOne<AnprRecognizeResult>(STUDIO_ENDPOINTS.ANPR_RECOGNIZE, form);

// Clip không được lưu ở server; giới hạn dung lượng/độ dài nằm ở config AI (REQ-021 F1, F7).
export const recognizeClip = (form: FormData): Promise<AnprClipResult> =>
  apiClient.postOne<AnprClipResult>(STUDIO_ENDPOINTS.ANPR_RECOGNIZE_CLIP, form);

// Server chỉ nhận hai loại xe (extra="forbid"); URL ảnh chưa dùng vì service chưa so ảnh.
export const verifyMatch = (body: { expected_vehicle_type: string; current_vehicle_type: string }): Promise<VerifyMatchResult> =>
  apiClient.postOne<VerifyMatchResult>(STUDIO_ENDPOINTS.VERIFY_MATCH, {
    expected_vehicle_type: body.expected_vehicle_type,
    current_vehicle_type: body.current_vehicle_type,
  });

export const studioApi = {
  simulateDispute,
  knowledgeSeeds: getKnowledgeSeeds,
  recognizePlate,
  recognizeClip,
  verifyMatch,
};
