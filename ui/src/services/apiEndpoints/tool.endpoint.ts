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
  GET_DOCUMENT_CHUNKS: (id: string) => `/tools/knowledge/documents/${id}/chunks`,
} as const;

export interface DocumentChunk {
  ordinal: number;
  section_title: string;
  content: string;
}

export interface DocumentVersion {
  version_no: number;
  status: string;
  chunk_count: number;
  created_at: string;
  published_at: string;
}

export interface DocumentChunksData {
  version_no: number;
  status: string;
  total: number;
  chunks: DocumentChunk[];
  versions: DocumentVersion[];
}

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

export const getDocumentChunks = (
  documentId: string,
  parkingLotId?: string,
  versionNo: number = 0,
): Promise<DocumentChunksData> => {
  const params = new URLSearchParams();
  if (parkingLotId) params.set('parking_lot_id', parkingLotId);
  if (versionNo > 0) params.set('version_no', String(versionNo));
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiClient.getOne<DocumentChunksData>(
    `${TOOL_ENDPOINTS.GET_DOCUMENT_CHUNKS(documentId)}${query}`,
  );
};

export const toolApi = {
  systemCheck: getSystemCheck,
  tryCopilot,
  ingestDraft,
  getKnowledgeDocuments,
  deleteKnowledgeDocument,
  getDocumentChunks,
};
