export const formatarQuantidade = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

export function fimDoMesIso() {
  const data = new Date();
  data.setMonth(data.getMonth() + 1, 0);
  return data.toISOString().split("T")[0];
}

export function inicioDoMesIso(dataBase = new Date()) {
  const data = new Date(dataBase);
  data.setDate(1);
  return data.toISOString().split("T")[0];
}

export function fimDoMesBaseIso(dataBase = new Date()) {
  const data = new Date(dataBase.getFullYear(), dataBase.getMonth() + 1, 0);
  return data.toISOString().split("T")[0];
}

export function hojeIso() {
  return new Date().toISOString().split("T")[0];
}

export function extrairListaProdutos(payload) {
  if (!payload) return [];
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.itens)) return payload.itens;
  if (Array.isArray(payload.produtos)) return payload.produtos;
  if (Array.isArray(payload.data)) return payload.data;
  if (Array.isArray(payload)) return payload;
  return [];
}

export function normalizarNumero(valor) {
  return Number(String(valor || "").replace(",", "."));
}

export function normalizarCodigo(valor) {
  return String(valor || "").replace(/\D/g, "");
}

export function produtoConfereCodigo(produto, termo) {
  const termoLimpo = String(termo || "").trim().toLowerCase();
  const termoDigitos = normalizarCodigo(termo);
  if (!termoLimpo) return false;
  const campos = [
    produto?.codigo,
    produto?.codigo_barras,
    produto?.gtin_ean,
    produto?.gtin_ean_tributario,
  ];
  return campos.some((campo) => {
    const texto = String(campo || "").trim().toLowerCase();
    if (!texto) return false;
    return texto === termoLimpo || (termoDigitos && normalizarCodigo(texto) === termoDigitos);
  });
}

export function formatarData(valor) {
  if (!valor) return "-";
  const data = new Date(`${valor}T00:00:00`);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

export function extrairObservacaoManualTransferencia(valor) {
  const texto = String(valor || "");
  const marcador = "\n\nItens:";
  const indice = texto.indexOf(marcador);
  if (indice >= 0) return texto.slice(0, indice).trim();
  return texto.trim();
}

export function baixarArquivoBlob(blob, nomeArquivo) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const CUPOM_TRANSFERENCIA_WIDTH = 42;

export const COLUNAS_DOCUMENTO_TRANSFERENCIA = [
  { chave: "codigo", label: "Codigo / SKU" },
  { chave: "produto", label: "Descricao" },
  { chave: "quantidade", label: "Quantidade" },
  { chave: "custo_unitario", label: "Custo unitario" },
  { chave: "total", label: "Total do item" },
  { chave: "totais", label: "Totais do acerto" },
];

export const COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO =
  COLUNAS_DOCUMENTO_TRANSFERENCIA.map((coluna) => coluna.chave);

export const COLUNAS_DOCUMENTO_TRANSFERENCIA_RETIRADA = [
  "codigo",
  "produto",
  "quantidade",
];

export const COLUNAS_DOCUMENTO_TRANSFERENCIA_FINANCEIRAS = [
  "custo_unitario",
  "total",
  "totais",
];

export const normalizarColunasDocumentoTransferencia = (
  colunas = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
) => {
  const candidatas = Array.isArray(colunas)
    ? colunas
    : String(colunas || "").split(",");

  const selecionadas = new Set(
    candidatas
      .map((coluna) => String(coluna || "").trim().toLowerCase())
      .filter(Boolean),
  );

  return COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO.filter((coluna) =>
    selecionadas.has(coluna),
  );
};

export const documentoTransferenciaTemValores = (colunas = []) =>
  normalizarColunasDocumentoTransferencia(colunas).some((coluna) =>
    COLUNAS_DOCUMENTO_TRANSFERENCIA_FINANCEIRAS.includes(coluna),
  );

export const montarParametrosDocumentoTransferencia = (colunas = []) => {
  const normalizadas = normalizarColunasDocumentoTransferencia(colunas);

  return {
    mostrar_codigo: normalizadas.includes("codigo"),
    mostrar_descricao: normalizadas.includes("produto"),
    mostrar_quantidade: normalizadas.includes("quantidade"),
    mostrar_custo_unitario: normalizadas.includes("custo_unitario"),
    mostrar_total_item: normalizadas.includes("total"),
    mostrar_totais: normalizadas.includes("totais"),
  };
};

function textoCupom(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\x20-\x7E]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cortarCupom(valor, max = CUPOM_TRANSFERENCIA_WIDTH) {
  const limpo = textoCupom(valor);
  return limpo.length > max ? `${limpo.slice(0, max - 3)}...` : limpo;
}

function centralizarCupom(valor, width = CUPOM_TRANSFERENCIA_WIDTH) {
  const texto = cortarCupom(valor, width);
  const total = Math.max(0, width - texto.length);
  const esquerda = Math.floor(total / 2);
  return `${" ".repeat(esquerda)}${texto}${" ".repeat(total - esquerda)}`;
}

function parCupom(label, valor, width = CUPOM_TRANSFERENCIA_WIDTH) {
  const direita = cortarCupom(valor, Math.max(8, Math.floor(width / 2)));
  const maxEsquerda = Math.max(0, width - direita.length - 1);
  const esquerda = cortarCupom(label, maxEsquerda);
  return `${esquerda}${" ".repeat(Math.max(1, width - esquerda.length - direita.length))}${direita}`;
}

function quebrarCupom(valor, width = CUPOM_TRANSFERENCIA_WIDTH) {
  const palavras = textoCupom(valor).split(" ");
  const linhas = [];
  let atual = "";

  for (const palavra of palavras) {
    if (!palavra) continue;
    const proposta = atual ? `${atual} ${palavra}` : palavra;
    if (proposta.length <= width) {
      atual = proposta;
      continue;
    }

    if (atual) linhas.push(atual);
    if (palavra.length <= width) {
      atual = palavra;
      continue;
    }

    for (let i = 0; i < palavra.length; i += width) {
      linhas.push(palavra.slice(i, i + width));
    }
    atual = "";
  }

  if (atual) linhas.push(atual);
  return linhas.length ? linhas : [""];
}

function formatarMoedaCupom(valor) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(valor || 0);
}

export function montarCupomTransferencia(
  registro,
  colunasDocumento = COLUNAS_DOCUMENTO_TRANSFERENCIA_COMPLETO,
) {
  const colunas = normalizarColunasDocumentoTransferencia(colunasDocumento);
  const mostrarCodigo = colunas.includes("codigo");
  const mostrarProduto = colunas.includes("produto");
  const mostrarQuantidade = colunas.includes("quantidade");
  const mostrarCustoUnitario = colunas.includes("custo_unitario");
  const mostrarTotalItem = colunas.includes("total");
  const mostrarTotais = colunas.includes("totais");
  const documento = registro.documento || `TRP-${registro.conta_receber_id}`;
  const itens = Array.isArray(registro.itens) ? registro.itens : [];
  const linhas = [
    centralizarCupom("PET SHOP PRO"),
    centralizarCupom("TRANSFERENCIA PARCEIRO"),
    centralizarCupom("COMPROVANTE DE RETIRADA"),
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    cortarCupom(`Documento: ${documento}`),
    cortarCupom(`Pessoa: ${registro.parceiro_nome || "-"}`),
    cortarCupom(`Emissao: ${formatarData(registro.data_emissao)}`),
    cortarCupom(`Vencimento: ${formatarData(registro.data_vencimento)}`),
    cortarCupom(`Status: ${registro.status_label || registro.status || "-"}`),
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    "ITENS",
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
  ];

  for (const item of itens) {
    if (mostrarProduto) {
      linhas.push(...quebrarCupom(item.produto_nome || "Item"));
    }
    if (mostrarCodigo && mostrarQuantidade) {
      linhas.push(
        parCupom(
          `Cod ${item.codigo || item.produto_id || "-"}`,
          `Qtd ${formatarQuantidade(item.quantidade)}`,
        ),
      );
    } else if (mostrarCodigo) {
      linhas.push(cortarCupom(`Cod ${item.codigo || item.produto_id || "-"}`));
    } else if (mostrarQuantidade) {
      linhas.push(cortarCupom(`Qtd ${formatarQuantidade(item.quantidade)}`));
    }
    if (mostrarCustoUnitario) {
      linhas.push(parCupom("Custo un.", formatarMoedaCupom(item.custo_unitario)));
    }
    if (mostrarTotalItem) {
      linhas.push(parCupom("Total", formatarMoedaCupom(item.valor_total)));
    }
    linhas.push("");
  }

  if (mostrarTotais) {
    linhas.push(
      "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
      parCupom("Valor", formatarMoedaCupom(registro.valor_original)),
      parCupom("Recebido", formatarMoedaCupom(registro.valor_recebido)),
      parCupom("Saldo", formatarMoedaCupom(registro.saldo_aberto)),
      "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    );
  } else {
    linhas.push("-".repeat(CUPOM_TRANSFERENCIA_WIDTH));
  }

  if (registro.observacoes) {
    linhas.push(
      "OBS:",
      ...quebrarCupom(registro.observacoes),
      "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    );
  }

  linhas.push(
    "RETIRADO POR:",
    "",
    "Nome: ________________________________",
    "Doc.: ________________________________",
    "",
    "Assinatura:",
    "",
    "______________________________________",
    "",
    "Data: ____/____/________",
    "-".repeat(CUPOM_TRANSFERENCIA_WIDTH),
    centralizarCupom("Documento para controle interno"),
  );

  return linhas.join("\n");
}
