import { Activity } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSendProgress } from "@/features/analytics/hooks/use-analytics";

export function LiveSendProgress({ campaignId }: { campaignId: string }) {
  const progress = useSendProgress(campaignId);
  const total = progress.data?.total ?? 0;
  const sent = progress.data?.sent ?? 0;
  const remaining = Math.max(total - sent, 0);
  const percent = total > 0 ? Math.round((sent / total) * 100) : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Live send progress
        </CardTitle>
        {progress.data ? <Badge variant="outline">{progress.data.status}</Badge> : null}
      </CardHeader>
      <CardContent>
        {progress.isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : (
          <div className="grid gap-3">
            <div className="h-3 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-primary transition-all" style={{ width: `${percent}%` }} />
            </div>
            <div className="flex flex-wrap justify-between gap-3 text-sm text-muted-foreground">
              <span>{sent} sent</span>
              <span>{remaining} remaining</span>
              <span>{percent}% complete</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
