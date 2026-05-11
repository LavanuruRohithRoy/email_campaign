import { api, unwrap } from "@/lib/api";
import type { AuthTokens, User } from "@/types/api";

export function login(email: string, password: string) {
  return unwrap(api.post<AuthTokens>("/api/v1/auth/login", { email, password }));
}

export function getMe() {
  return unwrap(api.get<User>("/api/v1/auth/me"));
}

export function logout(refreshToken: string) {
  return api.post<void>("/api/v1/auth/logout", { refresh_token: refreshToken });
}
