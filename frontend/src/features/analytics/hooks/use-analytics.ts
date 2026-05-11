import { useQuery } from "@tanstack/react-query";

import {
  getCampaignAnalytics,
  getClickTimeseries,
  getDashboardAnalytics,
  getOpenTimeseries,
  getSendProgress,
  getTopCampaigns,
} from "@/features/analytics/api/analytics-api";

export function useDashboardAnalytics() {
  return useQuery({ queryKey: ["analytics", "dashboard"], queryFn: getDashboardAnalytics });
}

export function useCampaignAnalytics(campaignId: string) {
  return useQuery({
    queryKey: ["analytics", "campaign", campaignId],
    queryFn: () => getCampaignAnalytics(campaignId),
    enabled: Boolean(campaignId),
  });
}

export function useTopCampaigns(limit = 10) {
  return useQuery({ queryKey: ["analytics", "top-campaigns", limit], queryFn: () => getTopCampaigns(limit) });
}

export function useOpenTimeseries(days = 30) {
  return useQuery({ queryKey: ["analytics", "opens", days], queryFn: () => getOpenTimeseries(days) });
}

export function useClickTimeseries(days = 30) {
  return useQuery({ queryKey: ["analytics", "clicks", days], queryFn: () => getClickTimeseries(days) });
}

export function useSendProgress(campaignId: string) {
  return useQuery({
    queryKey: ["campaigns", campaignId, "progress"],
    queryFn: () => getSendProgress(campaignId),
    enabled: Boolean(campaignId),
    refetchInterval: 5000,
  });
}
