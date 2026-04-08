import {
  Bell,
  Bot,
  CreditCard,
  Lock,
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
  const actionBase =
    "inline-flex h-14 items-center justify-center gap-2 rounded-2xl border border-transparent px-5 text-sm font-semibold shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm";
  const iconActionBase =
    "relative inline-flex h-14 w-14 items-center justify-center rounded-2xl border bg-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md";

  const secondaryAction = `${actionBase} border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-slate-100`;
  const successAction = `${actionBase} bg-emerald-600 text-white hover:bg-emerald-700`;
  const primaryAction = `${actionBase} bg-blue-600 text-white hover:bg-blue-700`;
  const accentAction = `${actionBase} border-violet-200 bg-violet-50 text-violet-700 hover:border-violet-300 hover:bg-violet-100`;
  const destructiveAction = `${actionBase} border-red-200 bg-red-50 text-red-700 hover:border-red-300 hover:bg-red-100`;

  return (
    <div className="border-b bg-white px-6 py-5">
      {(destaqueAbrirCaixa || destaqueVenda) && (
        <div className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {destaqueAbrirCaixa
            ? "Etapa da introducao guiada: abra o caixa para liberar salvamento e finalizacao de vendas."
            : "Etapa da introducao guiada: use esta tela para concluir a venda e validar o fluxo operacional."}
        </div>
      )}

      <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 shadow-sm">
              <ShoppingCart className="h-8 w-8" />
            </div>

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
              className="inline-flex h-10 items-center gap-1 rounded-xl px-3 text-sm text-gray-400 transition-colors hover:bg-blue-50 hover:text-blue-600"
            >
              <svg
                className="h-4 w-4"
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
              <span className="hidden text-xs sm:inline">Tour</span>
            </button>
          </div>

          <div className="flex w-full max-w-xl items-center gap-3">
            <div className="relative flex-1">
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
                className="h-14 w-full rounded-2xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm text-slate-700 shadow-sm transition-all placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-100"
              />
              <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
            </div>
            <button
              onClick={onBuscarVenda}
              disabled={!searchVendaQuery.trim() || loading}
              className={`${primaryAction} min-w-[108px]`}
            >
              Buscar
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 xl:max-w-[54rem] xl:self-end">
          {vendaAtual.cliente && (
            <button
              onClick={onAbrirPendenciasEstoque}
              className={`${iconActionBase} border-orange-200 text-orange-500 hover:border-orange-300 hover:bg-orange-50`}
              title="Lista de espera - Produtos sem estoque"
            >
              <Bell className="h-5 w-5" />
              {pendenciasCount > 0 && (
                <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                  {pendenciasCount}
                </span>
              )}
            </button>
          )}

          {vendaAtual.cliente && (
            <button
              onClick={onAbrirOportunidades}
              className={`${iconActionBase} border-yellow-200 text-yellow-500 hover:border-yellow-300 hover:bg-yellow-50`}
              title="Ver oportunidades de venda"
            >
              <Star className="h-5 w-5 fill-yellow-500" />
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
              className={`inline-flex h-14 min-w-[56px] items-center justify-center gap-2 rounded-2xl border shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${
                painelAssistenteAberto
                  ? "border-indigo-400 bg-indigo-100 text-indigo-700"
                  : "border-indigo-200 bg-white text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50"
              }`}
              title="Assistente IA do cliente"
            >
              <Bot className="h-5 w-5" />
              {mensagensAssistenteLength > 1 && !painelAssistenteAberto && (
                <span className="h-2 w-2 rounded-full bg-indigo-500" />
              )}
            </button>
          )}

          <div
            className={
              destaqueAbrirCaixa ? `rounded-2xl ${caixaGuiaClasses.action}` : ""
            }
          >
            <MenuCaixa key={menuCaixaKey} onAbrirCaixa={onAbrirCaixa} />
          </div>

          <button
            onClick={onNavigateMeusCaixas}
            className={`${accentAction} min-w-[148px]`}
            title="Ver historico de caixas"
          >
            <Wallet className="h-5 w-5" />
            <span>Meus Caixas</span>
          </button>

          {!modoVisualizacao && vendaAtual.id && (
            <>
              <button
                onClick={onCancelarEdicao}
                disabled={loading}
                className={`${secondaryAction} min-w-[170px]`}
              >
                <X className="h-5 w-5" />
                <span>Cancelar Edicao</span>
              </button>
              <button
                onClick={onExcluirVenda}
                disabled={loading}
                className={`${destructiveAction} min-w-[118px]`}
              >
                <Trash2 className="h-5 w-5" />
                <span>Excluir</span>
              </button>
            </>
          )}

          <button
            onClick={onSalvarVenda}
            disabled={loading || modoVisualizacao || !temCaixaAberto}
            className={`${secondaryAction} min-w-[136px]`}
            title={
              !temCaixaAberto
                ? "Caixa fechado - Abra o caixa para salvar vendas"
                : "Salvar venda atual"
            }
          >
            <Save className="h-5 w-5" />
            <span>Salvar</span>
            {!temCaixaAberto && <Lock className="h-4 w-4 opacity-80" />}
          </button>

          <button
            onClick={onAbrirModalPagamento}
            disabled={
              loading ||
              vendaAtual.status === "finalizada" ||
              vendaAtual.status === "pago_nf" ||
              !temCaixaAberto
            }
            className={`${successAction} min-w-[260px]`}
            title={
              !temCaixaAberto
                ? "Caixa fechado - Abra o caixa para registrar recebimentos"
                : "Registrar pagamento da venda"
            }
          >
            <CreditCard className="h-5 w-5" />
            <span>Registrar Recebimento</span>
            {!temCaixaAberto && <Lock className="h-4 w-4 opacity-80" />}
          </button>
        </div>
      </div>
    </div>
  );
}
