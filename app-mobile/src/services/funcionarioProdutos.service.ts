import api from "./api";

export type ProdutoRapido = {
  id: number;
  nome: string;
  codigo: string;
  codigo_barras: string | null;
  unidade: string;
  preco_venda: number | null;
  ativo: boolean;
  situacao: boolean | null;
};

export type ProdutoRapidoPayload = {
  codigo_barras: string;
  nome: string;
  preco_venda: number;
  preco_custo: number;
  unidade: "UN" | "KG" | "CX" | "PC" | "LT";
};

export async function consultarCodigoProdutoRapido(codigo: string): Promise<ProdutoRapido | null> {
  const { data } = await api.get<ProdutoRapido | null>(
    "/app/funcionario/produtos/consultar-codigo", { params: { codigo: codigo.trim() } },
  );
  return data;
}

export async function criarProdutoRapido(payload: ProdutoRapidoPayload): Promise<ProdutoRapido> {
  const { data } = await api.post<ProdutoRapido>("/app/funcionario/produtos/rapido", payload);
  return data;
}
