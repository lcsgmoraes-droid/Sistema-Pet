import { formatMoneyBRL } from "../../utils/formatters.js";

export const RESULTADOS_RELATORIO = {
  enviado: "Enviado",
  enviado_com_pendencias: "Enviado com pendências",
  bloqueado: "Lote bloqueado",
  falha_smtp: "Falha no envio de e-mail",
  falhou: "Falha na preparação",
  sem_notas: "Sem notas ou eventos",
  pendencias: "Somente pendências — nenhum XML enviado",
  interrompido: "Processamento interrompido",
};

export function quantidadeRelatorio(valor) {
  if (valor == null || valor === "" || !Number.isFinite(Number(valor))) return "Indisponível";
  return Number(valor).toLocaleString("pt-BR");
}

export function valorRelatorio(valor) {
  if (valor == null || valor === "" || !Number.isFinite(Number(valor))) return "Indisponível";
  return formatMoneyBRL(valor);
}

export function linkNotaRelatorio(documento) {
  const params = new URLSearchParams();
  const busca = String(documento.numero || documento.chave || "").trim();
  const vendaId = String(documento.venda_id || "");
  if (busca) params.set("busca", busca);
  if (/^[1-9]\d*$/.test(vendaId)) {
    params.set("venda_id", vendaId);
    params.set("abrir", "1");
  }
  return `/notas-fiscais/saida${params.size ? `?${params}` : ""}`;
}

export function filtrarDocumentosRelatorio(documentos, busca, situacao) {
  const termo = busca.trim().toLocaleLowerCase("pt-BR");
  return documentos.filter((doc) => {
    if (situacao === "pendentes" && doc.estado !== "pendente") return false;
    if (situacao === "nao_enviadas" && doc.enviada !== false) return false;
    if (situacao === "enviadas" && doc.enviada !== true) return false;
    return (
      !termo ||
      [doc.numero, doc.chave, doc.documento_id, doc.motivo, doc.status_fiscal].some((valor) =>
        String(valor || "")
          .toLocaleLowerCase("pt-BR")
          .includes(termo),
      )
    );
  });
}
