import { BarChart3, ContactRound, ListChecks, MailOpen, MousePointerClick, Send } from "lucide-react";

import { StatCard } from "@/features/analytics/components/stat-card";
import { TimeseriesChart } from "@/features/analytics/components/timeseries-chart";
import { TopCampaignsTable } from "@/features/analytics/components/top-campaigns-table";
import { useClickTimeseries, useDashboardAnalytics, useOpenTimeseries, useTopCampaigns } from "@/features/analytics/hooks/use-analytics";

function pct(value: number | undefined) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function DashboardPage() {
  const dashboard = useDashboardAnalytics();
  const opens = useOpenTimeseries(30);
  const clicks = useClickTimeseries(30);
  const topCampaigns = useTopCampaigns(5);
  const hasError = dashboard.isError || opens.isError || clicks.isError || topCampaigns.isError;

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal">Dashboard</h2>
        <p className="text-sm text-muted-foreground">Live analytics from subscriber events and campaign activity.</p>
      </div>
      {hasError ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          Some analytics data could not be loaded. Please retry.
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total contacts" value={dashboard.data?.total_contacts} icon={ContactRound} loading={dashboard.isLoading} />
        <StatCard label="Active contacts" value={dashboard.data?.active_contacts} icon={ListChecks} loading={dashboard.isLoading} />
        <StatCard label="Campaigns" value={dashboard.data?.total_campaigns} icon={Send} loading={dashboard.isLoading} />
        <StatCard label="Total opens" value={dashboard.data?.total_opens} icon={MailOpen} loading={dashboard.isLoading} />
        <StatCard label="Total clicks" value={dashboard.data?.total_clicks} icon={MousePointerClick} loading={dashboard.isLoading} />
        <StatCard label="Total sent" value={dashboard.data?.total_sent} icon={Send} loading={dashboard.isLoading} />
        <StatCard label="Avg open rate" value={pct(dashboard.data?.avg_open_rate)} icon={BarChart3} loading={dashboard.isLoading} />
        <StatCard label="Avg click rate" value={pct(dashboard.data?.avg_click_rate)} icon={BarChart3} loading={dashboard.isLoading} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <TimeseriesChart title="Opens over time" data={opens.data} loading={opens.isLoading} />
        <TimeseriesChart title="Clicks over time" data={clicks.data} loading={clicks.isLoading} />
      </div>
      <TopCampaignsTable items={topCampaigns.data?.items} loading={topCampaigns.isLoading} />
    </section>
  );
}
