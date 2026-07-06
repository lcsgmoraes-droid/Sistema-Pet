import * as SecureStore from 'expo-secure-store';
import { Linking } from 'react-native';
import { create } from 'zustand';
import { API_BASE_URL } from '../config';

export interface TenantInfo {
  id: string;
  slug: string;
  nome: string;
  logo_url: string | null;
  endereco?: string | null;
  numero?: string | null;
  bairro?: string | null;
  cep?: string | null;
  cidade: string | null;
  uf: string | null;
}

interface TenantState {
  tenant: TenantInfo | null;
  isLoading: boolean;
  loadTenant: () => Promise<void>;
  buscarPorSlug: (slug: string) => Promise<TenantInfo>;
  buscarPorLocalidade: (cidade: string, uf?: string | null) => Promise<TenantInfo[]>;
  confirmarTenant: (tenant: TenantInfo) => Promise<void>;
  limparTenant: () => Promise<void>;
}

const STORAGE_KEY = 'tenant_info';
const API_UNAVAILABLE_MESSAGE = 'Servico temporariamente indisponivel. Tente novamente em instantes.';

function apiPublicBaseUrl(): string {
  return API_BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
}

async function apiErrorMessage(response: Response, fallback: string): Promise<string> {
  if (response.status >= 500) {
    return API_UNAVAILABLE_MESSAGE;
  }

  const body = await response.json().catch(() => ({}));
  return body.detail || fallback;
}

export function extractStoreSlug(input: string): string {
  const raw = input.trim().toLowerCase();
  if (!raw) return '';

  try {
    const url = new URL(raw);
    const querySlug =
      url.searchParams.get('loja') ||
      url.searchParams.get('slug') ||
      url.searchParams.get('tenant') ||
      url.searchParams.get('store');

    if (querySlug) return sanitizeSlug(querySlug);

    const segments = url.pathname
      .split('/')
      .map((segment) => segment.trim())
      .filter(Boolean);
    return sanitizeSlug(firstUsefulSegment(segments));
  } catch {
    const [, queryString = ''] = raw.split('?');
    const queryParams = new URLSearchParams(queryString);
    const querySlug =
      queryParams.get('loja') ||
      queryParams.get('slug') ||
      queryParams.get('tenant') ||
      queryParams.get('store');

    if (querySlug) return sanitizeSlug(querySlug);

    const withoutProtocol = raw
      .replace(/^(?:[a-z]+:\/\/)?[^/\s]+\.[^/\s]+\/?/i, '')
      .replace(/^\//, '');
    const [withoutQuery] = withoutProtocol.split('?');
    return sanitizeSlug(firstUsefulSegment(withoutQuery.split('/').filter(Boolean)) || withoutQuery);
  }
}

function firstUsefulSegment(segments: string[]): string {
  const reserved = new Set(['loja', 'store', 'ecommerce', 'app', 'tenant']);
  return (
    segments.find((segment) => !reserved.has(segment.toLowerCase())) ||
    segments[segments.length - 1] ||
    ''
  );
}

function sanitizeSlug(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '');
}

async function fetchTenantBySlug(slug: string): Promise<TenantInfo> {
  const slugLimpo = extractStoreSlug(slug);
  if (!slugLimpo) {
    throw new Error('Informe o codigo ou QR Code da loja.');
  }

  const response = await fetch(`${apiPublicBaseUrl()}/api/ecommerce/tenant-slug/${slugLimpo}`);

  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, 'Loja nao encontrada. Verifique o codigo.'));
  }

  return response.json();
}

export const useTenantStore = create<TenantState>()((set) => ({
  tenant: null,
  isLoading: true,

  loadTenant: async () => {
    set({ isLoading: true });
    try {
      const raw = await SecureStore.getItemAsync(STORAGE_KEY);
      if (raw) {
        const tenant: TenantInfo = JSON.parse(raw);
        set({ tenant });
        return;
      }

      const initialUrl = await Linking.getInitialURL().catch(() => null);
      const slugInicial = initialUrl ? extractStoreSlug(initialUrl) : '';
      if (slugInicial) {
        const tenant = await fetchTenantBySlug(slugInicial);
        await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(tenant));
        set({ tenant });
      }
    } catch {
      // Ignore corrupted local tenant data and force a fresh selection later.
    } finally {
      set({ isLoading: false });
    }
  },

  buscarPorSlug: async (slug: string) => {
    return fetchTenantBySlug(slug);
  },

  buscarPorLocalidade: async (cidade: string, uf?: string | null) => {
    const cidadeLimpa = cidade.trim();
    if (!cidadeLimpa) return [];

    const params = new URLSearchParams({ cidade: cidadeLimpa });
    if (uf?.trim()) params.set('uf', uf.trim().slice(0, 2).toUpperCase());

    const response = await fetch(`${apiPublicBaseUrl()}/api/ecommerce/tenants/sugerir?${params.toString()}`);
    if (!response.ok) {
      if (response.status === 404) return [];
      throw new Error(await apiErrorMessage(response, 'Nao foi possivel buscar lojas pela localizacao.'));
    }

    const data = await response.json().catch(() => ({ lojas: [] }));
    return Array.isArray(data.lojas) ? data.lojas : [];
  },

  confirmarTenant: async (tenant: TenantInfo) => {
    await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(tenant));
    set({ tenant });
  },

  limparTenant: async () => {
    await SecureStore.deleteItemAsync(STORAGE_KEY);
    set({ tenant: null });
  },
}));
