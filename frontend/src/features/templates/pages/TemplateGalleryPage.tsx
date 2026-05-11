import { useEffect, useState } from "react";

import { api, unwrap } from "@/lib/api";
import type { TemplateSummary } from "@/features/templates/types/template-builder";
import type { Paginated } from "@/types/api";

export default function TemplateGalleryPage() {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const data = await unwrap(api.get<Paginated<TemplateSummary>>("/api/v1/templates?limit=20&offset=0"));
        setTemplates(data.items || []);
      } catch {
        setTemplates([]);
      }
    };

    void loadTemplates();
  }, []);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl">Templates</h1>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {templates.map((template) => (
          <div key={template.id} className="card p-4">
            <h3 className="font-semibold">{template.name}</h3>
            <p className="text-sm text-muted">{template.category || "General"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
