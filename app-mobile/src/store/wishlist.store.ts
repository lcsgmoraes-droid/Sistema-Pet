import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'app_wishlist_products';

interface WishlistState {
  ids: number[];
  carregado: boolean;

  // Ações
  carregar: () => Promise<void>;
  toggle: (produtoId: number) => Promise<void>;
  temNaLista: (produtoId: number) => boolean;
}

export const useWishlistStore = create<WishlistState>()((set, get) => ({
  ids: [],
  carregado: false,

  carregar: async () => {
    if (get().carregado) return;
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      const ids: number[] = raw ? JSON.parse(raw) : [];
      set({ ids, carregado: true });
    } catch {
      set({ carregado: true });
    }
  },

  toggle: async (produtoId) => {
    const atual = get().ids;
    const novo = atual.includes(produtoId)
      ? atual.filter((id) => id !== produtoId)
      : [...atual, produtoId];
    set({ ids: novo });
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(novo));
    } catch {
      // silencioso
    }
  },

  temNaLista: (produtoId) => get().ids.includes(produtoId),
}));
