import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  createCampaign,
  getRecipientCount,
  scheduleCampaign,
  sendCampaign,
  updateCampaignRecipients,
  type CampaignCreatePayload,
} from "@/features/campaigns/api/campaigns";
import { getTemplateById } from "@/features/templates/api/template-builder";

type StepKey = "details" | "audience" | "template" | "editing" | "schedule" | "review";
type ScheduleMode = "now" | "scheduled";

interface ComposerDraft {
  name: string;
  subject: string;
  from_name: string;
  from_email: string;
  target_list_ids: string[];
  target_segment_ids: string[];
  exclude_list_ids: string[];
  template_id: string;
  schedule_mode: ScheduleMode;
  scheduled_at: string;
  timezone: string;
}

const steps: StepKey[] = ["details", "audience", "template", "editing", "schedule", "review"];

export default function CampaignComposerPage() {
  const [stepIndex, setStepIndex] = useState(0);
  const [campaignId, setCampaignId] = useState("");
  const [draft, setDraft] = useState<ComposerDraft>({
    name: "",
    subject: "",
    from_name: "",
    from_email: "",
    target_list_ids: [],
    target_segment_ids: [],
    exclude_list_ids: [],
    template_id: "",
    schedule_mode: "now",
    scheduled_at: "",
    timezone: "UTC",
  });
  const [estimatedRecipients, setEstimatedRecipients] = useState<number | null>(null);
  const [checkingRecipients, setCheckingRecipients] = useState(false);
  const [templateHasUnsubscribe, setTemplateHasUnsubscribe] = useState(false);

  const currentStep = steps[stepIndex];
  const canBack = stepIndex > 0;

  const scheduleValidationError = useMemo(() => {
    if (draft.schedule_mode !== "scheduled") return "";
    if (!draft.scheduled_at) return "Scheduled datetime is required";
    if (!draft.timezone.trim()) return "Timezone is required for scheduled mode";
    const selected = new Date(draft.scheduled_at);
    if (Number.isNaN(selected.valueOf())) return "Scheduled datetime is invalid";
    if (selected <= new Date()) return "Scheduled datetime must be in the future";
    return "";
  }, [draft.schedule_mode, draft.scheduled_at, draft.timezone]);

  const warnings = useMemo(() => {
    const items: string[] = [];
    if (!draft.subject.trim()) items.push("Subject is empty");
    if (!templateHasUnsubscribe) items.push("Template is missing an unsubscribe link token");
    if ((estimatedRecipients ?? 0) <= 0) items.push("No recipients selected");
    if (scheduleValidationError) items.push(scheduleValidationError);
    return items;
  }, [draft.subject, templateHasUnsubscribe, estimatedRecipients, scheduleValidationError]);

  useEffect(() => {
    const inspectTemplate = async () => {
      if (!draft.template_id.trim()) {
        setTemplateHasUnsubscribe(false);
        return;
      }
      try {
        const template = await getTemplateById(draft.template_id);
        const html = template.html.toLowerCase();
        const hasLink = html.includes("{{unsubscribe_url}}") || html.includes("/unsubscribe") || html.includes("unsubscribe");
        setTemplateHasUnsubscribe(hasLink);
      } catch {
        setTemplateHasUnsubscribe(false);
      }
    };

    void inspectTemplate();
  }, [draft.template_id]);

  const ensureCampaignDraft = async (): Promise<string> => {
    if (campaignId) return campaignId;

    const payload: CampaignCreatePayload = {
      name: draft.name,
      subject: draft.subject,
      from_name: draft.from_name,
      from_email: draft.from_email,
      preview_text: null,
      reply_to: null,
      target_list_ids: draft.target_list_ids,
      target_segment_ids: draft.target_segment_ids,
      exclude_list_ids: draft.exclude_list_ids,
      template_id: draft.template_id || null,
    };

    const created = await createCampaign(payload);
    setCampaignId(created.id);
    return created.id;
  };

  const estimateAudience = async () => {
    setCheckingRecipients(true);
    try {
      const id = await ensureCampaignDraft();
      await updateCampaignRecipients(id, {
        target_list_ids: draft.target_list_ids,
        target_segment_ids: draft.target_segment_ids,
        exclude_list_ids: draft.exclude_list_ids,
      });
      const count = await getRecipientCount(id);
      setEstimatedRecipients(count.estimated_count);
      toast.success("Audience estimate updated");
    } catch {
      toast.error("Failed to estimate audience");
    } finally {
      setCheckingRecipients(false);
    }
  };

  const moveNext = () => {
    if (currentStep === "schedule" && scheduleValidationError) {
      toast.error(scheduleValidationError);
      return;
    }
    setStepIndex((value) => Math.min(value + 1, steps.length - 1));
  };

  const moveBack = () => {
    setStepIndex((value) => Math.max(value - 1, 0));
  };

  const confirmAndSend = async () => {
    try {
      const id = await ensureCampaignDraft();

      if (draft.schedule_mode === "scheduled") {
        if (scheduleValidationError) {
          toast.error(scheduleValidationError);
          return;
        }
        await scheduleCampaign(id, {
          scheduled_at: new Date(draft.scheduled_at).toISOString(),
          timezone: draft.timezone,
        });
        toast.success("Campaign scheduled");
        return;
      }

      await sendCampaign(id);
      toast.success("Campaign send started");
    } catch {
      toast.error("Failed to finalize campaign");
    }
  };

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center gap-2 text-sm">
        {steps.map((step, index) => (
          <span key={step} className={index === stepIndex ? "font-semibold" : "text-muted-foreground"}>
            {index + 1}. {step}
          </span>
        ))}
      </div>

      {currentStep === "details" && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Campaign Details</h2>
          <input className="input" placeholder="Campaign name" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
          <input className="input" placeholder="Subject" value={draft.subject} onChange={(event) => setDraft({ ...draft, subject: event.target.value })} />
          <input className="input" placeholder="From name" value={draft.from_name} onChange={(event) => setDraft({ ...draft, from_name: event.target.value })} />
          <input className="input" placeholder="From email" value={draft.from_email} onChange={(event) => setDraft({ ...draft, from_email: event.target.value })} />
        </div>
      )}

      {currentStep === "audience" && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Audience Selection</h2>
          <p className="text-sm text-muted-foreground">Use comma-separated IDs for lists and segments.</p>
          <input
            className="input"
            placeholder="Target list IDs (comma-separated)"
            value={draft.target_list_ids.join(",")}
            onChange={(event) => setDraft({ ...draft, target_list_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })}
          />
          <input
            className="input"
            placeholder="Target segment IDs (comma-separated)"
            value={draft.target_segment_ids.join(",")}
            onChange={(event) => setDraft({ ...draft, target_segment_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })}
          />
          <input
            className="input"
            placeholder="Exclude list IDs (comma-separated)"
            value={draft.exclude_list_ids.join(",")}
            onChange={(event) => setDraft({ ...draft, exclude_list_ids: event.target.value.split(",").map((v) => v.trim()).filter(Boolean) })}
          />
          <button className="btn" onClick={estimateAudience} disabled={checkingRecipients}>
            {checkingRecipients ? "Estimating..." : "Estimate Audience"}
          </button>
          <div className="text-sm">Estimated recipients: {estimatedRecipients ?? "-"}</div>
        </div>
      )}

      {currentStep === "template" && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Template Selection</h2>
          <input className="input" placeholder="Template ID" value={draft.template_id} onChange={(event) => setDraft({ ...draft, template_id: event.target.value })} />
          <div className="text-xs">
            {templateHasUnsubscribe ? (
              <span className="text-emerald-600">Unsubscribe token detected in template HTML</span>
            ) : (
              <span className="text-amber-600">Unsubscribe token not detected</span>
            )}
          </div>
        </div>
      )}

      {currentStep === "editing" && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Template Editing</h2>
          <p className="text-sm text-muted-foreground">Continue editing in Templates editor.</p>
        </div>
      )}

      {currentStep === "schedule" && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Scheduling</h2>
          <select
            className="input"
            value={draft.schedule_mode}
            onChange={(event) => setDraft({ ...draft, schedule_mode: event.target.value as ScheduleMode })}
          >
            <option value="now">Send now</option>
            <option value="scheduled">Schedule</option>
          </select>
          {draft.schedule_mode === "scheduled" && (
            <>
              <input className="input" type="datetime-local" value={draft.scheduled_at} onChange={(event) => setDraft({ ...draft, scheduled_at: event.target.value })} />
              <input className="input" placeholder="Timezone (e.g. UTC, Asia/Kolkata)" value={draft.timezone} onChange={(event) => setDraft({ ...draft, timezone: event.target.value })} />
            </>
          )}
          {scheduleValidationError ? <p className="text-sm text-red-600">{scheduleValidationError}</p> : null}
        </div>
      )}

      {currentStep === "review" && (
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Review & Send</h2>
          <div className="text-sm">Subject: {draft.subject || "(empty)"}</div>
          <div className="text-sm">Audience estimate: {estimatedRecipients ?? "-"}</div>
          {warnings.length > 0 ? (
            <ul className="ml-5 list-disc text-sm text-amber-700">
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
          <button className="btn" onClick={confirmAndSend}>Confirm and continue</button>
        </div>
      )}

      <div className="flex justify-between border-t pt-4">
        <button className="btn-ghost" onClick={moveBack} disabled={!canBack}>Back</button>
        <button className="btn" onClick={moveNext} disabled={stepIndex >= steps.length - 1}>Next</button>
      </div>
    </div>
  );
}
