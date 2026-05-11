export type SavingState = "idle" | "saving" | "saved" | "error";

export type MergeTagKey =
  | "first_name"
  | "last_name"
  | "email"
  | "company"
  | "unsubscribe_url";

export interface EditorExportData {
  html: string;
  design: Record<string, unknown>;
}

export interface TemplateBuilderSavePayload {
  name: string;
  subject: string;
  html_content: string;
  design_json: Record<string, unknown>;
  is_draft: boolean;
}

export interface TemplateBuilderSaveResponse {
  id: string;
  status: string;
}

export interface TemplatePreviewPayload {
  html_content: string;
  sample_data: Partial<Record<MergeTagKey, string>>;
}

export interface TemplatePreviewResponse {
  html: string;
}

export interface TestEmailPayload {
  to_email: string;
  subject: string;
  html_content: string;
}

export interface TestEmailResponse {
  message_id: string;
}

export interface TemplateSummary {
  id: string;
  name: string;
  category: string | null;
  updated_at: string;
  created_at: string;
}

export interface TemplateDetail {
  id: string;
  html: string;
  name: string;
  category: string | null;
}
