export type DataOrigin = "DEMO" | "LIVE";
export type IntegrationState = "NOT_CONFIGURED" | "CONNECTED" | "DEGRADED" | "ERROR";

export interface Principal {
  user_id: string;
  organization_id: string;
  organization_slug: string;
  email: string;
}

export interface LoginCredentials {
  organization_slug: string;
  email: string;
  password: string;
}

export interface AttentionItem {
  item_id: string;
  tenant_id: string;
  owner_id: string;
  source_id: string;
  score: number;
  summary: string;
  importance_reason: string;
  next_step: string;
  source_timestamp: string;
  data_origin: DataOrigin;
}

export interface IntegrationStatus {
  integration_id: string;
  provider: string;
  status: IntegrationState;
  last_sync_at: string | null;
  detail: string;
  data_origin: DataOrigin;
}

export interface SourceDetail {
  source_id: string;
  tenant_id: string;
  owner_id: string;
  external_id: string;
  source_type: string;
  title: string;
  content: string;
  source_timestamp: string;
  source_url: string | null;
  data_origin: DataOrigin;
}

export interface Digest {
  digest_id: string;
  generated_at: string;
  attention_items: AttentionItem[];
  integrations: IntegrationStatus[];
  data_origin: DataOrigin;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Array<{ field: string; message: string; type: string }>;
  };
}
