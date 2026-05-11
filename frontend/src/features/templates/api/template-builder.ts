import { api, unwrap } from "@/lib/api";
import type {
  TemplateBuilderSavePayload,
  TemplateBuilderSaveResponse,
  TemplateDetail,
  TemplatePreviewPayload,
  TemplatePreviewResponse,
  TestEmailPayload,
  TestEmailResponse,
} from "@/features/templates/types/template-builder";

export function saveTemplateDraft(payload: TemplateBuilderSavePayload) {
  return unwrap(api.post<TemplateBuilderSaveResponse>("/api/v1/templates/builder/save", payload));
}

export function previewTemplate(payload: TemplatePreviewPayload) {
  return unwrap(api.post<TemplatePreviewResponse>("/api/v1/templates/builder/preview", payload));
}

export function sendTemplateTestEmail(payload: TestEmailPayload) {
  return unwrap(api.post<TestEmailResponse>("/api/v1/templates/builder/test-email", payload));
}

export function getTemplateById(templateId: string) {
  return unwrap(api.get<TemplateDetail>(`/api/v1/templates/${templateId}`));
}
