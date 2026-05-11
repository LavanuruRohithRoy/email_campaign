import { format } from "date-fns";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnalyticsTimeSeriesPoint } from "@/features/analytics/types/analytics";

interface TimeseriesChartProps {
  title: string;
  data: AnalyticsTimeSeriesPoint[] | undefined;
  loading?: boolean;
}

export function TimeseriesChart({ title, data, loading = false }: TimeseriesChartProps) {
  const rows = (data ?? []).map((point) => ({
    date: format(new Date(point.timestamp), "MMM d"),
    value: point.value,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : rows.length ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={rows} margin={{ left: -20, right: 8, top: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="hsl(var(--primary))" fill="hsl(var(--primary) / 0.18)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="grid h-64 place-items-center text-sm text-muted-foreground">No trend data yet.</div>
        )}
      </CardContent>
    </Card>
  );
}
