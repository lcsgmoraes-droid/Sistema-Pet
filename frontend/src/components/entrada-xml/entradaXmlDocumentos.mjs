function cabecalho(response, nome) {
  return response?.headers?.get?.(nome) || response?.headers?.[nome];
}

export function nomeDocumentoEntrada(nota, formato) {
  const numero = String(nota?.numero_nota || "nota").replace(/\D/g, "") || "nota";
  const serie = String(nota?.serie || "1").replace(/\D/g, "") || "1";
  const extensao = formato === "pdf" ? "pdf" : "xml";
  const prefixo = extensao === "pdf" ? "danfe" : "nfe";
  return `${prefixo}_${numero}_serie_${serie}.${extensao}`;
}

export function nomeDocumentoDaResposta(response, fallback) {
  const disposition = String(cabecalho(response, "content-disposition") || "");
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return match?.[1]?.trim() || fallback;
}

export function salvarDocumentoEntrada(response, nota, formato) {
  const tipo = formato === "pdf" ? "application/pdf" : "application/xml";
  const blob =
    response.data instanceof Blob ? response.data : new Blob([response.data], { type: tipo });
  const nome = nomeDocumentoDaResposta(response, nomeDocumentoEntrada(nota, formato));
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function mensagemErroDocumentoEntrada(error, fallback) {
  let dados = error?.response?.data;
  if (dados instanceof Blob) {
    try {
      dados = JSON.parse(await dados.text());
    } catch {
      dados = null;
    }
  }
  return typeof dados?.detail === "string" ? dados.detail : fallback;
}
