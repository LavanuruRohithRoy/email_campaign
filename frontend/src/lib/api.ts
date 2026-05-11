import axios, { type AxiosError, type AxiosResponse } from "axios";

import { useAuthStore } from "@/stores/auth-store";
import type { AuthTokens } from "@/types/api";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = useAuthStore.getState().refreshToken;
  if (!refreshToken) {
    return null;
  }
  const response = await axios.post<AuthTokens>(`${baseURL}/api/v1/auth/refresh`, {
    refresh_token: refreshToken,
  });
  useAuthStore.getState().setTokens(response.data);
  return response.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config;
    if (error.response?.status !== 401 || !original || original.headers?.["x-retried"]) {
      if (error.response?.status === 401) {
        useAuthStore.getState().logout();
        window.location.assign("/login");
      }
      return Promise.reject(error);
    }

    try {
      refreshPromise = refreshPromise ?? refreshAccessToken();
      const token = await refreshPromise;
      refreshPromise = null;
      if (!token) {
        throw error;
      }
      original.headers.Authorization = `Bearer ${token}`;
      original.headers["x-retried"] = "true";
      return api(original);
    } catch (refreshError) {
      refreshPromise = null;
      useAuthStore.getState().logout();
      window.location.assign("/login");
      return Promise.reject(refreshError);
    }
  },
);

export async function unwrap<T>(promise: Promise<AxiosResponse<T>>): Promise<T> {
  const response = await promise;
  return response.data;
}
