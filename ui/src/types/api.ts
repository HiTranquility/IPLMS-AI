/** Envelope chuẩn của REST API AI Console (`app/api/rest/routes/console_*`). */
export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T[];
  total?: number;
  code?: string;
  detail?: unknown;
}

export type Envelope<T> = ApiEnvelope<T>;
