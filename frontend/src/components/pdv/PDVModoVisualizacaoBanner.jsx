import { useState } from "react";
import { AlertCircle, FileText, Pencil, RotateCcw, X } from "lucide-react";
import { useModulos } from "../../contexts/ModulosContext";
import ImprimirCupom from "../ImprimirCupom";
import ActionButton from "../ui/ActionButton";
import {
  getTextoDevolucaoVendaPDV,
  podeAbrirDevolucaoVenda,
} from "../../utils/pdvReturnEligibility";
import ImprimirDocumentoFiscalButton from "./ImprimirDocumentoFiscalButton";
import ModalSelecaoDocumentoFiscal from "./ModalSelecaoDocumentoFiscal";
import ModalDadosVendaFinalizada from "./ModalDadosVendaFinalizada";

export default function PDVModoVisualizacaoBanner({
  ativo,
  vendaAtual,
  temCaixaAberto,
  onAbrirDevolucao,
  onVoltar,
  emitirNotaVendaFinalizada,
  mudarStatusParaAberta,
  habilitarEdicao,
  onRecarregarVenda,
}) {
  const { moduloAtivo, erroCarregamento, carregandoModulos, carregarModulos } = useModulos();
  const moduloFiscalAtivo = moduloAtivo("fiscal");
  const [mostrarSelecaoDocumento, setMostrarSelecaoDocumento] = useState(false);
  const [mostrarDadosFinalizados, setMostrarDadosFinalizados] = useState(false);

  if (!ativo) {
    return null;
  }

  const podeAbrirDevolucao = podeAbrirDevolucaoVenda(vendaAtual);
  const textoDevolucao = getTextoDevolucaoVendaPDV(vendaAtual);
  const notaRejeitada =
    vendaAtual.status === "pago_nf" &&
    String(vendaAtual.nfe_status || "").toLowerCase() === "rejeitada";
  const situacaoVenda =
    textoDevolucao?.situacao ||
    (vendaAtual.status === "finalizada"
      ? "Finalizada"
      : vendaAtual.status === "baixa_parcial"
        ? "com Baixa Parcial"
        : notaRejeitada
          ? "com NF rejeitada"
          : vendaAtual.status === "pago_nf"
            ? "com NF emitida"
            : "Aberta");
  const orientacao =
    textoDevolucao?.orientacao ||
    (notaRejeitada
      ? "Clique em Corrigir erro no aviso da nota para revisar os dados fiscais."
      : vendaAtual.status === "aberta"
        ? "Clique em Editar para modificar."
        : "Reabra a venda para modificar.");

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

            {["finalizada", "baixa_parcial", "pago_nf"].includes(vendaAtual.status) && (
              <ActionButton
                onClick={() => setMostrarDadosFinalizados(true)}
                icon={Pencil}
                intent="edit"
                size="md"
              >
                NSU e observação
              </ActionButton>
            )}

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

      {erroCarregamento && !moduloFiscalAtivo && (
        <div
          role="alert"
          className="border-b border-amber-200 bg-amber-50 px-5 py-3 text-sm text-amber-900"
        >
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2">
            <span>
              Não foi possível confirmar o acesso fiscal desta empresa. A emissão de NF está
              temporariamente indisponível.
            </span>
            <button
              type="button"
              onClick={carregarModulos}
              disabled={carregandoModulos}
              className="rounded-md border border-amber-500 px-3 py-1 font-semibold hover:bg-amber-100 disabled:opacity-50"
            >
              {carregandoModulos ? "Verificando..." : "Tentar novamente"}
            </button>
          </div>
        </div>
      )}

      {moduloFiscalAtivo && mostrarSelecaoDocumento && (
        <ModalSelecaoDocumentoFiscal
          cliente={vendaAtual.cliente}
          cpfAvulso={vendaAtual.nfe_consumidor_cpf}
          onClose={() => setMostrarSelecaoDocumento(false)}
          onEmitir={emitirNotaVendaFinalizada}
          vendaId={vendaAtual.id}
        />
      )}
      {mostrarDadosFinalizados && (
        <ModalDadosVendaFinalizada
          venda={vendaAtual}
          onClose={() => setMostrarDadosFinalizados(false)}
          onUpdated={() => onRecarregarVenda(vendaAtual.id)}
        />
      )}
    </>
  );
}
