import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL } from '../config';

const ACCESS_TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'auth_refresh_token';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
    'X-Client-Channel': 'app',
    'X-Canal-Venda': 'app',
  },
});

function removeJsonContentTypeForFormData(config: any) {
  if (typeof FormData === 'undefined' || !(config.data instanceof FormData) || !config.headers) {
    return;
  }

  const deleteHeader = (name: string) => {
    if (typeof config.headers.delete === 'function') {
      config.headers.delete(name);
      return;
    }

    delete config.headers[name];
  };

  deleteHeader('Content-Type');
  deleteHeader('content-type');
}

// ─── Interceptor de Request ─────────────────────────────────────────────────
// Injeta token JWT + X-Tenant-ID dinamicamente em cada chamada
api.interceptors.request.use(
  async (config) => {
    removeJsonContentTypeForFormData(config);

    try {
      // Token de autenticação
      const token = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Tenant vinculado (persiste em SecureStore)
      const tenantRaw = await SecureStore.getItemAsync('tenant_info');
      if (tenantRaw) {
        const tenant = JSON.parse(tenantRaw);
        if (tenant?.id) {
          config.headers['X-Tenant-ID'] = tenant.id;
        }
      }
    } catch (_) {
      // falha silenciosa — a API retornará 400 se o tenant for necessário
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Interceptor de Response ────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = String(originalRequest?.url || '');

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !requestUrl.includes('/ecommerce/auth/refresh')
    ) {
      const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      if (refreshToken) {
        try {
          originalRequest._retry = true;
          const { data } = await axios.post(
            `${API_BASE_URL}/ecommerce/auth/refresh`,
            { refresh_token: refreshToken },
            { timeout: 15000 },
          );
          if (data?.access_token) {
            await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, data.access_token);
          }
          if (data?.refresh_token) {
            await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, data.refresh_token);
          }
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch {
          await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
          await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
        }
      } else {
        await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
      }
    } else if (error.response?.status === 401) {
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    }
    return Promise.reject(error);
  }
);

export default api;

