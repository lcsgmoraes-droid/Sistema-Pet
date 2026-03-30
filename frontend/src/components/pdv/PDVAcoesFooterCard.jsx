import { AlertCircle, CreditCard, Save, X } from "lucide-react";

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
    <div id="tour-pdv-resumo" className="bg-white rounded-lg shadow-sm border p-6">
      {!temCaixaAberto && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-center">
          <div className="flex items-center space-x-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm font-medium">
              🔒 Caixa fechado - Use o botão "Abrir Caixa" no topo da página
              para continuar
            </span>
          </div>
        </div>
      )}
      <div className="flex items-center justify-end gap-3">
        {!vendaId && (
          <button
            onClick={onNovaVenda}
            disabled={loading || modoVisualizacao}
            className="flex items-center space-x-2 px-4 py-3 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-red-200"
            title="Descartar venda atual e começar uma nova"
          >
            <X className="w-5 h-5" />
            <span className="font-medium">Nova Venda</span>
          </button>
        )}

        <button
          onClick={onSalvarVenda}
          disabled={loading || modoVisualizacao || !temCaixaAberto}
          className="flex items-center space-x-2 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title={
            !temCaixaAberto
              ? "🔒 Caixa fechado - Abra o caixa para salvar vendas"
              : "Salvar venda atual"
          }
        >
          <Save className="w-5 h-5" />
          <span className="font-medium">Salvar Venda</span>
          {!temCaixaAberto && <span className="text-xs">🔒</span>}
        </button>

        <button
          onClick={onAbrirModalPagamento}
          disabled={
            loading ||
            statusVenda === "finalizada" ||
            statusVenda === "pago_nf" ||
            !temCaixaAberto
          }
          className="flex items-center space-x-2 px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          title={
            !temCaixaAberto
              ? "🔒 Caixa fechado - Abra o caixa para registrar recebimentos"
              : "Registrar pagamento da venda"
          }
        >
          <CreditCard className="w-5 h-5" />
          <span>Registrar Recebimento</span>
          {!temCaixaAberto && <span className="text-xs">🔒</span>}
        </button>
      </div>
    </div>
  );
}
