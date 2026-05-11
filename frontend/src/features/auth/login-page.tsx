import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Mail, ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { getMe, login } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth-store";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setTokens = useAuthStore((state) => state.setTokens);
  const setUser = useAuthStore((state) => state.setUser);
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const mutation = useMutation({
    mutationFn: async (values: LoginForm) => {
      const tokens = await login(values.email, values.password);
      setTokens(tokens);
      const user = await getMe();
      setUser(user);
      return user;
    },
    onSuccess: (user) => {
      queryClient.setQueryData(["session"], user);
      toast.success("Signed in");
      navigate("/");
    },
    onError: () => toast.error("Invalid email or password"),
  });

  return (
    <main className="grid min-h-screen place-items-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="mb-3 grid h-11 w-11 place-items-center rounded-md bg-primary text-primary-foreground">
            <Mail className="h-5 w-5" />
          </div>
          <CardTitle>Email Campaign</CardTitle>
          <CardDescription>Sign in to manage campaigns, contacts, and analytics.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
            <label className="grid gap-2 text-sm font-medium">
              Email
              <Input type="email" autoComplete="email" {...form.register("email")} />
            </label>
            <label className="grid gap-2 text-sm font-medium">
              Password
              <Input type="password" autoComplete="current-password" {...form.register("password")} />
            </label>
            <Button type="submit" disabled={mutation.isPending}>
              <ShieldCheck className="h-4 w-4" />
              {mutation.isPending ? "Signing in" : "Login"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
