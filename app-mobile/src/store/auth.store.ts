import { create } from 'zustand';
import { EcommerceUser } from '../types';
import * as AuthService from '../services/auth.service';

interface AuthState {
  isAuthenticated: boolean;
  user: EcommerceUser | null;
  isLoading: boolean;

  // Ações
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, nome?: string) => Promise<void>;
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
    set({ isAuthenticated: true, user });
  },

  register: async (email, password, nome) => {
    const { user } = await AuthService.register(email, password, nome);
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
        const user = await AuthService.getProfile();
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
