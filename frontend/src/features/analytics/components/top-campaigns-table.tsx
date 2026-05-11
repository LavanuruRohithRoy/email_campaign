import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CampaignPerformanceItem } from "@/features/analytics/types/analytics";

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function TopCampaignsTable({
  items,
  loading = false,
}: {
  items: CampaignPerformanceItem[] | undefined;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Top campaigns</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="grid gap-2 p-5">{Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-12 w-full" />)}</div>
        ) : items?.length ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Campaign</TableHead>
                <TableHead>Sent</TableHead>
                <TableHead>Open rate</TableHead>
                <TableHead>Click rate</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((campaign) => (
                <TableRow key={campaign.campaign_id}>
                  <TableCell className="font-medium">{campaign.campaign_name}</TableCell>
                  <TableCell>{campaign.sent}</TableCell>
                  <TableCell>{pct(campaign.open_rate)}</TableCell>
                  <TableCell>{pct(campaign.click_rate)}</TableCell>
                  <TableCell className="text-right">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/campaigns/${campaign.campaign_id}/report`}>Report</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="p-8 text-center text-sm text-muted-foreground">No sent campaigns yet.</div>
        )}
      </CardContent>
    </Card>
  );
}
