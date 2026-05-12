import { useMemo, useState } from "react";
import type { RefObject } from "react";
import EmailEditor from "react-email-editor";
import type { EditorRef } from "react-email-editor";
import { toast } from "sonner";

import { previewTemplate, sendTemplateTestEmail } from "@/features/templates/api/template-builder";
import { useTemplateAutosave } from "@/features/templates/hooks/useTemplateAutosave";
import { useTemplateEditor } from "@/features/templates/hooks/useTemplateEditor";
import type { MergeTagKey } from "@/features/templates/types/template-builder";

const mergeTags: MergeTagKey[] = ["first_name", "last_name", "email", "company", "unsubscribe_url"];

export default function TemplateEditorPage() {
  const { editorRef, exportHtml, insertMergeTag } = useTemplateEditor();

  const [templateName] = useState("M10 Template Draft");
  const [subject] = useState("M10 Subject Draft");
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [showTestModal, setShowTestModal] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [sampleData, setSampleData] = useState({
    first_name: "Test",
    last_name: "User",
    email: "test@example.com",
    company: "ACME",
    unsubscribe_url: "",
  });

  const { savingState, lastSavedAt, saveIfChanged } = useTemplateAutosave({
    getSnapshot: exportHtml,
    templateName,
    subject,
    intervalMs: 30000,
  });

  const hasUnsubscribeLink = useMemo(() => {
    if (!previewHtml) return false;
    const lower = previewHtml.toLowerCase();
    return lower.includes("{{unsubscribe_url}}") || lower.includes("/unsubscribe") || lower.includes("unsubscribe");
  }, [previewHtml]);

  const handleManualSave = async () => {
    try {
      const saved = await saveIfChanged();
      if (saved) {
        toast.success("Draft saved");
      } else {
        toast.info("No changes to save");
      }
    } catch {
      toast.error("Failed to save draft");
    }
  };

  const handleRefreshPreview = async () => {
    try {
      const snapshot = await exportHtml();
      const response = await previewTemplate({
        html_content: snapshot.html,
        sample_data: sampleData,
      });
      setPreviewHtml(response.html);
      toast.success("Preview updated");
    } catch {
      toast.error("Failed to render preview");
    }
  };

  const handleOpenTestModal = async () => {
    await handleRefreshPreview();
    setShowTestModal(true);
  };

  const handleSendTestEmail = async () => {
    try {
      setTestLoading(true);
      const snapshot = await exportHtml();
      await sendTemplateTestEmail({
        to_email: testEmail,
        subject,
        html_content: snapshot.html,
      });
      toast.success("Test email sent");
      setShowTestModal(false);
      setTestEmail("");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to send test email";
      toast.error(message);
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center gap-4">
        <button onClick={handleManualSave} className="btn">Save</button>
        <button onClick={handleRefreshPreview} className="btn-ghost">Preview</button>
        <button onClick={handleOpenTestModal} className="btn">Send Test</button>
        <div className="ml-auto text-sm">
          {savingState === "saving" && <span>Saving...</span>}
          {savingState === "saved" && (
            <span>
              Saved
              {lastSavedAt ? ` at ${new Date(lastSavedAt).toLocaleTimeString()}` : ""}
            </span>
          )}
          {savingState === "error" && <span className="text-red-600">Save error</span>}
        </div>
      </div>

      <div className="flex gap-6">
        <div style={{ flex: 1 }}>
          <div className="mb-3">
            <label className="block text-sm font-medium">Insert Merge Tag</label>
            <div className="mt-2 flex items-center gap-2">
              {mergeTags.map((tag) => (
                <button key={tag} onClick={() => insertMergeTag(tag)} className="rounded border px-2 py-1 text-sm">
                  {"{{"}
                  {tag}
                  {"}}"}
                </button>
              ))}
            </div>
          </div>

          <div style={{ height: 700 }}>
            <EmailEditor ref={editorRef as unknown as RefObject<EditorRef<"email">>} />
          </div>
        </div>

        <div style={{ width: 420 }}>
          <div className="mb-4">
            <h3 className="font-semibold">Live Preview</h3>
            <div className="mt-2 space-y-1">
              <label className="text-xs">Sample First Name</label>
              <input
                className="input"
                value={sampleData.first_name}
                onChange={(event) => setSampleData({ ...sampleData, first_name: event.target.value })}
              />
              <label className="text-xs">Sample Email</label>
              <input
                className="input"
                value={sampleData.email}
                onChange={(event) => setSampleData({ ...sampleData, email: event.target.value })}
              />
              <label className="text-xs">Sample Unsubscribe URL</label>
              <input
                className="input"
                value={sampleData.unsubscribe_url}
                onChange={(event) => setSampleData({ ...sampleData, unsubscribe_url: event.target.value })}
                placeholder="https://example.com/unsubscribe?t=token"
              />
              <div className="mt-2">
                <button onClick={handleRefreshPreview} className="btn-ghost">Refresh Preview</button>
              </div>
            </div>
          </div>
          <div className="mb-2 text-xs">
            {hasUnsubscribeLink ? (
              <span className="text-emerald-600">Unsubscribe link detected in rendered HTML</span>
            ) : (
              <span className="text-amber-600">No unsubscribe link detected in rendered HTML</span>
            )}
          </div>
          <div className="rounded border p-2" style={{ height: 520, overflow: "auto" }}>
            {previewHtml ? <div dangerouslySetInnerHTML={{ __html: previewHtml }} /> : <div className="text-sm text-muted">No preview yet</div>}
          </div>
        </div>
      </div>

      {showTestModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/40">
          <div className="w-96 rounded bg-white p-6">
            <h3 className="mb-2 text-lg font-semibold">Send Test Email</h3>
            <label className="text-sm">Recipient</label>
            <input
              className="input mb-2"
              value={testEmail}
              onChange={(event) => setTestEmail(event.target.value)}
              placeholder="recipient@example.com"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowTestModal(false)} className="btn-ghost">Cancel</button>
              <button onClick={handleSendTestEmail} className="btn" disabled={testLoading || !testEmail}>
                {testLoading ? "Sending..." : "Send"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
