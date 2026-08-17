import axios from "axios";

import {
  clearPlatformAuthTokens,
  getPlatformAccessToken,
  getPlatformRefreshToken,
  setPlatformAccessToken,
  setPlatformRefreshToken,
} from "./auth/platformTokenStorage";
import { createRefreshManager } from "./auth/refreshManager";

const API_URL = import.meta.env.DEV ? "/api" : import.meta.env.VITE_API_URL || "/api";
const NO_RETRY = [
  "/platform-auth/login",
  "/platform-auth/refresh",
  "/platform-auth/logout",
  "/platform-auth/forgot-password",
  "/platform-auth/reset-password",
];

const platformApi = axios.create({
  baseURL: API_URL,
  timeout: 20000,
  headers: { "Content-Type": "application/json" },
});

const refreshManager = createRefreshManager({
  refreshRequest: (refreshToken) =>
    axios.post(`${API_URL}/platform-auth/refresh`, { refresh_token: refreshToken }),
  getRefreshToken: getPlatformRefreshToken,
  setAccessToken: setPlatformAccessToken,
  setRefreshToken: setPlatformRefreshToken,
  clearAuthTokens: clearPlatformAuthTokens,
});

function platformSessionExpired() {
  clearPlatformAuthTokens();
  localStorage.removeItem("platform_admin");
  const path = globalThis.location?.pathname || "";
  if (!path.startsWith("/ops/login") && !path.startsWith("/ops/recuperar-senha")) {
    globalThis.location.href = "/ops/login";
  }
}

platformApi.interceptors.request.use((config) => {
  const token = getPlatformAccessToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

platformApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const retryAllowed = !NO_RETRY.some((path) => String(originalRequest.url || "").includes(path));

    if (
      error.response?.status === 401 &&
      !originalRequest._platformRetry &&
      retryAllowed &&
      getPlatformRefreshToken()
    ) {
      originalRequest._platformRetry = true;
      try {
        const accessToken = await refreshManager.refreshAccessToken();
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return platformApi(originalRequest);
      } catch (refreshError) {
        platformSessionExpired();
        return Promise.reject(refreshError);
      }
    }

    if (error.response?.status === 401 && retryAllowed) {
      platformSessionExpired();
    }
    return Promise.reject(error);
  },
);

export default platformApi;
