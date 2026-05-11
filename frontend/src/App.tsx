import { Navigate, Route, Routes } from "react-router-dom";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { AnalyticsPage } from "@/features/analytics/pages/AnalyticsPage";
import { CampaignReportPage } from "@/features/analytics/pages/CampaignReportPage";
import { LoginPage } from "@/features/auth/login-page";
import { ContactsPage } from "@/features/contacts/contacts-page";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { ListsPage } from "@/features/lists/lists-page";
import { SegmentsPage } from "@/features/segments/segments-page";
import { PreferencesPage } from "@/features/unsubscribe/preferences-page";
import { UnsubscribePage } from "@/features/unsubscribe/unsubscribe-page";
import { PlaceholderPage } from "@/pages/placeholder-page";
import TemplateGalleryPage from "@/features/templates/pages/TemplateGalleryPage";
import TemplateEditorPage from "@/features/templates/pages/TemplateEditorPage";
import CampaignComposerPage from "@/features/campaigns/pages/CampaignComposerPage";
import { ProtectedRoute } from "@/routes/protected-route";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/unsubscribe" element={<UnsubscribePage />} />
      <Route path="/preferences" element={<PreferencesPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route element={<ProtectedRoute roles={["super_admin", "campaign_manager"]} />}>
            <Route path="contacts" element={<ContactsPage />} />
            <Route path="lists" element={<ListsPage />} />
            <Route path="segments" element={<SegmentsPage />} />
            <Route path="templates" element={<TemplateGalleryPage />} />
            <Route path="templates/new" element={<TemplateEditorPage />} />
          </Route>
          <Route path="campaigns" element={<PlaceholderPage title="Campaigns" />} />
          <Route path="campaigns/new" element={<CampaignComposerPage />} />
          <Route path="campaigns/:id/edit" element={<CampaignComposerPage />} />
          <Route path="campaigns/:id/report" element={<CampaignReportPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route element={<ProtectedRoute roles={["super_admin"]} />}>
            <Route path="settings" element={<PlaceholderPage title="Settings" />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
