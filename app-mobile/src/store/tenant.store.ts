/**
 * tenant.store.ts
 *
 * Armazena qual loja o usuário vinculou ao app.
 * Persiste em SecureStore para sobreviver a reinicializações.
 *
 * Fluxo:
 *  1. App abre → carrega tenant do storage
 *  2. Se não tiver tenant → mostra SelecionarLojaScreen
 *  3. Usuário digita slug ou lê QR Code → API valida → salva tenant
 *  4. Todas as chamadas de API usam o tenant_id salvo aqui
 */

import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { API_BASE_URL } from '../config';

export interface TenantInfo {
  id: string;           // UUID do tenant
  slug: string;         // ex: "atacadao"
  nome: string;         // ex: "Atacadão das Rações Pet"
  logo_url: string | null;
  cidade: string | null;
  uf: string | null;
}

interface TenantState {
  tenant: TenantInfo | null;
  isLoading: boolean;

  // Carrega do storage persistido
  loadTenant: () => Promise<void>;
  // Busca na API pelo slug e salva
  selecionarPorSlug: (slug: string) => Promise<TenantInfo>;
  // Remove a loja vinculada (forçar re-seleção)
  limparTenant: () => Promise<void>;
}

const STORAGE_KEY = 'tenant_info';

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
      }
    } catch (_) {
      // storage corrompido — ignora
    } finally {
      set({ isLoading: false });
    }
  },

  selecionarPorSlug: async (slug: string) => {
    // Normaliza: remove URL se o usuário colou a URL completa
    // Ex: "https://mlprohub.com.br/atacadao" → "atacadao"
    const slugLimpo = slug
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\/[^/]+\/?/, '') // remove domínio
      .replace(/^\//, '')                   // remove barra inicial
      .split('/')[0]                        // pega só o primeiro segmento
      .split('?')[0];                       // remove query string

    // Chama o endpoint de descoberta de loja
    const base = API_BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
    const response = await fetch(`${base}/api/ecommerce/tenant-slug/${slugLimpo}`);

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || 'Loja não encontrada');
    }

    const tenant: TenantInfo = await response.json();

    // Persiste
    await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(tenant));
    set({ tenant });
    return tenant;
  },

  limparTenant: async () => {
    await SecureStore.deleteItemAsync(STORAGE_KEY);
    set({ tenant: null });
  },
}));
