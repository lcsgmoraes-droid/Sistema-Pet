import { parseNumero } from "./shared";

export const FORM_PROCEDIMENTO_INICIAL = {
  nome: "",
  descricao: "",
  categoria: "",
  duracao: "",
  preco: "",
  requer_anestesia: false,
  observacoes: "",
  insumos: [],
};

export function mapProcedimentoParaForm(item) {
  return {
    nome: item?.nome || "",
    descricao: item?.descricao || "",
    categoria: item?.categoria || "",
    duracao: item?.duracao_minutos ?? item?.duracao_estimada_min ?? "",
    preco: item?.valor_padrao ?? "",
    requer_anestesia: Boolean(item?.requer_anestesia),
    observacoes: item?.observacoes || "",
    insumos: Array.isArray(item?.insumos)
      ? item.insumos.map((insumo) => ({
          produto_id: insumo.produto_id ? String(insumo.produto_id) : "",
          quantidade: insumo.quantidade ?? "1",
          baixar_estoque: insumo.baixar_estoque !== false,
        }))
      : [],
  };
}

export function buildProcedimentoPayload(form) {
  return {
    nome: form.nome.trim(),
    descricao: form.descricao.trim() || undefined,
    categoria: form.categoria.trim() || undefined,
    valor_padrao: parseNumero(form.preco),
    duracao_minutos: form.duracao ? parseInt(form.duracao, 10) : undefined,
    requer_anestesia: Boolean(form.requer_anestesia),
    observacoes: form.observacoes.trim() || undefined,
    insumos: form.insumos
      .map((item) => ({
        produto_id: item.produto_id ? Number(item.produto_id) : null,
        quantidade: parseNumero(item.quantidade),
        baixar_estoque: item.baixar_estoque !== false,
      }))
      .filter((item) => item.produto_id && item.quantidade > 0),
  };
}
