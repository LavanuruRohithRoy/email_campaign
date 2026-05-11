import { TimeseriesChart } from "@/features/analytics/components/timeseries-chart";
import { TopCampaignsTable } from "@/features/analytics/components/top-campaigns-table";
import { useClickTimeseries, useOpenTimeseries, useTopCampaigns } from "@/features/analytics/hooks/use-analytics";

export function AnalyticsPage() {
  const opens = useOpenTimeseries(30);
  const clicks = useClickTimeseries(30);
  const topCampaigns = useTopCampaigns(10);

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal">Analytics</h2>
        <p className="text-sm text-muted-foreground">Campaign performance, subscriber engagement, and reporting trends.</p>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <TimeseriesChart title="Open trend" data={opens.data} loading={opens.isLoading} />
        <TimeseriesChart title="Click trend" data={clicks.data} loading={clicks.isLoading} />
      </div>
      <TopCampaignsTable items={topCampaigns.data?.items} loading={topCampaigns.isLoading} />
    </section>
  );
}
