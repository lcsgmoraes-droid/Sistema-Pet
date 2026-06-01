import api from "../api";

function linhaProduto(item) {
  const partes = [];
  if (item?.produto_nome) partes.push(item.produto_nome);
  if (item?.sku) partes.push(`SKU ${item.sku}`);
  return partes.join(" - ") || item?.campo || "Item fiscal";
}

export function formatarPendenciasFiscais(validacao) {
  const bloqueios = validacao?.bloqueios || [];
  const correcoes = validacao?.correcoes || [];
  const linhas = [];

  if (bloqueios.length) {
    linhas.push("Pendencias que precisam ser corrigidas manualmente:");
    bloqueios.forEach((item) => {
      linhas.push(`- ${linhaProduto(item)}: ${item.mensagem || item.campo}`);
    });
  }

  if (correcoes.length) {
    if (linhas.length) linhas.push("");
    linhas.push("Correcoes que o sistema pode preencher com sua autorizacao:");
    correcoes.forEach((item) => {
      linhas.push(
        `- ${linhaProduto(item)}: ${item.campo} ${item.valor_atual || "vazio"} -> ${item.valor_sugerido}. ${item.motivo || ""}`.trim(),
      );
    });
  }

  return linhas.join("\n");
}

export function extrairMensagemNFe(error) {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === "object") {
    const validacao = detail.validacao || detail;
    const mensagemFiscal = formatarPendenciasFiscais(validacao);
    if (mensagemFiscal) {
      return `${detail.mensagem || "Existem pendencias fiscais antes de emitir a nota."}\n\n${mensagemFiscal}`;
    }
    return detail.mensagem || detail.erro || "Erro ao emitir nota fiscal.";
  }
  return detail || error?.message || "Erro ao emitir nota fiscal.";
}

export function extrairAcaoCorrecaoFiscal(error) {
  const detail = error?.response?.data?.detail;
  const validacao = error?.validacaoFiscal || detail?.validacao || detail;

  if (!validacao || typeof validacao !== "object") return null;

  const pendencias = [
    ...(validacao.bloqueios || []),
    ...(validacao.correcoes || []),
  ];
  const pendenciaProduto = pendencias.find((item) => item?.produto_id);

  if (!pendenciaProduto) return null;

  return {
    produtoId: pendenciaProduto.produto_id,
    produtoNome: pendenciaProduto.produto_nome,
    campo: pendenciaProduto.campo,
    url: `/produtos/${pendenciaProduto.produto_id}/editar?aba=5`,
  };
}

function erroComValidacaoFiscal(validacao) {
  const error = new Error(formatarPendenciasFiscais(validacao));
  error.validacaoFiscal = validacao;
  return error;
}

export async function emitirNotaFiscalAssistida({
  vendaId,
  tipoNota = "nfce",
  confirmar = window.confirm,
} = {}) {
  const { data: validacao } = await api.post("/nfe/prevalidar", {
    venda_id: vendaId,
    tipo_nota: tipoNota,
  });

  const bloqueios = validacao?.bloqueios || [];
  const correcoes = validacao?.correcoes || [];
  if (bloqueios.length) {
    throw erroComValidacaoFiscal(validacao);
  }

  let autorizarCorrecoes = false;
  if (correcoes.length) {
    const mensagem = [
      "O sistema encontrou dados fiscais que pode corrigir automaticamente.",
      "",
      formatarPendenciasFiscais(validacao),
      "",
      "Autorizar correcao e emitir a nota agora?",
    ].join("\n");
    autorizarCorrecoes = confirmar(mensagem);
    if (!autorizarCorrecoes) {
      return { cancelado: true, validacao };
    }
  }

  const { data } = await api.post("/nfe/emitir", {
    venda_id: vendaId,
    tipo_nota: tipoNota,
    transmitir: true,
    autorizar_correcoes_fiscais: autorizarCorrecoes,
  });

  return { data, validacao, correcoesAutorizadas: autorizarCorrecoes };
}
