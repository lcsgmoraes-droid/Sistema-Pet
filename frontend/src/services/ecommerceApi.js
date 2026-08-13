/**
 * Ecommerce API Client
 * Instância axios para o módulo de e-commerce (loja pública).
 * Headers de autenticação são adicionados por chamada, não na instância.
 */
import axios from "axios";
import { createRefreshManager } from "../auth/refreshManager";
import {
  clearEcommerceTokens,
  getEcommerceAccessToken,
  getEcommerceRefreshToken,
  setEcommerceAccessToken,
  setEcommerceRefreshToken,
} from "../auth/ecommerceTokenStorage";

const REFRESH_RETRY_EXCLUDED_ENDPOINTS = [
  "/api/ecommerce/auth/login",
  "/api/ecommerce/auth/registrar",
  "/api/ecommerce/auth/refresh",
  "/api/ecommerce/auth/esqueci-senha",
  "/api/ecommerce/auth/resetar-senha",
];

// baseURL vazio: as chamadas já incluem /api/ no path (ex: /api/ecommerce/...)
// Não usar VITE_API_URL aqui para não duplicar o prefixo /api
const ecommerceApi = axios.create({
  baseURL: "",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

const refreshManager = createRefreshManager({
  refreshRequest: (refreshToken) =>
    axios.post(
      "/api/ecommerce/auth/refresh",
      { refresh_token: refreshToken },
      { headers: { "Content-Type": "application/json" } },
    ),
  getRefreshToken: getEcommerceRefreshToken,
  setAccessToken: setEcommerceAccessToken,
  setRefreshToken: setEcommerceRefreshToken,
  clearAuthTokens: clearEcommerceTokens,
});

function isRefreshRetryEligible(config) {
  const url = config?.url || "";
  return !REFRESH_RETRY_EXCLUDED_ENDPOINTS.some((endpoint) => url.includes(endpoint));
}

ecommerceApi.interceptors.request.use((config) => {
  const accessToken = getEcommerceAccessToken();
  if (accessToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

ecommerceApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const canRefresh =
      error.response?.status === 401 &&
      !originalRequest._ecommerceRefreshRetry &&
      isRefreshRetryEligible(originalRequest) &&
      getEcommerceRefreshToken();

    if (!canRefresh) {
      return Promise.reject(error);
    }

    originalRequest._ecommerceRefreshRetry = true;
    try {
      const accessToken = await refreshManager.refreshAccessToken();
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${accessToken}`;
      return ecommerceApi(originalRequest);
    } catch (refreshError) {
      clearEcommerceTokens();
      return Promise.reject(refreshError);
    }
  },
);

export default ecommerceApi;
