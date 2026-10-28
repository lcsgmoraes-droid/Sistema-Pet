import { textoRespostaFiscal } from "./pdvFiscalStatus.js";

export function resumirCancelamentoNota(payload = {}) {
  const recebido = payload || {};
  const dados = recebido.detail && typeof recebido.detail === "object" ? recebido.detail : recebido;
  const statusInformado = String(
    dados.cancelamento_status || dados.nfe_cancelamento_status || "",
  ).toLowerCase();
  const situacao = String(dados.situacao || dados.nfe_status || dados.status || "").toLowerCase();
  const confirmado =
    statusInformado === "confirmado" || (!statusInformado && situacao === "cancelada");
  const solicitado =
    !confirmado &&
    statusInformado !== "recusado" &&
    (statusInformado === "solicitado" || dados.cancelamento_solicitado === true);
  const codigo = textoRespostaFiscal(
    dados.cancelamento_codigo ?? dados.nfe_cancelamento_codigo ?? dados.codigo ?? dados.code,
  );
  const motivo = textoRespostaFiscal(
    dados.cancelamento_motivo ||
      dados.nfe_cancelamento_motivo ||
      dados.motivo ||
      dados.motivo_rejeicao ||
      dados.detail ||
      dados.mensagem ||
      dados.message ||
      (typeof dados === "string" ? dados : ""),
  );
  const detalhe = [codigo ? `Código ${codigo}` : "", motivo].filter(Boolean).join(" — ");
  const mensagem = confirmado
    ? "Nota fiscal cancelada com confirmação do emissor."
    : solicitado
      ? "Cancelamento da nota em andamento. A nota mantém a situação fiscal atual até a confirmação do emissor; atualize a lista para acompanhar."
      : statusInformado === "recusado"
        ? "O cancelamento da nota foi recusado. A nota mantém a situação fiscal atual e precisa de regularização."
        : "O cancelamento da nota ainda não foi confirmado. A nota mantém a situação fiscal atual e precisa de regularização.";
  return {
    status: confirmado ? "confirmado" : solicitado ? "solicitado" : statusInformado || "pendente",
    confirmado,
    solicitado,
    codigo,
    motivo,
    mensagem: [mensagem, detalhe].filter(Boolean).join("\n\n"),
  };
}
