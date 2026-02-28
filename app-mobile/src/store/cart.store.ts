import { create } from 'zustand';
import { ItemCarrinho, Produto } from '../types';
import * as ShopService from '../services/shop.service';

interface CartState {
  itens: ItemCarrinho[];
  subtotal: number;
  isLoading: boolean;

  // Ações
  carregar: () => Promise<void>;
  adicionar: (produto: Produto, quantidade?: number) => Promise<void>;
  atualizar: (produto_id: number, quantidade: number) => Promise<void>;
  remover: (produto_id: number) => Promise<void>;
  limpar: () => Promise<void>;

  // Computed
  totalItens: () => number;
}

export const useCartStore = create<CartState>()((set, get) => ({
  itens: [],
  subtotal: 0,
  isLoading: false,

  carregar: async () => {
    set({ isLoading: true });
    try {
      const carrinho = await ShopService.obterCarrinho();
      // converte o formato do backend para o nosso ItemCarrinho
      const itens: ItemCarrinho[] = (carrinho.itens || []).map((item: any) => ({
        produto_id: item.produto_id,
        nome: item.nome,
        preco_unitario: item.preco_unitario,
        quantidade: item.quantidade,
        subtotal: item.subtotal,
        foto_url: item.foto_url,
      }));
      set({
        itens,
        subtotal: carrinho.subtotal ?? 0,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  adicionar: async (produto, quantidade = 1) => {
    await ShopService.adicionarAoCarrinho(produto.id, quantidade);
    // Atualiza otimisticamente antes de recarregar
    const { itens } = get();
    const existente = itens.find((i) => i.produto_id === produto.id);
    if (existente) {
      const novaQtd = existente.quantidade + quantidade;
      const novosItens = itens.map((i) =>
        i.produto_id === produto.id
          ? { ...i, quantidade: novaQtd, subtotal: novaQtd * i.preco_unitario }
          : i
      );
      set({ itens: novosItens });
    } else {
      const preco = produto.promocao_ativa && produto.preco_promocional
        ? produto.preco_promocional
        : produto.preco;
      set({
        itens: [
          ...itens,
          {
            produto_id: produto.id,
            nome: produto.nome,
            preco_unitario: preco,
            quantidade,
            subtotal: preco * quantidade,
            foto_url: produto.foto_url,
          },
        ],
      });
    }
    // recalcula subtotal
    const { itens: updated } = get();
    const subtotal = updated.reduce((acc, i) => acc + i.subtotal, 0);
    set({ subtotal });
  },

  atualizar: async (produto_id, quantidade) => {
    await ShopService.atualizarCarrinho(produto_id, quantidade);
    const { itens } = get();
    const novosItens = itens.map((i) =>
      i.produto_id === produto_id
        ? { ...i, quantidade, subtotal: quantidade * i.preco_unitario }
        : i
    );
    const subtotal = novosItens.reduce((acc, i) => acc + i.subtotal, 0);
    set({ itens: novosItens, subtotal });
  },

  remover: async (produto_id) => {
    await ShopService.removerDoCarrinho(produto_id);
    const { itens } = get();
    const novosItens = itens.filter((i) => i.produto_id !== produto_id);
    const subtotal = novosItens.reduce((acc, i) => acc + i.subtotal, 0);
    set({ itens: novosItens, subtotal });
  },

  limpar: async () => {
    await ShopService.limparCarrinho();
    set({ itens: [], subtotal: 0 });
  },

  totalItens: () => {
    return get().itens.reduce((acc, i) => acc + i.quantidade, 0);
  },
}));
