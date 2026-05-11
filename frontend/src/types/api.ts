export type UserRole = "super_admin" | "campaign_manager" | "viewer";
export type ContactStatus = "active" | "unsubscribed" | "bounced" | "complained";

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface Contact {
  id: string;
  org_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  status: ContactStatus;
  custom_fields: Record<string, string>;
  source: string;
  created_at: string;
  list_memberships: string[];
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ContactList {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  tags: string[];
  contact_count: number;
  created_at: string;
}

export interface Segment {
  id: string;
  org_id: string;
  name: string;
  rules: Record<string, unknown>;
  created_at: string;
}

export interface PreferenceCenter {
  contact_id: string;
  email: string;
  status: ContactStatus;
  unsubscribed: boolean;
  updated_at: string | null;
}
