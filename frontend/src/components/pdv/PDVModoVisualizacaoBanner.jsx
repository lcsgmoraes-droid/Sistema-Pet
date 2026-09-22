import { useState } from "react";
import { AlertCircle, FileText, RotateCcw, X } from "lucide-react";
import { useModulos } from "../../contexts/ModulosContext";
import ImprimirCupom from "../ImprimirCupom";
import ActionButton from "../ui/ActionButton";
import { podeAbrirDevolucaoVenda } from "../../utils/pdvReturnEligibility";
import ImprimirDocumentoFiscalButton from "./ImprimirDocumentoFiscalButton";
import ModalSelecaoDocumentoFiscal from "./ModalSelecaoDocumentoFiscal";

export default function PDVModoVisualizacaoBanner({
  ativo,
  vendaAtual,
  temCaixaAberto,
  onAbrirDevolucao,
  onVoltar,
  emitirNotaVendaFinalizada,
  mudarStatusParaAberta,
  habilitarEdicao,
}) {
  const { moduloAtivo } = useModulos();
  const moduloFiscalAtivo = moduloAtivo("fiscal");
  const [mostrarSelecaoDocumento, setMostrarSelecaoDocumento] = useState(false);

  if (!ativo) {
    return null;
  }

  const podeAbrirDevolucao = podeAbrirDevolucaoVenda(vendaAtual);
  const notaRejeitada =
    vendaAtual.status === "pago_nf" &&
    String(vendaAtual.nfe_status || "").toLowerCase() === "rejeitada";
  const situacaoVenda =
    vendaAtual.status === "finalizada"
      ? "Finalizada"
      : vendaAtual.status === "baixa_parcial"
        ? "com Baixa Parcial"
        : notaRejeitada
          ? "com NF rejeitada"
          : vendaAtual.status === "pago_nf"
            ? "com NF emitida"
            : "Aberta";
  const orientacao = notaRejeitada
    ? "Libere a tentativa rejeitada na Central NF para escolher outro modelo."
    : vendaAtual.status === "aberta"
      ? "Clique em Editar para modificar."
      : "Reabra a venda para modificar.";

  return (
    <>
      <div className="border-b border-yellow-200 bg-yellow-50 px-5 py-2.5">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2.5">
          <div className="flex items-center space-x-2 text-sm text-yellow-800">
            <AlertCircle className="h-4 w-4" />
            <span className="font-semibold">Modo Visualização - Venda {situacaoVenda}</span>
            <span className="text-xs">({orientacao})</span>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ImprimirCupom venda={vendaAtual} size="md" className="min-w-[132px]" />
            <ImprimirDocumentoFiscalButton venda={vendaAtual} size="md" className="min-w-[132px]" />

            {podeAbrirDevolucao && (
              <ActionButton
                onClick={onAbrirDevolucao}
                disabled={!temCaixaAberto}
                icon={RotateCcw}
                intent="warning"
                size="md"
                className="min-w-[118px]"
                title={
                  temCaixaAberto
                    ? "Abrir devolucao desta venda"
                    : "Abra o caixa para registrar devolucao"
                }
              >
                Devolucao
              </ActionButton>
            )}

            <ActionButton
              onClick={onVoltar}
              icon={X}
              intent="neutral"
              size="md"
              className="min-w-[96px]"
            >
              Voltar
            </ActionButton>

            {moduloFiscalAtivo &&
              (vendaAtual.status === "finalizada" || vendaAtual.status === "baixa_parcial") && (
                <ActionButton
                  onClick={() => setMostrarSelecaoDocumento(true)}
                  icon={FileText}
                  intent="create"
                  size="md"
                  className="min-w-[116px]"
                >
                  Emitir NF
                </ActionButton>
              )}

            {(vendaAtual.status === "finalizada" || vendaAtual.status === "baixa_parcial") && (
              <ActionButton
                onClick={mudarStatusParaAberta}
                icon={AlertCircle}
                intent="warning"
                size="md"
                className="min-w-[126px]"
              >
                Reabrir Venda
              </ActionButton>
            )}

            {vendaAtual.status === "aberta" && (
              <ActionButton
                onClick={habilitarEdicao}
                intent="edit"
                size="md"
                className="min-w-[96px]"
              >
                Editar
              </ActionButton>
            )}
          </div>
        </div>
      </div>

      {moduloFiscalAtivo && mostrarSelecaoDocumento && (
        <ModalSelecaoDocumentoFiscal
          cliente={vendaAtual.cliente}
          onClose={() => setMostrarSelecaoDocumento(false)}
          onEmitir={emitirNotaVendaFinalizada}
          vendaId={vendaAtual.id}
        />
      )}
    </>
  );
}
