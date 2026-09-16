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
