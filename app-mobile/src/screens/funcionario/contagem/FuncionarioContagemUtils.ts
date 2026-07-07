import type { FuncionarioProdutoEstoque } from "../../../types";

export type ContagemItemLocal = {
  id: string;
  produto: FuncionarioProdutoEstoque;
  quantidade: number;
  observacao?: string | null;
};

type IncrementarProdutoContagemRapidaOptions = {
  retornarQuantidade?: boolean;
};

type IncrementarProdutoContagemRapidaResultado = {
  itens: ContagemItemLocal[];
  quantidadeAtual: number;
};

export function mensagemErroApi(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  const message = error?.response?.data?.message;
  if (typeof message === "string" && message.trim()) return message;
  return fallback;
}

export function parseNumero(valor: string): number | null {
  const normalizado = valor.replace(/\./g, "").replace(",", ".").trim();
  if (!normalizado) return null;
  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : null;
}

export function formatarQuantidade(valor: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor ?? 0));
}

export function incrementarProdutoContagemRapida(
  itens: ContagemItemLocal[],
  produto: FuncionarioProdutoEstoque,
  options: { retornarQuantidade: true },
): IncrementarProdutoContagemRapidaResultado;
export function incrementarProdutoContagemRapida(
  itens: ContagemItemLocal[],
  produto: FuncionarioProdutoEstoque,
  options?: IncrementarProdutoContagemRapidaOptions,
): ContagemItemLocal[];
export function incrementarProdutoContagemRapida(
  itens: ContagemItemLocal[],
  produto: FuncionarioProdutoEstoque,
  options: IncrementarProdutoContagemRapidaOptions = {},
): ContagemItemLocal[] | IncrementarProdutoContagemRapidaResultado {
  let quantidadeAtual = 1;
  const existente = itens.find((item) => item.produto.id === produto.id);
  const proximos = existente
    ? itens.map((item) => {
        if (item.produto.id !== produto.id) return item;
        quantidadeAtual = item.quantidade + 1;
        return { ...item, quantidade: quantidadeAtual };
      })
    : [
        ...itens,
        {
          id: String(produto.id),
          produto,
          quantidade: 1,
          observacao: null,
        },
      ];

  if (options.retornarQuantidade) {
    return { itens: proximos, quantidadeAtual };
  }

  return proximos;
}
