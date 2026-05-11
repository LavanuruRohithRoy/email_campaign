import { create } from "zustand";

import type { AuthTokens, User } from "@/types/api";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setTokens: (tokens: AuthTokens) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
}

const accessKey = "email_campaign_access";
const refreshKey = "email_campaign_refresh";

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem(accessKey),
  refreshToken: localStorage.getItem(refreshKey),
  user: null,
  setTokens: (tokens) => {
    localStorage.setItem(accessKey, tokens.access_token);
    localStorage.setItem(refreshKey, tokens.refresh_token);
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem(accessKey);
    localStorage.removeItem(refreshKey);
    set({ accessToken: null, refreshToken: null, user: null });
  },
}));
