/** Kiểu của các studio thử trên console (ai bug-018); đường API ở services/apiEndpoints/studio.endpoint.ts. */
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
  plate_text?: string;
  plate?: string;
  confidence?: number;
  vehicle_type?: string;
  latency_ms?: number;
}

export interface VerifyMatchResult {
  is_matched: boolean;
  similarity_score?: number | null;
  mismatch_reason?: string;
}
