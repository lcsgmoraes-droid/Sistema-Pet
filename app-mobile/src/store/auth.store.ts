import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import * as AuthService from "../services/auth.service";
import { EcommerceUser } from "../types";

const ROLE_CACHE_KEY_PREFIX = "ecommerce_role_cache_";

async function cacheEntregadorRole(user: EcommerceUser | null): Promise<void> {
  if (!user?.id) return;

  const cacheKey = `${ROLE_CACHE_KEY_PREFIX}${user.id}`;
  if (user.is_entregador) {
    await SecureStore.setItemAsync(
      cacheKey,
      JSON.stringify({
        is_entregador: true,
        funcionario_id: user.funcionario_id ?? null,
      }),
    );
  } else {
    // Não sobrescreve cache positivo com valor falso para evitar regressão intermitente.
  }
}

async function applyCachedEntregadorRole(
  user: EcommerceUser,
): Promise<EcommerceUser> {
  if (!user?.id || user.is_entregador) return user;

  const cacheKey = `${ROLE_CACHE_KEY_PREFIX}${user.id}`;
  const raw = await SecureStore.getItemAsync(cacheKey);
  if (!raw) return user;

  try {
    const cached = JSON.parse(raw) as {
      is_entregador?: boolean;
      funcionario_id?: number | null;
    };
    if (cached?.is_entregador) {
      return {
        ...user,
        is_entregador: true,
        funcionario_id: cached.funcionario_id ?? user.funcionario_id ?? null,
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
  ) => Promise<void>;
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
    await cacheEntregadorRole(user);
    set({ isAuthenticated: true, user });
  },

  register: async (email, password, nome, cpf) => {
    const { user } = await AuthService.register(email, password, nome, cpf);
    await cacheEntregadorRole(user);
    set({ isAuthenticated: true, user });
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
        const user = await applyCachedEntregadorRole(freshUser);
        await cacheEntregadorRole(user);
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
