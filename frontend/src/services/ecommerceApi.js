/**
 * Ecommerce API Client
 * Instância axios para o módulo de e-commerce (loja pública).
 * Headers de autenticação são adicionados por chamada, não na instância.
 */
import axios from "axios";
import {
  STORAGE_REFRESH_TOKEN_KEY,
  STORAGE_TOKEN_KEY,
} from "../pages/ecommerce/ecommerceMvpUtils";

// baseURL vazio: as chamadas já incluem /api/ no path (ex: /api/ecommerce/...)
// Não usar VITE_API_URL aqui para não duplicar o prefixo /api
const ecommerceApi = axios.create({
  baseURL: "",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshPromise = null;

function getStoredToken(key) {
  try {
    return globalThis.localStorage?.getItem(key) || "";
  } catch {
    return "";
  }
}

function setStoredToken(key, value) {
  try {
    if (value) {
      globalThis.localStorage?.setItem(key, value);
    }
  } catch {
    // Ignora ambientes sem localStorage.
  }
}

function clearStoredCustomerTokens() {
  try {
    globalThis.localStorage?.removeItem(STORAGE_TOKEN_KEY);
    globalThis.localStorage?.removeItem(STORAGE_REFRESH_TOKEN_KEY);
  } catch {
    // Ignora ambientes sem localStorage.
  }
}

async function refreshCustomerToken() {
  if (refreshPromise) return refreshPromise;

  const refreshToken = getStoredToken(STORAGE_REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    throw new Error("Refresh token ausente");
  }

  refreshPromise = axios
    .post("/api/ecommerce/auth/refresh", { refresh_token: refreshToken }, { timeout: 15000 })
    .then((response) => {
      const accessToken = response?.data?.access_token;
      const nextRefreshToken = response?.data?.refresh_token;
      if (!accessToken) {
        throw new Error("Access token ausente na renovacao");
      }
      setStoredToken(STORAGE_TOKEN_KEY, accessToken);
      setStoredToken(STORAGE_REFRESH_TOKEN_KEY, nextRefreshToken || refreshToken);
      return accessToken;
    })
    .catch((error) => {
      clearStoredCustomerTokens();
      throw error;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

ecommerceApi.interceptors.request.use((config) => {
  const accessToken = getStoredToken(STORAGE_TOKEN_KEY);
  if (accessToken && config.headers?.Authorization) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

ecommerceApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = String(originalRequest?.url || "");

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !requestUrl.includes("/api/ecommerce/auth/refresh") &&
      getStoredToken(STORAGE_REFRESH_TOKEN_KEY)
    ) {
      originalRequest._retry = true;
      const accessToken = await refreshCustomerToken();
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return ecommerceApi(originalRequest);
    }

    return Promise.reject(error);
  },
);

export default ecommerceApi;
