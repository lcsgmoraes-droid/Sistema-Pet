import axios from "axios";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../auth/tokenStorage";
import { createRefreshManager } from "../auth/refreshManager";

const configuredApiUrl = import.meta.env.VITE_API_URL;
const baseURL = import.meta.env.DEV ? "/api" : (configuredApiUrl || "/api");
const PUBLIC_PATH_PREFIXES = [
  "/login",
  "/register",
  "/recuperar-senha",
  "/verificar-email",
  "/termos",
  "/privacidade",
  "/landing",
  "/planos",
  "/app",
  "/ecommerce",
];
const REFRESH_RETRY_EXCLUDED_ENDPOINTS = [
  "/auth/login-multitenant",
  "/auth/register",
  "/auth/select-tenant",
  "/auth/refresh",
  "/auth/logout-multitenant",
];

function isPublicBrowserPath() {
  const path = window.location.pathname || "/";
  return PUBLIC_PATH_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );
}

function isRefreshRetryEligible(config) {
  const url = config?.url || "";
  return !REFRESH_RETRY_EXCLUDED_ENDPOINTS.some((endpoint) => url.includes(endpoint));
}

function handleAuthExpired() {
  const isPublicPath = isPublicBrowserPath();
  if (!isPublicPath) {
    console.warn("Sessao invalida ou tenant nao selecionado");
  }

  clearAuthTokens();
  localStorage.removeItem("tenants");
  localStorage.removeItem("selectedTenant");

  if (!isPublicPath) {
    window.location.href = "/login";
  }
}

export const api = axios.create({
  baseURL,
});

const refreshManager = createRefreshManager({
  refreshRequest: (refreshToken) => axios.post(
    `${baseURL}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { "Content-Type": "application/json" } },
  ),
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  clearAuthTokens,
});

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();

    if (!config.headers.Authorization && token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const originalRequest = error.config || {};

    if (status === 401) {
      if (!originalRequest._retry && isRefreshRetryEligible(originalRequest) && getRefreshToken()) {
        originalRequest._retry = true;
        try {
          const accessToken = await refreshManager.refreshAccessToken();
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          handleAuthExpired();
          return Promise.reject(refreshError);
        }
      }

      handleAuthExpired();
    }

    if (status === 403) {
      console.warn("Acesso negado para este tenant");
    }

    return Promise.reject(error);
  }
);

export default api;
