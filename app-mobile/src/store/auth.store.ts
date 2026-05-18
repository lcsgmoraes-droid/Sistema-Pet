import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import * as AuthService from "../services/auth.service";
import { AuthResponse, EcommerceUser } from "../types";

const ROLE_CACHE_KEY_PREFIX = "ecommerce_role_cache_";

async function cacheOperationalRole(user: EcommerceUser | null): Promise<void> {
  if (!user?.id) return;

  const cacheKey = `${ROLE_CACHE_KEY_PREFIX}${user.id}`;
  if (user.is_veterinario || user.is_entregador) {
    await SecureStore.setItemAsync(
      cacheKey,
      JSON.stringify({
        is_veterinario: user.is_veterinario ?? false,
        veterinario_id: user.veterinario_id ?? null,
        is_entregador: user.is_entregador ?? false,
        funcionario_id: user.funcionario_id ?? null,
        perfil_operacional: user.is_veterinario
          ? "veterinario"
          : user.is_entregador
            ? "entregador"
            : user.perfil_operacional ?? "cliente",
      }),
    );
  } else {
    // Não sobrescreve cache positivo com valor falso para evitar regressão intermitente.
  }
}

async function applyCachedOperationalRole(
  user: EcommerceUser,
): Promise<EcommerceUser> {
  if (!user?.id || user.is_veterinario || user.is_entregador) return user;

  const cacheKey = `${ROLE_CACHE_KEY_PREFIX}${user.id}`;
  const raw = await SecureStore.getItemAsync(cacheKey);
  if (!raw) return user;

  try {
    const cached = JSON.parse(raw) as {
      is_veterinario?: boolean;
      veterinario_id?: number | null;
      is_entregador?: boolean;
      funcionario_id?: number | null;
      perfil_operacional?: "cliente" | "entregador" | "veterinario";
    };
    if (cached?.is_veterinario || cached?.is_entregador) {
      return {
        ...user,
        is_veterinario: cached.is_veterinario ?? user.is_veterinario ?? false,
        veterinario_id: cached.veterinario_id ?? user.veterinario_id ?? null,
        is_entregador: cached.is_entregador ?? user.is_entregador ?? false,
        funcionario_id: cached.funcionario_id ?? user.funcionario_id ?? null,
        perfil_operacional: cached.perfil_operacional ?? user.perfil_operacional,
      };
    }
  } catch {
    // Cache inválido: remove para não repetir erro de parse nas próximas aberturas.
    await SecureStore.deleteItemAsync(cacheKey);
  }

  return user;
}

interface AuthState {
  isAuthenticated: boolean;
  user: EcommerceUser | null;
  isLoading: boolean;

  // Ações
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    nome?: string,
    cpf?: string,
    telefone?: string,
    acceptedTerms?: boolean,
    acceptedPrivacy?: boolean,
  ) => Promise<AuthResponse>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  updateUser: (updates: Partial<EcommerceUser>) => void;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  isAuthenticated: false,
  user: null,
  isLoading: true,

  login: async (email, password) => {
    const { user } = await AuthService.login(email, password);
    await cacheOperationalRole(user);
    set({ isAuthenticated: true, user });
  },

  register: async (email, password, nome, cpf, telefone, acceptedTerms, acceptedPrivacy) => {
    const response = await AuthService.register(email, password, nome, cpf, telefone, acceptedTerms, acceptedPrivacy);
    const { user } = response;
    if (response.requires_email_verification || !response.access_token) {
      set({ isAuthenticated: false, user: null });
      return response;
    }
    await cacheOperationalRole(user);
    set({ isAuthenticated: true, user });
    return response;
  },

  logout: async () => {
    await AuthService.logout();
    set({ isAuthenticated: false, user: null });
  },

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const token = await AuthService.getStoredToken();
      if (token) {
        const freshUser = await AuthService.getProfile();
        const user = await applyCachedOperationalRole(freshUser);
        await cacheOperationalRole(user);
        set({ isAuthenticated: true, user, isLoading: false });
      } else {
        set({ isAuthenticated: false, user: null, isLoading: false });
      }
    } catch {
      set({ isAuthenticated: false, user: null, isLoading: false });
    }
  },

  updateUser: (updates) => {
    const { user } = get();
    if (user) {
      set({ user: { ...user, ...updates } });
    }
  },
}));
