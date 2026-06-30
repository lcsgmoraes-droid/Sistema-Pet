import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import api from "./api";
import {
  FuncionarioContagem,
  FuncionarioContagemArquivo,
  FuncionarioContagemExportOptions,
  FuncionarioContagemFornecedor,
  FuncionarioContagemItem,
  FuncionarioContagemPayload,
  FuncionarioContagemResumo,
} from "../types";

function normalizarFornecedor(data: any): FuncionarioContagemFornecedor {
  return {
    id: Number(data.id),
    nome: String(data.nome ?? ""),
    documento: data.documento ?? null,
  };
}

function normalizarItem(data: any): FuncionarioContagemItem {
  return {
    id: Number(data.id),
    produto_id: Number(data.produto_id),
    codigo: data.codigo ?? null,
    codigo_barras: data.codigo_barras ?? null,
    gtin_ean: data.gtin_ean ?? null,
    nome: String(data.nome ?? ""),
    unidade: data.unidade ?? "UN",
    quantidade: Number(data.quantidade ?? 0),
    preco_custo: Number(data.preco_custo ?? 0),
    preco_venda: Number(data.preco_venda ?? 0),
    observacao: data.observacao ?? null,
  };
}

function normalizarResumo(data: any): FuncionarioContagemResumo {
  return {
    id: Number(data.id),
    titulo: String(data.titulo ?? "Contagem"),
    status: String(data.status ?? "salva"),
    fornecedor_id: data.fornecedor_id ?? null,
    fornecedor_nome: data.fornecedor_nome ?? null,
    observacao: data.observacao ?? null,
    total_itens: Number(data.total_itens ?? 0),
    quantidade_total: Number(data.quantidade_total ?? 0),
    created_at: String(data.created_at ?? ""),
  };
}

function normalizarContagem(data: any): FuncionarioContagem {
  return {
    ...normalizarResumo(data),
    itens: Array.isArray(data.itens) ? data.itens.map(normalizarItem) : [],
  };
}

function normalizarArquivo(data: any): FuncionarioContagemArquivo {
  return {
    filename: String(data.filename ?? "contagem.pdf"),
    mime_type: String(data.mime_type ?? "application/octet-stream"),
    base64: String(data.base64 ?? ""),
  };
}

export async function buscarFornecedoresContagemFuncionario(
  termo: string,
): Promise<FuncionarioContagemFornecedor[]> {
  const q = termo.trim();
  if (q.length < 2) return [];
  const response = await api.get("/app/funcionario/contagens/fornecedores/buscar", {
    params: { q },
  });
  return Array.isArray(response.data) ? response.data.map(normalizarFornecedor) : [];
}

export async function salvarContagemFuncionario(
  payload: FuncionarioContagemPayload,
): Promise<FuncionarioContagem> {
  const response = await api.post("/app/funcionario/contagens", payload);
  return normalizarContagem(response.data);
}

export async function listarContagensFuncionario(): Promise<FuncionarioContagemResumo[]> {
  const response = await api.get("/app/funcionario/contagens");
  return Array.isArray(response.data) ? response.data.map(normalizarResumo) : [];
}

export async function obterContagemFuncionario(contagemId: number): Promise<FuncionarioContagem> {
  const response = await api.get(`/app/funcionario/contagens/${contagemId}`);
  return normalizarContagem(response.data);
}

export async function baixarContagemFuncionario(
  contagemId: number,
  formato: "pdf" | "xlsx",
  opcoes: FuncionarioContagemExportOptions,
): Promise<string> {
  const response = await api.get(
    `/app/funcionario/contagens/${contagemId}/export/${formato}/mobile`,
    {
      params: {
        mostrar_custo: Boolean(opcoes.mostrar_custo),
        mostrar_venda: Boolean(opcoes.mostrar_venda),
      },
    },
  );
  const arquivo = normalizarArquivo(response.data);
  const file = new FileSystem.File(FileSystem.Paths.cache, arquivo.filename);
  if (file.exists) {
    file.delete();
  }
  file.create();
  file.write(arquivo.base64, { encoding: "base64" });

  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(file.uri, {
      mimeType: arquivo.mime_type,
      dialogTitle: "Compartilhar contagem",
    });
  }
  return file.uri;
}
