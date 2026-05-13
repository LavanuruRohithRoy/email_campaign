import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useSession } from "@/features/auth/use-session";
import { useAuthStore } from "@/stores/auth-store";
import type { UserRole } from "@/types/api";

interface ProtectedRouteProps {
  roles?: UserRole[];
}

export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const location = useLocation();
  const token = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const session = useSession();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (session.isLoading && !user) {
    return <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">Loading session...</div>;
  }

  if (!user && session.isError) {
    logout();
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const activeUser = user ?? session.data;
  if (roles && (!activeUser || !roles.includes(activeUser.role))) {
    return <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">403: Access denied</div>;
  }

  return <Outlet />;
}
