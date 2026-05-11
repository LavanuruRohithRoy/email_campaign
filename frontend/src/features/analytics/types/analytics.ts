export interface CampaignAnalytics {
  campaign_id: string;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  complained: number;
  unsubscribed: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
  complaint_rate: number;
  unsubscribe_rate: number;
}

export interface DashboardAnalytics {
  total_contacts: number;
  active_contacts: number;
  total_campaigns: number;
  total_sent: number;
  total_opens: number;
  total_clicks: number;
  avg_open_rate: number;
  avg_click_rate: number;
}

export interface AnalyticsTimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface CampaignPerformanceItem {
  campaign_id: string;
  campaign_name: string;
  sent: number;
  open_rate: number;
  click_rate: number;
  created_at: string;
}

export interface TopCampaignsResponse {
  items: CampaignPerformanceItem[];
}

export interface AnalyticsExportResponse {
  download_url: string;
}

export interface SendProgress {
  total: number;
  sent: number;
  status: string;
}
