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
import ActionButton from "../ui/ActionButton";
import IconActionButton from "../ui/IconActionButton";
import PageHeader from "../ui/PageHeader";

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
  const dataAtual = new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="border-b bg-white px-5 py-3">
      {(destaqueAbrirCaixa || destaqueVenda) && (
        <div className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
          {destaqueAbrirCaixa
            ? "Etapa da introducao guiada: abra o caixa para liberar salvamento e finalizacao de vendas."
            : "Etapa da introducao guiada: use esta tela para concluir a venda e validar o fluxo operacional."}
        </div>
      )}

      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <PageHeader
            icon={ShoppingCart}
            title="Ponto de Venda"
            subtitle={dataAtual}
            onTour={iniciarTour}
            tourTitle="Ver tour guiado do PDV"
          />

          <div className="flex w-full max-w-lg items-center gap-2">
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
                className="h-10 w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-3 text-sm text-slate-700 shadow-sm transition-all placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-100"
              />
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </div>
            <ActionButton
              onClick={onBuscarVenda}
              disabled={!searchVendaQuery.trim() || loading}
              intent="edit"
              size="lg"
              className="min-w-[86px]"
            >
              Buscar
            </ActionButton>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 xl:max-w-[54rem] xl:self-end">
          {vendaAtual.cliente && (
            <IconActionButton
              onClick={onAbrirPendenciasEstoque}
              icon={Bell}
              intent="warning"
              size="lg"
              badge={pendenciasCount > 0 ? pendenciasCount : null}
              title="Lista de espera - Produtos sem estoque"
            />
          )}

          {vendaAtual.cliente && (
            <IconActionButton
              onClick={onAbrirOportunidades}
              icon={Star}
              intent="warning"
              size="lg"
              badge={
                opportunitiesCount > 0 ? Math.min(opportunitiesCount, 6) : null
              }
              title="Ver oportunidades de venda"
            />
          )}

          {vendaAtual.cliente && (
            <IconActionButton
              onClick={onToggleAssistente}
              active={painelAssistenteAberto}
              icon={Bot}
              intent="edit"
              size="lg"
              title="Assistente IA do cliente"
              badge={mensagensAssistenteLength > 1 && !painelAssistenteAberto ? "" : null}
            />
          )}

          <div
            className={
              destaqueAbrirCaixa ? `rounded-lg ${caixaGuiaClasses.action}` : ""
            }
          >
            <MenuCaixa
              key={menuCaixaKey}
              onAbrirCaixa={onAbrirCaixa}
              vendaParaDevolucao={vendaAtual}
            />
          </div>

          <ActionButton
            onClick={onNavigateMeusCaixas}
            icon={Wallet}
            intent="neutral"
            tone="soft"
            size="lg"
            className="min-w-[120px]"
            title="Ver historico de caixas"
          >
            <span>Meus Caixas</span>
          </ActionButton>

          {!modoVisualizacao && vendaAtual.id && (
            <>
              <ActionButton
                onClick={onCancelarEdicao}
                disabled={loading}
                icon={X}
                intent="neutral"
                tone="soft"
                size="lg"
                className="min-w-[138px]"
              >
                <span>Cancelar Edicao</span>
              </ActionButton>
              <ActionButton
                onClick={onExcluirVenda}
                disabled={loading}
                icon={Trash2}
                intent="delete"
                tone="soft"
                size="lg"
                className="min-w-[96px]"
              >
                <span>Excluir</span>
              </ActionButton>
            </>
          )}

          <ActionButton
            onClick={onSalvarVenda}
            disabled={loading || modoVisualizacao || !temCaixaAberto}
            icon={Save}
            intent="edit"
            tone="solid"
            size="lg"
            className="min-w-[96px]"
            title={
              !temCaixaAberto
                ? "Caixa fechado - Abra o caixa para salvar vendas"
                : "Salvar venda atual"
            }
          >
            <span>Salvar</span>
            {!temCaixaAberto && <Lock className="h-4 w-4 opacity-80" />}
          </ActionButton>

          <ActionButton
            onClick={onAbrirModalPagamento}
            disabled={
              loading ||
              vendaAtual.status === "finalizada" ||
              vendaAtual.status === "pago_nf" ||
              !temCaixaAberto
            }
            icon={CreditCard}
            intent="create"
            size="lg"
            className="min-w-[190px]"
            title={
              !temCaixaAberto
                ? "Caixa fechado - Abra o caixa para registrar recebimentos"
                : "Registrar pagamento da venda"
            }
          >
            <span>Registrar Recebimento</span>
            {!temCaixaAberto && <Lock className="h-4 w-4 opacity-80" />}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
