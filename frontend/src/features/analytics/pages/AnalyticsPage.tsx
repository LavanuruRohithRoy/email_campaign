import { TimeseriesChart } from "@/features/analytics/components/timeseries-chart";
import { TopCampaignsTable } from "@/features/analytics/components/top-campaigns-table";
import { useClickTimeseries, useOpenTimeseries, useTopCampaigns } from "@/features/analytics/hooks/use-analytics";

export function AnalyticsPage() {
  const opens = useOpenTimeseries(30);
  const clicks = useClickTimeseries(30);
  const topCampaigns = useTopCampaigns(10);
  const hasError = opens.isError || clicks.isError || topCampaigns.isError;

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal">Analytics</h2>
        <p className="text-sm text-muted-foreground">Campaign performance, subscriber engagement, and reporting trends.</p>
      </div>
      {hasError ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          Some reporting data could not be loaded. Please retry.
        </div>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-2">
        <TimeseriesChart title="Open trend" data={opens.data} loading={opens.isLoading} />
        <TimeseriesChart title="Click trend" data={clicks.data} loading={clicks.isLoading} />
      </div>
      <TopCampaignsTable items={topCampaigns.data?.items} loading={topCampaigns.isLoading} />
    </section>
  );
}
