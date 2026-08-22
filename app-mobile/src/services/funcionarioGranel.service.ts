import api from "./api";

export type FuncionarioGranelProduto = {
  id: number;
  codigo?: string | null;
  codigo_barras?: string | null;
  nome: string;
  estoque_atual: number;
  peso_embalagem: number;
  unidade?: string | null;
  e_granel: boolean;
};

function normalizarProduto(data: any): FuncionarioGranelProduto {
  return {
    id: Number(data.id),
    codigo: data.codigo ?? null,
    codigo_barras: data.codigo_barras ?? null,
    nome: String(data.nome ?? ""),
    estoque_atual: Number(data.estoque_atual ?? 0),
    peso_embalagem: Number(data.peso_embalagem ?? 0),
    unidade: data.unidade ?? null,
    e_granel: Boolean(data.e_granel),
  };
}

export async function obterConfigGranelFuncionario(): Promise<{ bipagem_obrigatoria: boolean }> {
  const response = await api.get("/app/funcionario/granel/config");
  return { bipagem_obrigatoria: Boolean(response.data?.bipagem_obrigatoria) };
}

export async function buscarProdutoGranelPorBarcode(
  barcode: string,
  etapa: "origem" | "granel",
  produtoOrigemId?: number,
): Promise<FuncionarioGranelProduto> {
  const response = await api.get(
    `/app/funcionario/granel/produtos/barcode/${encodeURIComponent(barcode)}`,
    { params: { etapa, produto_origem_id: produtoOrigemId } },
  );
  return normalizarProduto(response.data);
}

export async function buscarProdutosGranelFuncionario(
  termo: string,
  etapa: "origem" | "granel",
  produtoOrigemId?: number,
): Promise<FuncionarioGranelProduto[]> {
  const response = await api.get("/app/funcionario/granel/produtos/buscar", {
    params: { termo: termo.trim(), etapa, produto_origem_id: produtoOrigemId },
  });
  return Array.isArray(response.data) ? response.data.map(normalizarProduto) : [];
}

export async function converterGranelFuncionario(payload: {
  produto_origem_id: number;
  produto_granel_id: number;
  quantidade_pacotes: number;
  produto_origem_barcode?: string | null;
  produto_granel_barcode?: string | null;
  observacao?: string | null;
}): Promise<any> {
  const response = await api.post("/app/funcionario/granel/converter", payload);
  return response.data;
}
