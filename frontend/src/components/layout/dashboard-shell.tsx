import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BarChart3,
  ContactRound,
  LayoutDashboard,
  List,
  LogOut,
  MailPlus,
  Menu,
  Settings,
  Tags,
  UserRound,
} from "lucide-react";

import { logout as logoutApi } from "@/api/auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useAuthStore } from "@/stores/auth-store";
import { useUiStore } from "@/stores/ui-store";
import type { UserRole } from "@/types/api";

const navItems: Array<{ href: string; label: string; icon: typeof LayoutDashboard; roles: UserRole[] }> = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["super_admin", "campaign_manager"] },
  { href: "/contacts", label: "Contacts", icon: ContactRound, roles: ["super_admin", "campaign_manager"] },
  { href: "/lists", label: "Lists", icon: List, roles: ["super_admin", "campaign_manager"] },
  { href: "/segments", label: "Segments", icon: Tags, roles: ["super_admin", "campaign_manager"] },
  { href: "/templates", label: "Templates", icon: MailPlus, roles: ["super_admin", "campaign_manager"] },
  { href: "/campaigns", label: "Campaigns", icon: MailPlus, roles: ["super_admin", "campaign_manager", "viewer"] },
  { href: "/analytics", label: "Analytics", icon: BarChart3, roles: ["super_admin", "campaign_manager", "viewer"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ["super_admin"] },
];

function Sidebar() {
  const user = useAuthStore((state) => state.user);
  const role = user?.role ?? "viewer";
  return (
    <aside className="flex h-full flex-col gap-5">
      <Link to="/" className="flex items-center gap-2 px-2 text-base font-semibold">
        <span className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground">EC</span>
        Email Campaign
      </Link>
      <nav className="grid gap-1">
        {navItems
          .filter((item) => item.roles.includes(role))
          .map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
      </nav>
      {role === "viewer" ? <div className="mt-auto rounded-md border p-3 text-xs text-muted-foreground">Viewer mode is read-only.</div> : null}
    </aside>
  );
}

export function DashboardShell() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const logout = useAuthStore((state) => state.logout);
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);

  const handleLogout = async () => {
    if (refreshToken) {
      await logoutApi(refreshToken).catch(() => undefined);
    }
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="fixed inset-y-0 left-0 hidden w-64 border-r bg-card p-4 lg:block">
        <Sidebar />
      </div>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 px-4 backdrop-blur sm:px-6">
          <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
            <SheetTrigger asChild>
              <Button className="lg:hidden" variant="ghost" size="icon" aria-label="Open navigation">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <Sidebar />
            </SheetContent>
          </Sheet>
          <div>
            <p className="text-sm text-muted-foreground">Workspace</p>
            <h1 className="text-lg font-semibold">Campaign operations</h1>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-3 px-2">
                <Avatar>
                  <AvatarFallback>{user?.email.slice(0, 2).toUpperCase() ?? "U"}</AvatarFallback>
                </Avatar>
                <span className="hidden text-left text-sm sm:block">{user?.email}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <UserRound className="h-4 w-4" />
                {user?.role.replace("_", " ")}
              </DropdownMenuItem>
              <Separator />
              <DropdownMenuItem onSelect={handleLogout}>
                <LogOut className="h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
