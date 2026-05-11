import { Navigate, Route, Routes } from "react-router-dom";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { LoginPage } from "@/features/auth/login-page";
import { ContactsPage } from "@/features/contacts/contacts-page";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { ListsPage } from "@/features/lists/lists-page";
import { SegmentsPage } from "@/features/segments/segments-page";
import { PreferencesPage } from "@/features/unsubscribe/preferences-page";
import { UnsubscribePage } from "@/features/unsubscribe/unsubscribe-page";
import { PlaceholderPage } from "@/pages/placeholder-page";
import { ProtectedRoute } from "@/routes/protected-route";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/unsubscribe" element={<UnsubscribePage />} />
      <Route path="/preferences" element={<PreferencesPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="contacts" element={<ContactsPage />} />
          <Route path="lists" element={<ListsPage />} />
          <Route path="segments" element={<SegmentsPage />} />
          <Route path="templates" element={<PlaceholderPage title="Templates" />} />
          <Route path="campaigns" element={<PlaceholderPage title="Campaigns" />} />
          <Route path="analytics" element={<PlaceholderPage title="Analytics" />} />
          <Route path="settings" element={<PlaceholderPage title="Settings" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
