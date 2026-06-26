import { safeArray } from "../../utils/safeArray";

const hojeISO = () => new Date().toISOString().split("T")[0];

export const criarDadosPadraoContaPagar = () => ({
  descricao: "",
  fornecedor_id: null,
  categoria_id: null,
  dre_subcategoria_id: null,
  tipo_despesa_id: null,
  canal: "loja_fisica",
  valor_original: "",
  data_emissao: hojeISO(),
  data_vencimento: hojeISO(),
  documento: "",
  observacoes: "",
  eh_parcelado: false,
  total_parcelas: 1,
  eh_recorrente: false,
  tipo_recorrencia: "mensal",
  intervalo_dias: null,
  data_inicio_recorrencia: null,
  data_fim_recorrencia: null,
  numero_repeticoes: null,
  aplicar_recorrencia_futura: false,
});

export const criarFormCategoriaPadrao = () => ({
  nome: "",
  tipo: "despesa",
  cor: "#ef4444",
  icone: "💸",
  descricao: "",
  ativo: true,
  novasSubcategorias: [],
});

export const normalizarDataContaPagar = (valor, fallback = "") => {
  if (!valor) return fallback;
  return String(valor).split("T")[0];
};

export const normalizarDataOpcionalRecorrencia = (valor) => {
  const dataNormalizada = normalizarDataContaPagar(valor, "");
  return dataNormalizada || null;
};

export const montarDadosEdicaoContaPagar = (conta) => ({
  ...criarDadosPadraoContaPagar(),
  descricao: conta?.descricao || "",
  fornecedor_id: conta?.fornecedor_id || conta?.fornecedor?.id || null,
  categoria_id: conta?.categoria_id || conta?.categoria?.id || null,
  dre_subcategoria_id: conta?.dre_subcategoria_id || null,
  tipo_despesa_id: conta?.tipo_despesa_id || null,
  canal: conta?.canal || "loja_fisica",
  valor_original: String(conta?.valor_original ?? conta?.valores?.original ?? ""),
  data_emissao: normalizarDataContaPagar(conta?.data_emissao || conta?.datas?.emissao, hojeISO()),
  data_vencimento: normalizarDataContaPagar(
    conta?.data_vencimento || conta?.datas?.vencimento,
    hojeISO(),
  ),
  documento: conta?.documento || "",
  observacoes: conta?.observacoes || "",
  eh_recorrente: Boolean(conta?.eh_recorrente),
  tipo_recorrencia: conta?.tipo_recorrencia || "mensal",
  intervalo_dias: conta?.intervalo_dias || null,
  data_inicio_recorrencia: normalizarDataContaPagar(conta?.data_inicio_recorrencia),
  data_fim_recorrencia: normalizarDataContaPagar(conta?.data_fim_recorrencia),
  numero_repeticoes: conta?.numero_repeticoes || null,
  aplicar_recorrencia_futura: false,
});

export const filtrarCategoriasDespesa = (categorias) =>
  safeArray(categorias).filter((categoria) => {
    const tipo = categoria.tipo ? categoria.tipo.toLowerCase() : "";
    const nome = categoria.nome ? categoria.nome.toLowerCase() : "";
    const ehReceita = tipo === "receita" || tipo === "entrada";
    const temReceitaNoNome = nome.includes("receita") || nome.includes("venda");

    return !ehReceita && !temReceitaNoNome;
  });

export const gerarPreviewParcelas = (dados, intervaloParcelas) => {
  if (
    !dados.eh_parcelado ||
    !dados.total_parcelas ||
    !dados.data_vencimento ||
    !dados.valor_original
  ) {
    return [];
  }

  const total = parseFloat(dados.valor_original);
  const numParcelas = parseInt(dados.total_parcelas);
  const valorParcela = total / numParcelas;
  const dataBase = new Date(dados.data_vencimento);
  const parcelas = [];

  for (let i = 0; i < numParcelas; i += 1) {
    const dataVencimento = new Date(dataBase);
    dataVencimento.setDate(dataBase.getDate() + i * intervaloParcelas);

    parcelas.push({
      numero: i + 1,
      valor: i === numParcelas - 1 ? total - valorParcela * (numParcelas - 1) : valorParcela,
      data_vencimento: dataVencimento.toISOString().split("T")[0],
    });
  }

  const somaCalculada = parcelas.reduce((sum, parcela) => sum + parcela.valor, 0);
  const diferenca = total - somaCalculada;
  if (Math.abs(diferenca) > 0.01) {
    parcelas[parcelas.length - 1].valor += diferenca;
  }

  return parcelas;
};

export const montarPayloadContaPagar = (dados, contaEdicao, pertenceRecorrencia) => {
  const payload = {
    ...dados,
    valor_original: parseFloat(dados.valor_original),
    total_parcelas: dados.eh_parcelado ? parseInt(dados.total_parcelas) : 1,
    intervalo_dias:
      dados.eh_recorrente && dados.tipo_recorrencia === "personalizado"
        ? parseInt(dados.intervalo_dias)
        : null,
    numero_repeticoes:
      dados.eh_recorrente && dados.numero_repeticoes ? parseInt(dados.numero_repeticoes) : null,
  };
  const descricaoAnterior = (contaEdicao?.descricao || "").trim();
  const descricaoAtual = (payload.descricao || "").trim();
  const confirmarReplicacaoDescricao =
    Boolean(contaEdicao?.id) &&
    pertenceRecorrencia &&
    descricaoAtual &&
    descricaoAnterior &&
    descricaoAtual !== descricaoAnterior &&
    !payload.aplicar_recorrencia_futura &&
    window.confirm("Deseja aplicar o novo nome aos próximos lançamentos desta recorrência?");
  const recorrenciaPayload = {
    data_inicio_recorrencia:
      normalizarDataOpcionalRecorrencia(payload.data_inicio_recorrencia) || payload.data_vencimento,
    data_fim_recorrencia: normalizarDataOpcionalRecorrencia(payload.data_fim_recorrencia),
  };

  return {
    ...payload,
    aplicar_recorrencia_futura: Boolean(
      payload.aplicar_recorrencia_futura || confirmarReplicacaoDescricao,
    ),
    eh_recorrente: payload.eh_recorrente,
    tipo_recorrencia: payload.eh_recorrente ? payload.tipo_recorrencia : null,
    intervalo_dias:
      payload.eh_recorrente && payload.tipo_recorrencia === "personalizado"
        ? payload.intervalo_dias
        : null,
    data_inicio_recorrencia: payload.eh_recorrente
      ? recorrenciaPayload.data_inicio_recorrencia
      : null,
    data_fim_recorrencia: payload.eh_recorrente ? recorrenciaPayload.data_fim_recorrencia : null,
    numero_repeticoes: payload.eh_recorrente ? payload.numero_repeticoes : null,
  };
};

export const montarPayloadEdicaoContaPagar = (payloadNormalizado) => ({
  descricao: payloadNormalizado.descricao,
  fornecedor_id: payloadNormalizado.fornecedor_id,
  categoria_id: payloadNormalizado.categoria_id,
  dre_subcategoria_id: payloadNormalizado.dre_subcategoria_id,
  tipo_despesa_id: payloadNormalizado.tipo_despesa_id,
  canal: payloadNormalizado.canal,
  valor_original: payloadNormalizado.valor_original,
  data_emissao: payloadNormalizado.data_emissao,
  data_vencimento: payloadNormalizado.data_vencimento,
  documento: payloadNormalizado.documento,
  observacoes: payloadNormalizado.observacoes,
  eh_recorrente: payloadNormalizado.eh_recorrente,
  tipo_recorrencia: payloadNormalizado.eh_recorrente ? payloadNormalizado.tipo_recorrencia : null,
  intervalo_dias:
    payloadNormalizado.eh_recorrente && payloadNormalizado.tipo_recorrencia === "personalizado"
      ? payloadNormalizado.intervalo_dias
      : null,
  data_inicio_recorrencia: payloadNormalizado.eh_recorrente
    ? payloadNormalizado.data_inicio_recorrencia
    : null,
  data_fim_recorrencia: payloadNormalizado.eh_recorrente
    ? payloadNormalizado.data_fim_recorrencia
    : null,
  numero_repeticoes: payloadNormalizado.eh_recorrente ? payloadNormalizado.numero_repeticoes : null,
  aplicar_recorrencia_futura: Boolean(payloadNormalizado.aplicar_recorrencia_futura),
});
