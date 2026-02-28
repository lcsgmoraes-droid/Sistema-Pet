import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
});

// ─── Interceptor de Request ─────────────────────────────────────────────────
// Injeta token JWT + X-Tenant-ID dinamicamente em cada chamada
api.interceptors.request.use(
  async (config) => {
    try {
      // Token de autenticação
      const token = await SecureStore.getItemAsync('auth_token');
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
    if (error.response?.status === 401) {
      await SecureStore.deleteItemAsync('auth_token');
    }
    return Promise.reject(error);
  }
);

export default api;

