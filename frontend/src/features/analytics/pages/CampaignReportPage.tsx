import { useMutation } from "@tanstack/react-query";
import { Download, MailCheck, MailOpen, MousePointerClick, ShieldAlert, ThumbsDown, UserMinus } from "lucide-react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { exportCampaignCsv } from "@/features/analytics/api/analytics-api";
import { StatCard } from "@/features/analytics/components/stat-card";
import { TimeseriesChart } from "@/features/analytics/components/timeseries-chart";
import { useCampaignAnalytics, useClickTimeseries, useOpenTimeseries } from "@/features/analytics/hooks/use-analytics";
import { LiveSendProgress } from "@/features/campaigns/components/live-send-progress";

function pct(value: number | undefined) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function CampaignReportPage() {
  const { id = "" } = useParams();
  const analytics = useCampaignAnalytics(id);
  const opens = useOpenTimeseries(30);
  const clicks = useClickTimeseries(30);
  const exportMutation = useMutation({
    mutationFn: () => exportCampaignCsv(id),
    onSuccess: (data) => {
      window.location.assign(data.download_url);
      toast.success("CSV export ready");
    },
    onError: () => toast.error("Could not export campaign report"),
  });

  return (
    <section className="grid gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-normal">Campaign report</h2>
          <p className="text-sm text-muted-foreground">Delivery, engagement, and unsubscribe metrics for this campaign.</p>
        </div>
        <Button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending || !id}>
          <Download className="h-4 w-4" />
          {exportMutation.isPending ? "Exporting" : "Export CSV"}
        </Button>
      </div>
      <LiveSendProgress campaignId={id} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Sent" value={analytics.data?.sent} icon={MailCheck} loading={analytics.isLoading} />
        <StatCard label="Delivered" value={analytics.data?.delivered} icon={MailCheck} loading={analytics.isLoading} />
        <StatCard label="Opened" value={`${analytics.data?.opened ?? 0} (${pct(analytics.data?.open_rate)})`} icon={MailOpen} loading={analytics.isLoading} />
        <StatCard label="Clicked" value={`${analytics.data?.clicked ?? 0} (${pct(analytics.data?.click_rate)})`} icon={MousePointerClick} loading={analytics.isLoading} />
        <StatCard label="Bounced" value={`${analytics.data?.bounced ?? 0} (${pct(analytics.data?.bounce_rate)})`} icon={ShieldAlert} loading={analytics.isLoading} />
        <StatCard label="Complaints" value={`${analytics.data?.complained ?? 0} (${pct(analytics.data?.complaint_rate)})`} icon={ThumbsDown} loading={analytics.isLoading} />
        <StatCard label="Unsubscribed" value={`${analytics.data?.unsubscribed ?? 0} (${pct(analytics.data?.unsubscribe_rate)})`} icon={UserMinus} loading={analytics.isLoading} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <TimeseriesChart title="Open trends" data={opens.data} loading={opens.isLoading} />
        <TimeseriesChart title="Click trends" data={clicks.data} loading={clicks.isLoading} />
      </div>
    </section>
  );
}
