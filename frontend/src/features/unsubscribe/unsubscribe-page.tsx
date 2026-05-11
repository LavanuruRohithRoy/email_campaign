import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, MailX } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { unsubscribe } from "@/api/unsubscribe";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function UnsubscribePage() {
  const [params] = useSearchParams();
  const token = params.get("t") ?? "";
  const result = useQuery({
    queryKey: ["unsubscribe", token],
    queryFn: () => unsubscribe(token),
    enabled: token.length > 0,
    retry: false,
  });

  return (
    <main className="grid min-h-screen place-items-center bg-background px-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="mb-3 grid h-11 w-11 place-items-center rounded-md bg-primary/10 text-primary">
            {result.isError || !token ? <MailX className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}
          </div>
          <CardTitle>{result.isError || !token ? "Unsubscribe link unavailable" : "Unsubscribe"}</CardTitle>
          <CardDescription>
            {result.isLoading ? "Processing your request." : result.data?.message ?? "This link is invalid or has expired."}
          </CardDescription>
        </CardHeader>
        <CardContent>{result.isLoading ? <Skeleton className="h-10 w-full" /> : <p className="text-sm text-muted-foreground">You can close this page safely.</p>}</CardContent>
      </Card>
    </main>
  );
}
