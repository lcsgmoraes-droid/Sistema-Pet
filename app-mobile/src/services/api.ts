import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL, TENANT_ID } from '../config';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'X-Tenant-ID': TENANT_ID,
    'ngrok-skip-browser-warning': 'true',
  },
});

// ─── Interceptor de Request: injeta o token JWT se existir ─────────────────
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (_) {
      // sem token → requisição sem autenticação
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Interceptor de Response: trata erros globais ──────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expirado — limpa o storage
      await SecureStore.deleteItemAsync('auth_token');
    }
    return Promise.reject(error);
  }
);

export default api;
