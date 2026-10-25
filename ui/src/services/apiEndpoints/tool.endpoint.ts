import { apiClient } from '../apiClient';
import type { CopilotAnswer, IngestResult, SeedDocument, SystemCheck } from '@/types/tool';

export const TOOL_ENDPOINTS = {
  SYSTEM_CHECK: '/tools/system',
  TRY_COPILOT: '/tools/copilot',
  // SSE: apiClient không đọc stream nên ChatStudio gọi fetch với API_BASE + đường này.
  TRY_COPILOT_STREAM: '/tools/copilot/stream',
  INGEST_KNOWLEDGE: '/tools/knowledge',
  KNOWLEDGE_DOCUMENTS: '/tools/knowledge/documents',
  DELETE_KNOWLEDGE_DOCUMENT: (id: string) => `/tools/knowledge/documents/${id}`,
} as const;

export const getSystemCheck = (): Promise<SystemCheck> =>
  apiClient.getOne<SystemCheck>(TOOL_ENDPOINTS.SYSTEM_CHECK);

export const tryCopilot = (query: string, parkingLotId: string): Promise<CopilotAnswer> =>
  apiClient.postOne<CopilotAnswer>(TOOL_ENDPOINTS.TRY_COPILOT, {
    query,
    parking_lot_id: parkingLotId || null,
  });

export const ingestDraft = (form: FormData): Promise<IngestResult> =>
  apiClient.postOne<IngestResult>(TOOL_ENDPOINTS.INGEST_KNOWLEDGE, form);

export const getKnowledgeDocuments = (parkingLotId?: string): Promise<SeedDocument[]> => {
  const query = parkingLotId ? `?parking_lot_id=${encodeURIComponent(parkingLotId)}` : '';
  return apiClient.get<SeedDocument>(`${TOOL_ENDPOINTS.KNOWLEDGE_DOCUMENTS}${query}`);
};

export const deleteKnowledgeDocument = (
  documentId: string,
  parkingLotId?: string,
): Promise<{ deleted: number; document_id: string }> => {
  const query = parkingLotId ? `?parking_lot_id=${encodeURIComponent(parkingLotId)}` : '';
  return apiClient.deleteOne<{ deleted: number; document_id: string }>(
    `${TOOL_ENDPOINTS.DELETE_KNOWLEDGE_DOCUMENT(documentId)}${query}`,
  );
};

export const toolApi = {
  systemCheck: getSystemCheck,
  tryCopilot,
  ingestDraft,
  getKnowledgeDocuments,
  deleteKnowledgeDocument,
};
