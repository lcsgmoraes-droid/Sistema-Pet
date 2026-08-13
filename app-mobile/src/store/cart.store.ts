import { create } from "zustand";
import {
  CartPersistenceContext,
  clearCartSnapshot,
  loadCartSnapshot,
  saveCartSnapshot,
} from "../services/cartPersistence";
import * as ShopService from "../services/shop.service";
import { ItemCarrinho, Produto } from "../types";

interface CartState {
  itens: ItemCarrinho[];
  subtotal: number;
  isLoading: boolean;
  context: CartPersistenceContext | null;

  carregar: (context?: CartPersistenceContext) => Promise<void>;
  adicionar: (produto: Produto, quantidade?: number) => Promise<void>;
  atualizar: (produto_id: number, quantidade: number) => Promise<void>;
  remover: (produto_id: number) => Promise<void>;
  limpar: () => Promise<void>;
  limparLocal: () => void;
  totalItens: () => number;
}

let activeLoad: Promise<void> | null = null;
let activeLoadKey: string | null = null;

function contextKey(context: CartPersistenceContext | null): string {
  return context ? `${context.tenantId}:${context.userId}` : "sem-contexto";
}

function sameContext(
  left: CartPersistenceContext | null,
  right: CartPersistenceContext | null,
): boolean {
  return contextKey(left) === contextKey(right);
}

function calculateSubtotal(itens: ItemCarrinho[]): number {
  return itens.reduce((total, item) => total + item.subtotal, 0);
}

function mapServerItems(
  carrinho: any,
  cachedItems: ItemCarrinho[],
): ItemCarrinho[] {
  return (carrinho.itens || []).map((item: any) => {
    const cached = cachedItems.find(
      (candidate) => candidate.produto_id === item.produto_id,
    );
    return {
      produto_id: item.produto_id,
      nome: item.nome,
      preco_unitario: item.preco_unitario,
      quantidade: item.quantidade,
      subtotal: item.subtotal,
      foto_url: item.foto_url || cached?.foto_url || null,
    };
  });
}

function canSkipUnavailableCachedItem(error: unknown): boolean {
  const status = (error as { response?: { status?: number } })?.response
    ?.status;
  return status === 400 || status === 404 || status === 409 || status === 422;
}

async function persistCart(
  context: CartPersistenceContext | null,
  itens: ItemCarrinho[],
): Promise<void> {
  if (!context) return;
  await saveCartSnapshot(context, itens);
}

export const useCartStore = create<CartState>()((set, get) => ({
  itens: [],
  subtotal: 0,
  isLoading: false,
  context: null,

  carregar: async (requestedContext) => {
    const context = requestedContext || get().context;
    const loadKey = contextKey(context);
    if (activeLoad && activeLoadKey === loadKey) return activeLoad;

    const operation = (async () => {
      const cached = context
        ? await loadCartSnapshot(context).catch(() => null)
        : null;
      const contextChanged = !sameContext(get().context, context);

      if (contextChanged) {
        set({
          context,
          itens: cached?.itens || [],
          subtotal: cached?.subtotal || 0,
          isLoading: true,
        });
      } else {
        if (cached?.itens.length && get().itens.length === 0) {
          set({ itens: cached.itens, subtotal: cached.subtotal });
        }
        set({ isLoading: true });
      }

      try {
        let carrinho = await ShopService.obterCarrinho();
        let itens = mapServerItems(carrinho, cached?.itens || []);

        // Se o servidor perdeu o carrinho, restaura a copia local do mesmo
        // usuario e da mesma loja. Itens indisponiveis sao ignorados.
        if (itens.length === 0 && cached?.itens.length) {
          for (const item of cached.itens) {
            try {
              await ShopService.adicionarAoCarrinho(
                item.produto_id,
                item.quantidade,
              );
            } catch (error) {
              if (!canSkipUnavailableCachedItem(error)) throw error;
            }
          }
          carrinho = await ShopService.obterCarrinho();
          itens = mapServerItems(carrinho, cached.itens);
          if (itens.length === 0) itens = cached.itens;
        }

        const subtotal = calculateSubtotal(itens);
        if (!sameContext(get().context, context)) return;
        set({ context, itens, subtotal, isLoading: false });
        await persistCart(context, itens).catch(() => undefined);
      } catch {
        // Falha de rede ou sessao em renovacao: nao transforma o carrinho
        // visivel em vazio. A copia local continua disponivel.
        if (!sameContext(get().context, context)) return;
        if (cached) {
          set({
            context,
            itens: cached.itens,
            subtotal: cached.subtotal,
            isLoading: false,
          });
        } else {
          set({ context, isLoading: false });
        }
      }
    })();

    activeLoad = operation;
    activeLoadKey = loadKey;
    try {
      await operation;
    } finally {
      if (activeLoad === operation) {
        activeLoad = null;
        activeLoadKey = null;
      }
    }
  },

  adicionar: async (produto, quantidade = 1) => {
    await ShopService.adicionarAoCarrinho(produto.id, quantidade);
    const { itens, context } = get();
    const existente = itens.find((item) => item.produto_id === produto.id);
    let novosItens: ItemCarrinho[];

    if (existente) {
      const novaQuantidade = existente.quantidade + quantidade;
      novosItens = itens.map((item) =>
        item.produto_id === produto.id
          ? {
              ...item,
              quantidade: novaQuantidade,
              subtotal: novaQuantidade * item.preco_unitario,
            }
          : item,
      );
    } else {
      const preco =
        produto.promocao_ativa && produto.preco_promocional
          ? produto.preco_promocional
          : produto.preco;
      novosItens = [
        ...itens,
        {
          produto_id: produto.id,
          nome: produto.nome,
          preco_unitario: preco,
          quantidade,
          subtotal: preco * quantidade,
          foto_url: produto.foto_url,
        },
      ];
    }

    set({ itens: novosItens, subtotal: calculateSubtotal(novosItens) });
    await persistCart(context, novosItens).catch(() => undefined);
  },

  atualizar: async (produto_id, quantidade) => {
    await ShopService.atualizarCarrinho(produto_id, quantidade);
    const { itens, context } = get();
    const novosItens = itens.map((item) =>
      item.produto_id === produto_id
        ? {
            ...item,
            quantidade,
            subtotal: quantidade * item.preco_unitario,
          }
        : item,
    );
    set({ itens: novosItens, subtotal: calculateSubtotal(novosItens) });
    await persistCart(context, novosItens).catch(() => undefined);
  },

  remover: async (produto_id) => {
    await ShopService.removerDoCarrinho(produto_id);
    const { itens, context } = get();
    const novosItens = itens.filter((item) => item.produto_id !== produto_id);
    set({ itens: novosItens, subtotal: calculateSubtotal(novosItens) });
    await persistCart(context, novosItens).catch(() => undefined);
  },

  limpar: async () => {
    await ShopService.limparCarrinho();
    const { context } = get();
    set({ itens: [], subtotal: 0 });
    await persistCart(context, []).catch(() => undefined);
  },

  limparLocal: () => {
    const { context } = get();
    set({ itens: [], subtotal: 0, isLoading: false, context: null });
    if (context) void clearCartSnapshot(context).catch(() => undefined);
  },

  totalItens: () =>
    get().itens.reduce((total, item) => total + item.quantidade, 0),
}));
