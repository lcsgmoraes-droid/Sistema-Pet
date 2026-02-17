/**
 * API Client - Axios Multi-Tenant
 */
import axios from 'axios';

// 🔍 VERIFICAÇÃO DE AMBIENTE
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;
const configuredApiUrl = import.meta.env.VITE_API_URL;
const mode = import.meta.env.MODE;

// ⚠️ ALERTA: Em produção DEVE ser '/api', em desenvolvimento DEVE ser 'http://127.0.0.1:8000'
const API_URL = configuredApiUrl || 'http://127.0.0.1:8000';

// 🔍 DEBUG: Log de configuração ao carregar o módulo
console.log('═══════════════════════════════════════════════════════');
console.log('🌐 [API Config] Configuração do Axios carregada');
console.log('═══════════════════════════════════════════════════════');
console.log('  Mode:', mode);
console.log('  isDevelopment:', isDevelopment);
console.log('  isProduction:', isProduction);
console.log('  VITE_API_URL (configurado):', configuredApiUrl);
console.log('  API_URL (final):', API_URL);
console.log('  Origem:', window.location.origin);
console.log('═══════════════════════════════════════════════════════');

// ⚠️ VALIDAÇÃO: Alertar sobre configuração incorreta
if (isProduction && API_URL !== '/api') {
  console.error('❌ [API Config] ERRO: Em produção, VITE_API_URL deve ser "/api"!');
  console.error('   Valor atual:', API_URL);
  console.error('   Esperado: /api');
  console.error('   Verifique o arquivo .env.production e faça rebuild!');
}

if (isDevelopment && !API_URL.includes('127.0.0.1') && !API_URL.includes('localhost')) {
  console.warn('⚠️ [API Config] AVISO: Em desenvolvimento, API_URL geralmente aponta para localhost');
  console.warn('   Valor atual:', API_URL);
}

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');

    // 🔍 DEBUG: Log token e configuração
    console.log('🔐 [API Interceptor]', {
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 20)}...` : 'NO TOKEN',
      headers: config.headers
    });

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('✅ Token adicionado ao header Authorization');
    } else {
      console.warn('⚠️ Nenhum token encontrado no localStorage');
    }

    return config;
  },
  (error) => {
    console.error('❌ [API Interceptor] Erro na requisição:', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    console.log('✅ [API Response]', {
      status: response.status,
      url: response.config.url,
      dataPreview: JSON.stringify(response.data).substring(0, 100)
    });
    return response;
  },
  (error) => {
    const status = error.response?.status;

    // 🔍 DEBUG: Log detalhado do erro
    console.error('❌ [API Response Error]', {
      status: status,
      url: error.config?.url,
      fullURL: `${error.config?.baseURL}${error.config?.url}`,
      errorData: error.response?.data,
      headers: error.response?.headers,
      requestHeaders: error.config?.headers
    });

    if (status === 401) {
      console.warn('⚠️ Status 401: Sessão inválida ou tenant não selecionado');

      localStorage.removeItem('access_token');
      localStorage.removeItem('tenants');

      window.location.href = '/login';
    }

    if (status === 403) {
      console.warn('⚠️ Status 403: Acesso negado para este tenant');
      console.log('🔍 Detalhes do erro 403:', {
        message: error.response?.data?.detail || error.message,
        token: localStorage.getItem('access_token')?.substring(0, 20) + '...'
      });
    }

    return Promise.reject(error);
  }
);

export default api;
