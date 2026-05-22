import { create } from "zustand";
import { Produto } from "../types";

export interface FuncionarioPdvItem {
  produto_id: number;
  nome: string;
  preco_unitario: number;
  quantidade: number;
  subtotal: number;
  foto_url?: string | null;
  codigo?: string | null;
  codigo_barras?: string | null;
  estoque?: number | null;
}

interface FuncionarioPdvState {
  itens: FuncionarioPdvItem[];
  subtotal: number;
  adicionarProduto: (produto: Produto, quantidade?: number) => void;
  atualizarQuantidade: (produtoId: number, quantidade: number) => void;
  removerProduto: (produtoId: number) => void;
  limpar: () => void;
  totalItens: () => number;
}

function precoAtual(produto: Produto): number {
  return Number(produto.promocao_ativa && produto.preco_promocional ? produto.preco_promocional : produto.preco) || 0;
}

function estoqueDisponivel(produto: Produto | FuncionarioPdvItem): number | null {
  const estoque = Number(produto.estoque);
  return Number.isFinite(estoque) ? estoque : null;
}

function recalcular(itens: FuncionarioPdvItem[]): { itens: FuncionarioPdvItem[]; subtotal: number } {
  const normalizados = itens.map((item) => ({
    ...item,
    subtotal: item.preco_unitario * item.quantidade,
  }));
  return {
    itens: normalizados,
    subtotal: normalizados.reduce((acc, item) => acc + item.subtotal, 0),
  };
}

export const useFuncionarioPdvStore = create<FuncionarioPdvState>()((set, get) => ({
  itens: [],
  subtotal: 0,

  adicionarProduto: (produto, quantidade = 1) => {
    const qtd = Math.max(1, Math.floor(Number(quantidade) || 1));
    const estoque = estoqueDisponivel(produto);
    const { itens } = get();
    const existente = itens.find((item) => item.produto_id === produto.id);
    const quantidadeAtual = existente?.quantidade ?? 0;
    const novaQuantidade = quantidadeAtual + qtd;

    if (estoque !== null && novaQuantidade > estoque) {
      throw new Error("Quantidade maior que o estoque disponivel.");
    }

    const novosItens = existente
      ? itens.map((item) =>
          item.produto_id === produto.id
            ? { ...item, quantidade: novaQuantidade, estoque }
            : item,
        )
      : [
          ...itens,
          {
            produto_id: produto.id,
            nome: produto.nome,
            preco_unitario: precoAtual(produto),
            quantidade: qtd,
            subtotal: precoAtual(produto) * qtd,
            foto_url: produto.foto_url,
            codigo: produto.codigo,
            codigo_barras: produto.codigo_barras,
            estoque,
          },
        ];

    set(recalcular(novosItens));
  },

  atualizarQuantidade: (produtoId, quantidade) => {
    const qtd = Math.max(0, Math.floor(Number(quantidade) || 0));
    const { itens } = get();
    if (qtd === 0) {
      const novosItens = itens.filter((item) => item.produto_id !== produtoId);
      set(recalcular(novosItens));
      return;
    }

    const itemAtual = itens.find((item) => item.produto_id === produtoId);
    if (itemAtual?.estoque !== null && itemAtual?.estoque !== undefined && qtd > itemAtual.estoque) {
      throw new Error("Quantidade maior que o estoque disponivel.");
    }

    set(recalcular(itens.map((item) => (item.produto_id === produtoId ? { ...item, quantidade: qtd } : item))));
  },

  removerProduto: (produtoId) => {
    set(recalcular(get().itens.filter((item) => item.produto_id !== produtoId)));
  },

  limpar: () => set({ itens: [], subtotal: 0 }),

  totalItens: () => get().itens.reduce((acc, item) => acc + item.quantidade, 0),
}));
