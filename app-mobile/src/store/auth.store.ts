import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import * as AuthService from "../services/auth.service";
import { AppAccessProfile, AppProfileType, AuthResponse, EcommerceUser } from "../types";

const ROLE_CACHE_KEY_PREFIX = "ecommerce_role_cache_";

async function clearOperationalRoleCache(user: EcommerceUser | null): Promise<void> {
  if (!user?.id) return;
  await SecureStore.deleteItemAsync(`${ROLE_CACHE_KEY_PREFIX}${user.id}`);
}

async function cacheOperationalRole(user: EcommerceUser | null): Promise<void> {
  if (!user?.id) return;
  if (!user.is_veterinario && !user.is_entregador && !user.is_funcionario) {
    await clearOperationalRoleCache(user);
    return;
  }

  const cacheKey = `${ROLE_CACHE_KEY_PREFIX}${user.id}`;
  await SecureStore.setItemAsync(
    cacheKey,
    JSON.stringify({
      is_veterinario: user.is_veterinario ?? false,
      veterinario_id: user.veterinario_id ?? null,
      is_entregador: user.is_entregador ?? false,
      is_funcionario: user.is_funcionario ?? false,
      funcionario_id: user.funcionario_id ?? null,
      perfil_operacional: user.is_veterinario
        ? "veterinario"
        : user.is_entregador
          ? "entregador"
          : user.is_funcionario
            ? "funcionario"
            : user.perfil_operacional ?? "cliente",
    }),
  );
}

async function applyCachedOperationalRole(
  user: EcommerceUser,
): Promise<EcommerceUser> {
  if (!user?.id || user.is_veterinario || user.is_entregador || user.is_funcionario) return user;
  if (user.perfil_operacional === "cliente") {
    await clearOperationalRoleCache(user);
    return user;
  }

  const cacheKey = `${ROLE_CACHE_KEY_PREFIX}${user.id}`;
  const raw = await SecureStore.getItemAsync(cacheKey);
  if (!raw) return user;

  try {
    const cached = JSON.parse(raw) as {
      is_veterinario?: boolean;
      veterinario_id?: number | null;
      is_entregador?: boolean;
      is_funcionario?: boolean;
      funcionario_id?: number | null;
      perfil_operacional?: AppProfileType;
    };
    if (cached?.is_veterinario || cached?.is_entregador || cached?.is_funcionario) {
      return {
        ...user,
        is_veterinario: cached.is_veterinario ?? user.is_veterinario ?? false,
        veterinario_id: cached.veterinario_id ?? user.veterinario_id ?? null,
        is_entregador: cached.is_entregador ?? user.is_entregador ?? false,
        is_funcionario: cached.is_funcionario ?? user.is_funcionario ?? false,
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

function shouldSelectProfile(user: EcommerceUser | null): boolean {
  return (user?.available_profiles?.length ?? 0) > 1;
}

interface AuthState {
  isAuthenticated: boolean;
  user: EcommerceUser | null;
  pendingProfiles: AppAccessProfile[];
  needsProfileSelection: boolean;
  isLoading: boolean;

  // Ações
  login: (email: string, password: string) => Promise<void>;
  selectProfile: (profileType: AppProfileType) => Promise<void>;
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
  pendingProfiles: [],
  needsProfileSelection: false,
  isLoading: true,

  login: async (email, password) => {
    const { user } = await AuthService.login(email, password);
    if (shouldSelectProfile(user)) {
      set({
        isAuthenticated: false,
        user,
        pendingProfiles: user.available_profiles ?? [],
        needsProfileSelection: true,
        isLoading: false,
      });
      return;
    }
    await cacheOperationalRole(user);
    set({
      isAuthenticated: true,
      user,
      pendingProfiles: [],
      needsProfileSelection: false,
      isLoading: false,
    });
  },

  selectProfile: async (profileType) => {
    const { user } = await AuthService.selectProfile(profileType);
    await cacheOperationalRole(user);
    set({
      isAuthenticated: true,
      user,
      pendingProfiles: [],
      needsProfileSelection: false,
      isLoading: false,
    });
  },

  register: async (email, password, nome, cpf, telefone, acceptedTerms, acceptedPrivacy) => {
    const response = await AuthService.register(email, password, nome, cpf, telefone, acceptedTerms, acceptedPrivacy);
    const { user } = response;
    if (response.requires_email_verification || !response.access_token) {
      set({
        isAuthenticated: false,
        user: null,
        pendingProfiles: [],
        needsProfileSelection: false,
        isLoading: false,
      });
      return response;
    }
    if (shouldSelectProfile(user)) {
      set({
        isAuthenticated: false,
        user,
        pendingProfiles: user.available_profiles ?? [],
        needsProfileSelection: true,
        isLoading: false,
      });
      return response;
    }
    await cacheOperationalRole(user);
    set({
      isAuthenticated: true,
      user,
      pendingProfiles: [],
      needsProfileSelection: false,
      isLoading: false,
    });
    return response;
  },

  logout: async () => {
    await AuthService.logout();
    set({ isAuthenticated: false, user: null, pendingProfiles: [], needsProfileSelection: false });
  },

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const token = await AuthService.getStoredToken();
      if (token) {
        const freshUser = await AuthService.getProfile();
        if (
          freshUser.perfil_operacional === "cliente" &&
          !freshUser.is_veterinario &&
          !freshUser.is_entregador &&
          !freshUser.is_funcionario
        ) {
          await clearOperationalRoleCache(freshUser);
        }
        const user = await applyCachedOperationalRole(freshUser);
        await cacheOperationalRole(user);
        set({
          isAuthenticated: true,
          user,
          pendingProfiles: [],
          needsProfileSelection: false,
          isLoading: false,
        });
      } else {
        set({
          isAuthenticated: false,
          user: null,
          pendingProfiles: [],
          needsProfileSelection: false,
          isLoading: false,
        });
      }
    } catch {
      set({
        isAuthenticated: false,
        user: null,
        pendingProfiles: [],
        needsProfileSelection: false,
        isLoading: false,
      });
    }
  },

  updateUser: (updates) => {
    const { user } = get();
    if (user) {
      set({ user: { ...user, ...updates } });
    }
  },
}));
