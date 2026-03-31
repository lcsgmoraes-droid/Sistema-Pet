import {
  Bell,
  Bot,
  CreditCard,
  Save,
  Search,
  ShoppingCart,
  Star,
  Trash2,
  Wallet,
  X,
} from "lucide-react";

import MenuCaixa from "../MenuCaixa";

export default function PDVHeaderBar({
  destaqueAbrirCaixa,
  destaqueVenda,
  caixaGuiaClasses,
  iniciarTour,
  searchVendaQuery,
  onSearchVendaQueryChange,
  onBuscarVenda,
  vendaAtual,
  pendenciasCount,
  opportunitiesCount,
  painelAssistenteAberto,
  mensagensAssistenteLength,
  onAbrirPendenciasEstoque,
  onAbrirOportunidades,
  onToggleAssistente,
  menuCaixaKey,
  onAbrirCaixa,
  onNavigateMeusCaixas,
  modoVisualizacao,
  loading,
  temCaixaAberto,
  onCancelarEdicao,
  onExcluirVenda,
  onSalvarVenda,
  onAbrirModalPagamento,
}) {
  return (
    <div className="bg-white border-b px-6 py-4">
      {(destaqueAbrirCaixa || destaqueVenda) && (
        <div className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-amber-900 text-sm">
          {destaqueAbrirCaixa
            ? "Etapa da introducao guiada: abra o caixa para liberar salvamento e finalizacao de vendas."
            : "Etapa da introducao guiada: use esta tela para concluir a venda e validar o fluxo operacional."}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <ShoppingCart className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Ponto de Venda</h1>
            <p className="text-sm text-gray-500">
              {new Date().toLocaleDateString("pt-BR", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
          <button
            onClick={iniciarTour}
            title="Ver tour guiado do PDV"
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="hidden sm:inline text-xs">Tour</span>
          </button>

          <div className="flex items-center gap-2 ml-6">
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar venda (Ex: 0011)"
                value={searchVendaQuery}
                onChange={(e) => onSearchVendaQueryChange(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter" && searchVendaQuery.trim()) {
                    onBuscarVenda();
                  }
                }}
                className="pl-10 pr-4 py-2 w-64 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
              />
              <Search className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" />
            </div>
            <button
              onClick={onBuscarVenda}
              disabled={!searchVendaQuery.trim() || loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Buscar
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {vendaAtual.cliente && (
            <button
              onClick={onAbrirPendenciasEstoque}
              className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-orange-50 border-2 border-orange-400 rounded-lg transition-colors relative"
              title="Lista de espera - Produtos sem estoque"
            >
              <Bell className="w-5 h-5 text-orange-500" />
              {pendenciasCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  {pendenciasCount}
                </span>
              )}
            </button>
          )}

          {vendaAtual.cliente && (
            <button
              onClick={onAbrirOportunidades}
              className="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-yellow-50 border-2 border-yellow-400 rounded-lg transition-colors"
              title="Ver oportunidades de venda"
            >
              <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
              {opportunitiesCount > 0 && (
                <span className="font-semibold text-yellow-600">
                  {Math.min(opportunitiesCount, 6)}
                </span>
              )}
            </button>
          )}

          {vendaAtual.cliente && (
            <button
              onClick={onToggleAssistente}
              className={`flex items-center space-x-1 px-3 py-2 rounded-lg border-2 transition-colors ${
                painelAssistenteAberto
                  ? "bg-indigo-100 border-indigo-500 text-indigo-700"
                  : "bg-white hover:bg-indigo-50 border-indigo-300 text-indigo-600"
              }`}
              title="Assistente IA do cliente"
            >
              <Bot className="w-5 h-5" />
              {mensagensAssistenteLength > 1 && !painelAssistenteAberto && (
                <span className="w-2 h-2 bg-indigo-500 rounded-full" />
              )}
            </button>
          )}

          <div
            className={
              destaqueAbrirCaixa
                ? `rounded-lg ${caixaGuiaClasses.action}`
                : ""
            }
          >
            <MenuCaixa key={menuCaixaKey} onAbrirCaixa={onAbrirCaixa} />
          </div>

          <button
            onClick={onNavigateMeusCaixas}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors"
            title="Ver histórico de caixas"
          >
            <Wallet className="w-5 h-5" />
            <span>Meus Caixas</span>
          </button>

          {!modoVisualizacao && vendaAtual.id && (
            <>
              <button
                onClick={onCancelarEdicao}
                disabled={loading}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <X className="w-5 h-5" />
                <span>Cancelar Edição</span>
              </button>
              <button
                onClick={onExcluirVenda}
                disabled={loading}
                className="flex items-center space-x-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Trash2 className="w-5 h-5" />
                <span>Excluir</span>
              </button>
            </>
          )}

          <button
            onClick={onSalvarVenda}
            disabled={loading || modoVisualizacao || !temCaixaAberto}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              !temCaixaAberto
                ? "🔒 Caixa fechado - Abra o caixa para salvar vendas"
                : "Salvar venda atual"
            }
          >
            <Save className="w-5 h-5" />
            <span>Salvar</span>
            {!temCaixaAberto && <span className="text-xs">🔒</span>}
          </button>
          <button
            onClick={onAbrirModalPagamento}
            disabled={
              loading ||
              vendaAtual.status === "finalizada" ||
              vendaAtual.status === "pago_nf" ||
              !temCaixaAberto
            }
            className="flex items-center space-x-2 px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
    </div>
  );
}
