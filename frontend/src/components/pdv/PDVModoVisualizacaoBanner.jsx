import { AlertCircle, FileText, RotateCcw, X } from "lucide-react";
import ImprimirCupom from "../ImprimirCupom";
import ActionButton from "../ui/ActionButton";
import { podeAbrirDevolucaoVenda } from "../../utils/pdvReturnEligibility";

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
  if (!ativo) {
    return null;
  }

  const podeAbrirDevolucao = podeAbrirDevolucaoVenda(vendaAtual);

  return (
    <div className="border-b border-yellow-200 bg-yellow-50 px-5 py-2.5">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center space-x-2 text-sm text-yellow-800">
          <AlertCircle className="h-4 w-4" />
          <span className="font-semibold">
            Modo Visualização - Venda{" "}
            {vendaAtual.status === "finalizada"
              ? "Finalizada"
              : vendaAtual.status === "baixa_parcial"
                ? "com Baixa Parcial"
                : "Aberta"}
          </span>
          <span className="text-xs">(Clique em Editar para modificar)</span>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <ImprimirCupom venda={vendaAtual} size="md" className="min-w-[132px]" />

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

          {(vendaAtual.status === "finalizada" || vendaAtual.status === "baixa_parcial") && (
            <ActionButton
              onClick={emitirNotaVendaFinalizada}
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
  );
}
