export function metadadosDownloadDanfe(response, numero) {
  const headerContentType =
    response?.headers?.get?.("content-type") || response?.headers?.["content-type"];
  const contentType = String(
    headerContentType || response?.data?.type || "application/pdf",
  ).toLowerCase();
  const ehHtml = contentType.includes("text/html");

  return {
    nome: `danfe_${numero}.${ehHtml ? "html" : "pdf"}`,
    tipo: ehHtml ? "text/html;charset=utf-8" : "application/pdf",
  };
}

export async function mensagemDocumento(error, padrao) {
  let dados = error?.response?.data;
  if (dados instanceof Blob) {
    try {
      dados = JSON.parse(await dados.text());
    } catch {
      dados = null;
    }
  }

  const mensagem = [dados?.detail, dados?.detail?.mensagem, dados?.message].find(
    (valor) => typeof valor === "string" && valor.trim(),
  );
  const texto = mensagem?.trim() || padrao;
  const referencia = dados?.request_id;
  return typeof referencia === "string" && /^[a-zA-Z0-9_-]{1,100}$/.test(referencia)
    ? `${texto}\nReferência para suporte: ${referencia}`
    : texto;
}
