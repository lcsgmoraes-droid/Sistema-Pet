import api from "../api";
import { confirmarCorePet } from "../services/corepetDialog";

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

  const pendencias = [...(validacao.bloqueios || []), ...(validacao.correcoes || [])];
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
  const mensagem = [
    "A nota ainda nao foi criada porque existem pendencias fiscais.",
    "",
    formatarPendenciasFiscais(validacao),
  ].join("\n");
  const error = new Error(mensagem);
  error.validacaoFiscal = validacao;
  return error;
}

function resumoIntNFe(resumo) {
  const linhas = [
    `${resumo.modelo === 55 ? "NF-e" : "NFC-e"} em ${resumo.ambiente}, série ${resumo.serie}`,
    `Total: R$ ${Number(resumo.total || 0)
      .toFixed(2)
      .replace(".", ",")}`,
    `Itens: ${resumo.itens?.length || 0}`,
  ];
  const destinatario = resumo.destinatario?.razaoSocial;
  if (destinatario) linhas.push(`Destinatário: ${destinatario}`);
  if (resumo.ambiente_codigo === 1) {
    linhas.unshift("ATENÇÃO: esta confirmação transmitirá uma nota fiscal real.", "");
  }
  linhas.push("", "Confirmar a transmissão destes dados?");
  return linhas.join("\n");
}

function aguardar(ms) {
  return new Promise((resolve) => globalThis.setTimeout(resolve, ms));
}

async function acompanharIntNFe(vendaId, initial) {
  let current = initial;
  for (let attempt = 0; current?.processando && attempt < 8; attempt += 1) {
    await aguardar(2500);
    const response = await api.get(`/nfe/vendas/${vendaId}/status`);
    current = response.data;
  }
  return current;
}

function erroRejeicaoIntNFe(vendaId, data) {
  const error = new Error(
    data?.motivo_rejeicao ||
      data?.codigo_erro ||
      `A nota terminou com a situação: ${data?.situacao || "não autorizada"}.`,
  );
  error.recuperacaoNFe = {
    vendaId,
    codigoErro: data?.codigo_erro,
    motivo: data?.motivo_rejeicao,
    ambienteCodigo: data?.ambiente_codigo,
  };
  return error;
}

export async function corrigirEReemitirNota(vendaId) {
  const { data: initial } = await api.post(`/nfe/vendas/${vendaId}/corrigir-reemitir`);
  const data = initial?.provedor === "intnfe" ? await acompanharIntNFe(vendaId, initial) : initial;
  if (data?.provedor === "intnfe" && !data.success && !data.processando) {
    throw erroRejeicaoIntNFe(vendaId, data);
  }
  return data;
}

export async function emitirNotaFiscalAssistida({
  vendaId,
  tipoNota = "nfce",
  confirmar = confirmarCorePet,
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
      "Autorizar correcao fiscal e emitir a nota agora?",
    ].join("\n");
    autorizarCorrecoes = await confirmar(mensagem);
    if (!autorizarCorrecoes) {
      return { cancelado: true, validacao };
    }
  }

  if (validacao?.provedor === "intnfe" && validacao?.resumo_emissao) {
    const confirmed = await confirmar(resumoIntNFe(validacao.resumo_emissao));
    if (!confirmed) return { cancelado: true, validacao };
  }

  const { data: initialData } = await api.post("/nfe/emitir", {
    venda_id: vendaId,
    tipo_nota: tipoNota,
    transmitir: true,
    autorizar_correcoes_fiscais: autorizarCorrecoes,
  });
  const data =
    initialData?.provedor === "intnfe" ? await acompanharIntNFe(vendaId, initialData) : initialData;
  if (data?.provedor === "intnfe" && !data.success && !data.processando) {
    throw erroRejeicaoIntNFe(vendaId, data);
  }

  return { data, validacao, correcoesAutorizadas: autorizarCorrecoes };
}
