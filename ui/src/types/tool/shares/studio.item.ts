/** Kiểu của các studio thử trên console (ai bug-018); đường API ở services/apiEndpoints/studio.endpoint.ts. */
/** Một tài liệu thật trong kho tri thức (`GET /tools/knowledge/documents`): metadata, không kèm nội dung. */
export interface SeedDocument {
  id?: string;
  document_id?: string;
  category: 'regulation' | 'tariff' | 'fine_policy' | 'ev_charging' | string;
  title: string;
  content?: string;
  source: string;
  parking_lot_id?: string | null;
  chunk_count?: number;
  latest_version_no?: number;
  latest_status?: string;
  published_version_no?: number;
  updated_at?: string;
}

export interface DisputeStep {
  step: number;
  node: string;
  status: 'COMPLETED' | 'RUNNING' | 'AWAITING_STAFF_SIGN_OFF' | 'FAILED' | 'PENDING';
  description: string;
  data: Record<string, unknown>;
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

export interface AnprRecognizeResult {
  plate_number?: string;
  plate_text?: string;
  plate?: string;
  confidence?: number | null;
  vehicle_type?: string | null;
  plate_color?: string | null;
  latency_ms?: number | null;
  crop_image?: string | null;
  crop_plate_image_url?: string | null;
}

export interface VerifyMatchResult {
  is_matched: boolean;
  similarity_score?: number | null;
  mismatch_reason?: string;
}
