import { useQuery } from "@tanstack/react-query";
import { BarChart3, ContactRound, List, Tags } from "lucide-react";

import { getContacts, getLists, getSegments } from "@/api/contacts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardPage() {
  const contacts = useQuery({ queryKey: ["contacts", "dashboard"], queryFn: () => getContacts({ limit: 1, offset: 0, status: "all" }) });
  const lists = useQuery({ queryKey: ["lists", "dashboard"], queryFn: () => getLists(1, 0) });
  const segments = useQuery({ queryKey: ["segments", "dashboard"], queryFn: () => getSegments(1, 0) });
  const metrics = [
    { label: "Contacts", value: contacts.data?.total, icon: ContactRound },
    { label: "Lists", value: lists.data?.total, icon: List },
    { label: "Segments", value: segments.data?.total, icon: Tags },
    { label: "Analytics", value: "M9", icon: BarChart3 },
  ];
  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-normal">Dashboard</h2>
        <p className="text-sm text-muted-foreground">Live operational overview from the backend.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">{metric.label}</CardTitle>
                <Icon className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                {metric.value === undefined ? <Skeleton className="h-8 w-20" /> : <p className="text-3xl font-semibold">{metric.value}</p>}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
