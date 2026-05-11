import { api, unwrap } from "@/lib/api";
import type { PreferenceCenter } from "@/types/api";

export interface UnsubscribeResponse {
  status: string;
  message: string;
}

export function unsubscribe(token: string) {
  return unwrap(api.get<UnsubscribeResponse>("/unsubscribe", { params: { t: token } }));
}

export function getPreferences(token: string) {
  return unwrap(api.get<PreferenceCenter>("/preferences", { params: { t: token } }));
}

export function updatePreferences(token: string, unsubscribed: boolean) {
  return unwrap(api.post<PreferenceCenter>("/preferences", { unsubscribed }, { params: { t: token } }));
}
