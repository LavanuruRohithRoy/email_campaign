import { api, unwrap } from "@/lib/api";
import type { Contact, ContactList, ContactStatus, Paginated, Segment } from "@/types/api";

export interface ContactQuery {
  search?: string;
  status?: ContactStatus | "all";
  limit: number;
  offset: number;
}

export function getContacts(query: ContactQuery) {
  const params = {
    search: query.search || undefined,
    status: query.status === "all" ? undefined : query.status,
    limit: query.limit,
    offset: query.offset,
  };
  return unwrap(api.get<Paginated<Contact>>("/api/v1/contacts", { params }));
}

export function getLists(limit = 50, offset = 0) {
  return unwrap(api.get<Paginated<ContactList>>("/api/v1/lists", { params: { limit, offset } }));
}

export function getSegments(limit = 50, offset = 0) {
  return unwrap(api.get<Paginated<Segment>>("/api/v1/segments", { params: { limit, offset } }));
}
