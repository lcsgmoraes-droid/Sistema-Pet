import api from "./api";

export type ProdutoCadastro = {
  id: number;
  nome: string;
  codigo: string | null;
  codigo_barras: string | null;
  descricao_curta: string | null;
};

export type ProdutoCadastroPayload = Partial<Pick<ProdutoCadastro, "nome" | "codigo_barras" | "descricao_curta">>;

export async function obterCadastroProdutoFuncionario(produtoId: number): Promise<ProdutoCadastro> {
  const { data } = await api.get<ProdutoCadastro>(`/app/funcionario/produtos/${produtoId}/cadastro`);
  return data;
}

export async function atualizarCadastroProdutoFuncionario(produtoId: number, payload: ProdutoCadastroPayload): Promise<ProdutoCadastro> {
  const { data } = await api.patch<ProdutoCadastro>(`/app/funcionario/produtos/${produtoId}/cadastro`, payload);
  return data;
}

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
  codigo_barras?: string;
  chave_cadastro?: string;
  nome: string;
  preco_venda: number;
  preco_custo: number;
  unidade: "UN" | "KG" | "CX" | "PC" | "LT";
  codigo?: string;
  descricao_curta?: string;
};

export type FotoProdutoRapido = { uri: string; name: string; type: string; enviada?: boolean };

export async function consultarSkuProdutoRapido(codigo: string): Promise<{ codigo: string; disponivel: boolean; produto: ProdutoRapido | null }> {
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
