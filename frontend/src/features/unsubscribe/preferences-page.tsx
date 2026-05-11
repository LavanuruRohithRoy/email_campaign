import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MailCheck } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { getPreferences, updatePreferences } from "@/api/unsubscribe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function PreferencesPage() {
  const [params] = useSearchParams();
  const token = params.get("t") ?? "";
  const queryClient = useQueryClient();
  const preferences = useQuery({
    queryKey: ["preferences", token],
    queryFn: () => getPreferences(token),
    enabled: token.length > 0,
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: (unsubscribed: boolean) => updatePreferences(token, unsubscribed),
    onSuccess: (data) => {
      queryClient.setQueryData(["preferences", token], data);
      toast.success("Preferences updated");
    },
    onError: () => toast.error("Could not update preferences"),
  });

  const invalid = !token || preferences.isError;
  return (
    <main className="grid min-h-screen place-items-center bg-background px-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="mb-3 grid h-11 w-11 place-items-center rounded-md bg-primary/10 text-primary">
            <MailCheck className="h-5 w-5" />
          </div>
          <CardTitle>Preference center</CardTitle>
          <CardDescription>{invalid ? "This preference link is invalid or has expired." : "Manage email subscription status."}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5">
          {preferences.isLoading ? (
            <Skeleton className="h-28 w-full" />
          ) : preferences.data ? (
            <>
              <div className="rounded-md border p-4">
                <p className="font-medium">{preferences.data.email}</p>
                <div className="mt-2"><Badge variant={preferences.data.unsubscribed ? "outline" : "default"}>{preferences.data.status}</Badge></div>
              </div>
              <Button
                variant={preferences.data.unsubscribed ? "default" : "outline"}
                disabled={mutation.isPending}
                onClick={() => mutation.mutate(!preferences.data?.unsubscribed)}
              >
                {preferences.data.unsubscribed ? "Resubscribe" : "Unsubscribe"}
              </Button>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No preferences available.</p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
