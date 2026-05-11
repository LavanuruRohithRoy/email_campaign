import { useCallback, useEffect, useRef, useState } from "react";

import { saveTemplateDraft } from "@/features/templates/api/template-builder";
import type { EditorExportData, SavingState } from "@/features/templates/types/template-builder";

function hashSnapshot(snapshot: EditorExportData): string {
  const seed = `${snapshot.html.length}-${JSON.stringify(snapshot.design).length}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }
  return String(hash);
}

interface UseTemplateAutosaveOptions {
  getSnapshot: () => Promise<EditorExportData>;
  templateName: string;
  subject: string;
  intervalMs?: number;
}

export function useTemplateAutosave({
  getSnapshot,
  templateName,
  subject,
  intervalMs = 30000,
}: UseTemplateAutosaveOptions) {
  const [savingState, setSavingState] = useState<SavingState>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  const latestHashRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);

  const saveIfChanged = useCallback(async (): Promise<boolean> => {
    if (inFlightRef.current) {
      return false;
    }

    const snapshot = await getSnapshot();
    const nextHash = hashSnapshot(snapshot);

    if (latestHashRef.current === nextHash) {
      return false;
    }

    inFlightRef.current = true;
    setSavingState("saving");

    try {
      await saveTemplateDraft({
        name: templateName,
        subject,
        html_content: snapshot.html,
        design_json: snapshot.design,
        is_draft: true,
      });
      latestHashRef.current = nextHash;
      setSavingState("saved");
      setLastSavedAt(new Date().toISOString());
      return true;
    } catch (error) {
      setSavingState("error");
      throw error;
    } finally {
      inFlightRef.current = false;
    }
  }, [getSnapshot, templateName, subject]);

  useEffect(() => {
    const timer = setInterval(() => {
      void saveIfChanged().catch(() => {
        // status is already handled in hook state
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [intervalMs, saveIfChanged]);

  return {
    savingState,
    lastSavedAt,
    saveIfChanged,
  };
}
