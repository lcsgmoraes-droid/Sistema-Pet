import axios from "axios";
import * as SecureStore from "expo-secure-store";
import { API_BASE_URL } from "../config";
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  storeAuthTokens,
} from "./authTokenStorage";
import { markSessionActive, notifySessionExpired } from "./sessionExpiration";

const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
  "ngrok-skip-browser-warning": "true",
  "X-Client-Channel": "app",
  "X-Canal-Venda": "app",
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: DEFAULT_HEADERS,
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: DEFAULT_HEADERS,
});

let refreshPromise: Promise<string> | null = null;

const PUBLIC_AUTH_PATHS = [
  "/ecommerce/auth/login",
  "/ecommerce/auth/registrar",
  "/ecommerce/auth/esqueci-senha",
  "/ecommerce/auth/resetar-senha",
  "/ecommerce/auth/refresh",
];

function removeJsonContentTypeForFormData(config: any) {
  if (
    typeof FormData === "undefined" ||
    !(config.data instanceof FormData) ||
    !config.headers
  ) {
    return;
  }

  const deleteHeader = (name: string) => {
    if (typeof config.headers.delete === "function") {
      config.headers.delete(name);
      return;
    }

    delete config.headers[name];
  };

  deleteHeader("Content-Type");
  deleteHeader("content-type");
}

function requestUsedAuthentication(headers: any): boolean {
  if (!headers) return false;
  if (typeof headers.get === "function") {
    return Boolean(headers.get("Authorization"));
  }
  return Boolean(headers.Authorization || headers.authorization);
}

function isPublicAuthRequest(url?: string): boolean {
  return PUBLIC_AUTH_PATHS.some((path) => url?.includes(path));
}

function setAuthorizationHeader(config: any, token: string): void {
  if (!config.headers) config.headers = {};
  if (typeof config.headers.set === "function") {
    config.headers.set("Authorization", `Bearer ${token}`);
    return;
  }
  config.headers.Authorization = `Bearer ${token}`;
}

function refreshWasRejected(error: unknown): boolean {
  const status = (error as { response?: { status?: number } })?.response
    ?.status;
  return status === 400 || status === 401 || status === 403 || status === 422;
}

async function expireStoredSession(): Promise<void> {
  await clearAuthSession();
  await notifySessionExpired();
}

export async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;

  const operation = (async () => {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) {
      throw new Error("Refresh token ausente");
    }

    const { data } = await refreshClient.post<{
      access_token?: string | null;
      refresh_token?: string | null;
      token_type?: string;
    }>("/ecommerce/auth/refresh", { refresh_token: refreshToken });

    const accessToken = data.access_token?.trim();
    if (!accessToken || !data.refresh_token) {
      throw new Error("Resposta de renovacao de sessao invalida");
    }

    await storeAuthTokens({
      access_token: accessToken,
      refresh_token: data.refresh_token,
      token_type: data.token_type || "bearer",
    });
    markSessionActive();
    return accessToken;
  })();

  refreshPromise = operation;
  try {
    return await operation;
  } finally {
    if (refreshPromise === operation) refreshPromise = null;
  }
}

export function isUnauthorizedError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    (error as { response?: { status?: number } }).response?.status === 401
  );
}

// ─── Interceptor de Request ─────────────────────────────────────────────────
// Injeta token JWT + X-Tenant-ID dinamicamente em cada chamada
api.interceptors.request.use(
  async (config) => {
    removeJsonContentTypeForFormData(config);

    try {
      // Token de autenticação
      const token = await getAccessToken();
      if (token && !isPublicAuthRequest(config.url)) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Tenant vinculado (persiste em SecureStore)
      const tenantRaw = await SecureStore.getItemAsync("tenant_info");
      if (tenantRaw) {
        const tenant = JSON.parse(tenantRaw);
        if (tenant?.id) {
          config.headers["X-Tenant-ID"] = tenant.id;
        }
      }
    } catch (_) {
      // falha silenciosa — a API retornará 400 se o tenant for necessário
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Interceptor de Response ────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (!isUnauthorizedError(error)) {
      return Promise.reject(error);
    }

    const config = error.config as any;
    const usedAuthentication = requestUsedAuthentication(config?.headers);
    if (!usedAuthentication || config?._sessionRefreshRetried) {
      return Promise.reject(error);
    }

    const refreshToken = await getRefreshToken();
    if (!refreshToken) {
      await expireStoredSession();
      return Promise.reject(error);
    }

    config._sessionRefreshRetried = true;
    try {
      const accessToken = await refreshAccessToken();
      setAuthorizationHeader(config, accessToken);
      return api.request(config);
    } catch (refreshError) {
      // Falhas temporarias de rede/servidor nao devem deslogar o cliente.
      // A sessao so e removida quando o backend rejeita o refresh token.
      if (refreshWasRejected(refreshError)) {
        await expireStoredSession();
      }
      return Promise.reject(error);
    }
  },
);

export default api;
