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
  descricao_curta?: string | null;
  imagem_principal?: string | null;
};

export type ProdutoRapidoPayload = {
  codigo_barras: string;
  nome: string;
  preco_venda: number;
  preco_custo: number;
  unidade: "UN" | "KG" | "CX" | "PC" | "LT";
  codigo?: string;
  descricao_curta?: string;
};

export type FotoProdutoRapido = { uri: string; name: string; type: string; enviada?: boolean };

export async function consultarSkuProdutoRapido(codigo: string): Promise<{ codigo: string; disponivel: boolean }> {
  const { data } = await api.get("/app/funcionario/produtos/consultar-sku", { params: { codigo: codigo.trim() } });
  return data;
}

export async function enviarFotoProdutoRapido(produtoId: number, foto: FotoProdutoRapido): Promise<void> {
  const form = new FormData();
  form.append("file", { uri: foto.uri, name: foto.name, type: foto.type } as any);
  await api.post(`/app/funcionario/produtos/${produtoId}/imagens`, form, { timeout: 60000 });
}

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
