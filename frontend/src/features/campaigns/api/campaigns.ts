import { api, unwrap } from "@/lib/api";

export interface CampaignCreatePayload {
  name: string;
  subject: string;
  preview_text?: string | null;
  from_name: string;
  from_email: string;
  reply_to?: string | null;
  target_list_ids: string[];
  target_segment_ids: string[];
  exclude_list_ids: string[];
  template_id?: string | null;
}

export interface CampaignResponse {
  id: string;
  subject: string;
  name: string;
  status: string;
  recipient_count: number;
}

export interface RecipientCountResponse {
  estimated_count: number;
}

export interface CampaignRecipientsPayload {
  target_list_ids: string[];
  target_segment_ids: string[];
  exclude_list_ids: string[];
}

export interface CampaignSchedulePayload {
  scheduled_at: string;
  timezone: string;
}

export function createCampaign(payload: CampaignCreatePayload) {
  return unwrap(api.post<CampaignResponse>("/api/v1/campaigns", payload));
}

export function updateCampaignRecipients(campaignId: string, payload: CampaignRecipientsPayload) {
  return unwrap(api.put<{ updated: boolean }>(`/api/v1/campaigns/${campaignId}/recipients`, payload));
}

export function getRecipientCount(campaignId: string) {
  return unwrap(api.get<RecipientCountResponse>(`/api/v1/campaigns/${campaignId}/recipient-count`));
}

export function scheduleCampaign(campaignId: string, payload: CampaignSchedulePayload) {
  return unwrap(api.post<CampaignResponse>(`/api/v1/campaigns/${campaignId}/schedule`, payload));
}

export function sendCampaign(campaignId: string) {
  return unwrap(api.post<{ status: string; queued: number }>(`/api/v1/campaigns/${campaignId}/send`));
}
