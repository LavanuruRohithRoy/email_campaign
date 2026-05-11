import { api, unwrap } from "@/lib/api";
import type {
  AnalyticsExportResponse,
  AnalyticsTimeSeriesPoint,
  CampaignAnalytics,
  SendProgress,
  TopCampaignsResponse,
  DashboardAnalytics,
} from "@/features/analytics/types/analytics";

export function getDashboardAnalytics() {
  return unwrap(api.get<DashboardAnalytics>("/api/v1/analytics/dashboard"));
}

export function getCampaignAnalytics(campaignId: string) {
  return unwrap(api.get<CampaignAnalytics>(`/api/v1/analytics/campaigns/${campaignId}`));
}

export function getTopCampaigns(limit = 10) {
  return unwrap(api.get<TopCampaignsResponse>("/api/v1/analytics/campaigns/top", { params: { limit } }));
}

export function getOpenTimeseries(days = 30) {
  return unwrap(api.get<AnalyticsTimeSeriesPoint[]>("/api/v1/analytics/timeseries/opens", { params: { days } }));
}

export function getClickTimeseries(days = 30) {
  return unwrap(api.get<AnalyticsTimeSeriesPoint[]>("/api/v1/analytics/timeseries/clicks", { params: { days } }));
}

export function exportCampaignCsv(campaignId: string) {
  return unwrap(api.post<AnalyticsExportResponse>(`/api/v1/analytics/campaigns/${campaignId}/export`));
}

export function getSendProgress(campaignId: string) {
  return unwrap(api.get<SendProgress>(`/api/v1/campaigns/${campaignId}/progress`));
}
