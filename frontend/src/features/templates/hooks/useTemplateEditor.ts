import { useRef } from "react";

import type { EditorExportData, MergeTagKey } from "@/features/templates/types/template-builder";

interface EmailEditorRuntime {
  exportHtml: (callback: (data: EditorExportData) => void) => void;
  insertHtml?: (html: string) => void;
}

interface EmailEditorRefShape {
  editor: EmailEditorRuntime;
}

export function useTemplateEditor() {
  const editorRef = useRef<EmailEditorRefShape | null>(null);

  const exportHtml = (): Promise<EditorExportData> =>
    new Promise((resolve, reject) => {
      try {
        if (!editorRef.current?.editor) {
          reject(new Error("Editor not ready"));
          return;
        }
        editorRef.current.editor.exportHtml((data) => resolve(data));
      } catch (error) {
        reject(error);
      }
    });

  const insertMergeTag = (tag: MergeTagKey) => {
    const token = `{{${tag}}}`;
    editorRef.current?.editor.insertHtml?.(token);
  };

  return {
    editorRef,
    exportHtml,
    insertMergeTag,
  };
}
