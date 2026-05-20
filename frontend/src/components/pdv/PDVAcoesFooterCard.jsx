import { AlertCircle, CreditCard, Save, X } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import Panel from "../ui/Panel";

export default function PDVAcoesFooterCard({
  itensCount,
  loading,
  modoVisualizacao,
  onAbrirModalPagamento,
  onNovaVenda,
  onSalvarVenda,
  statusVenda,
  temCaixaAberto,
  vendaId,
}) {
  if (itensCount === 0) {
    return null;
  }

  return (
    <Panel id="tour-pdv-resumo" padding="lg">
      {!temCaixaAberto && (
        <div className="mb-4 flex items-center justify-center rounded-lg border border-red-200 bg-red-50 p-3">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="h-5 w-5" />
            <span className="text-sm font-medium">
              Caixa fechado - Use o botao Abrir Caixa no topo da pagina para continuar
            </span>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
        {!vendaId && (
          <ActionButton
            onClick={onNovaVenda}
            disabled={loading || modoVisualizacao}
            icon={X}
            intent="delete"
            tone="soft"
            size="md"
            className="w-full sm:w-auto"
            title="Descartar venda atual e comecar uma nova"
          >
            <span className="font-medium">Nova Venda</span>
          </ActionButton>
        )}

        <ActionButton
          onClick={onSalvarVenda}
          disabled={loading || modoVisualizacao || !temCaixaAberto}
          icon={Save}
          intent="edit"
          size="md"
          className="w-full sm:w-auto"
          title={
            !temCaixaAberto
              ? "Caixa fechado - Abra o caixa para salvar vendas"
              : "Salvar venda atual"
          }
        >
          <span className="font-medium">Salvar Venda</span>
        </ActionButton>

        <ActionButton
          onClick={onAbrirModalPagamento}
          disabled={
            loading ||
            statusVenda === "finalizada" ||
            statusVenda === "pago_nf" ||
            !temCaixaAberto
          }
          icon={CreditCard}
          intent="create"
          size="md"
          className="w-full sm:w-auto"
          title={
            !temCaixaAberto
              ? "Caixa fechado - Abra o caixa para registrar recebimentos"
              : "Registrar pagamento da venda"
          }
        >
          <span>Registrar Recebimento</span>
        </ActionButton>
      </div>
    </Panel>
  );
}
