/**
 * API Client - Axios Multi-Tenant
 */
import axios from 'axios';
import { clearAuthTokens, getAccessToken } from './auth/tokenStorage';

const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;
const configuredApiUrl = import.meta.env.VITE_API_URL;
// Em desenvolvimento, sempre usa proxy do Vite para manter auth/cookies consistentes.
const API_URL = isDevelopment ? '/api' : (configuredApiUrl || '/api');
const apiDebugEnabled = isDevelopment && import.meta.env.VITE_DEBUG_API === 'true';
const PUBLIC_PATH_PREFIXES = [
  '/login',
  '/register',
  '/recuperar-senha',
  '/verificar-email',
  '/termos',
  '/privacidade',
  '/landing',
  '/planos',
  '/app',
  '/ecommerce',
];

const debugLog = (...args) => {
  if (apiDebugEnabled) {
    console.log(...args);
  }
};

const debugWarn = (...args) => {
  if (apiDebugEnabled) {
    console.warn(...args);
  }
};

const isPublicBrowserPath = () => {
  const path = globalThis.location?.pathname || '/';
  return PUBLIC_PATH_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`)
  );
};

if (isProduction && API_URL !== '/api') {
  console.error('[API Config] Em producao, VITE_API_URL deve ser "/api". Valor atual:', API_URL);
}

if (isDevelopment && configuredApiUrl && configuredApiUrl !== '/api') {
  console.warn('[API Config] Ignorando VITE_API_URL em desenvolvimento. Usando "/api" via proxy do Vite.');
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 20000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      debugWarn('[API] Nenhum token de sessao encontrado');
    }

    debugLog('[API Request]', {
      method: config.method,
      url: config.url,
      baseURL: config.baseURL,
    });

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    debugLog('[API Response]', {
      status: response.status,
      url: response.config?.url,
    });
    return response;
  },
  (error) => {
    const status = error.response?.status;

    debugWarn('[API Response Error]', {
      status,
      url: error.config?.url,
      fullURL: `${error.config?.baseURL || ''}${error.config?.url || ''}`,
    });

    if (status === 401) {
      const isPublicPath = isPublicBrowserPath();
      clearAuthTokens();
      localStorage.removeItem('tenants');
      localStorage.removeItem('selectedTenant');
      if (!isPublicPath) {
        globalThis.location.href = '/login';
      }
    }

    if (status === 403) {
      debugWarn('[API] Acesso negado para este tenant');
    }

    if (error.code === 'ECONNABORTED') {
      console.warn('[API] Tempo limite excedido (20s):', error.config?.url);
    }

    return Promise.reject(error);
  }
);

export default api;
