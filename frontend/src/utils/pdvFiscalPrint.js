import api from "../api";
import { rotaDanfeFiscalVenda, tipoDocumentoFiscalVenda } from "./pdvFiscalStatus";

const PDF_PRINT_DELAY_MS = 1200;
const REVOKE_URL_DELAY_MS = 60000;

function tipoConteudo(response) {
  return String(
    response?.headers?.get?.("content-type") ||
      response?.headers?.["content-type"] ||
      response?.data?.type ||
      "application/pdf",
  ).toLowerCase();
}

function prepararJanela(documento) {
  const janela = globalThis.open?.("", "_blank");
  if (!janela) {
    throw new Error(
      "O navegador bloqueou a janela de impressão. Libere pop-ups e tente novamente.",
    );
  }

  janela.document.title = `Imprimir ${documento}`;
  janela.document.body.textContent = `Preparando ${documento} para impressão...`;
  return janela;
}

function imprimirQuandoCarregar(
  janela,
  { delay = 200, fallbackDelay = null, usarDocumentoPronto = true } = {},
) {
  let disparado = false;
  const imprimir = () => {
    if (disparado || janela.closed) return;
    disparado = true;
    globalThis.setTimeout(() => {
      if (janela.closed) return;
      janela.focus();
      janela.print();
    }, delay);
  };

  janela.addEventListener("afterprint", () => janela.close(), { once: true });
  janela.addEventListener("load", imprimir, { once: true });
  if (usarDocumentoPronto && janela.document?.readyState === "complete") imprimir();
  if (fallbackDelay !== null) globalThis.setTimeout(imprimir, fallbackDelay);
}

async function textoDoDocumento(data) {
  if (typeof data === "string") return data;
  if (typeof data?.text === "function") return data.text();
  return String(data || "");
}

export async function imprimirDocumentoFiscalVenda(venda = {}) {
  const rota = rotaDanfeFiscalVenda(venda);
  const documento = tipoDocumentoFiscalVenda(venda);
  if (!rota) throw new Error(`Não foi possível localizar o DANFE da ${documento}.`);

  const janela = prepararJanela(documento);
  try {
    const response = await api.get(rota, { responseType: "blob" });
    if (tipoConteudo(response).includes("text/html")) {
      const html = await textoDoDocumento(response.data);
      janela.document.open();
      janela.document.write(html);
      janela.document.close();
      imprimirQuandoCarregar(janela);
      return;
    }

    const blob =
      response.data instanceof Blob
        ? response.data
        : new Blob([response.data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    imprimirQuandoCarregar(janela, {
      delay: PDF_PRINT_DELAY_MS,
      fallbackDelay: PDF_PRINT_DELAY_MS,
      usarDocumentoPronto: false,
    });
    janela.location.replace(url);
    globalThis.setTimeout(() => URL.revokeObjectURL(url), REVOKE_URL_DELAY_MS);
  } catch (error) {
    janela.close();
    throw error;
  }
}
