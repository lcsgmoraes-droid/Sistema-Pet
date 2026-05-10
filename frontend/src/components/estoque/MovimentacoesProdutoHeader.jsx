import { ArrowLeft, Boxes, ExternalLink, Info, PackageOpen, Plus, RefreshCcw } from "lucide-react";
import ActionButton from "../ui/ActionButton";

function resolveEstoqueVisual(estoqueAtual, estoqueMinimo) {
  if (estoqueAtual > estoqueMinimo) {
    return {
      heroIconBg: "bg-emerald-100",
      heroIconColor: "text-green-600",
      saldoCard: "border-sky-200 bg-gradient-to-br from-sky-50 to-white",
      saldoValue: "text-sky-700",
    };
  }

  if (estoqueAtual === 0) {
    return {
      heroIconBg: "bg-red-100",
      heroIconColor: "text-red-600",
      saldoCard: "border-red-200 bg-gradient-to-br from-red-50 to-white",
      saldoValue: "text-red-700",
    };
  }

  return {
    heroIconBg: "bg-amber-100",
    heroIconColor: "text-yellow-600",
    saldoCard: "border-amber-200 bg-gradient-to-br from-amber-50 to-white",
    saldoValue: "text-amber-700",
  };
}

function resolveDisponivelVisual(saldoAposReserva, estoqueMinimo) {
  if (saldoAposReserva > estoqueMinimo) {
    return {
      card: "border-teal-200 bg-gradient-to-r from-teal-50 to-white",
      label: "text-teal-600",
      value: "text-teal-700",
    };
  }

  if (saldoAposReserva <= 0) {
    return {
      card: "border-red-200 bg-gradient-to-r from-red-50 to-white",
      label: "text-red-600",
      value: "text-red-700",
    };
  }

  return {
    card: "border-orange-200 bg-gradient-to-r from-orange-50 to-white",
    label: "text-orange-600",
    value: "text-orange-700",
  };
}

function KitNotice({ produto }) {
  if (produto?.tipo_produto !== "KIT") {
    return null;
  }

  if (produto?.tipo_kit === "VIRTUAL") {
    return (
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
        <div className="flex items-start gap-2.5">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-indigo-600" aria-hidden="true" />
          <div>
            <h3 className="mb-1 text-sm font-semibold text-indigo-900">
              Kit virtual - estoque calculado automaticamente
            </h3>
            <p className="text-xs leading-5 text-indigo-800">
              Este produto tem estoque calculado com base nos componentes. Para alterar o saldo,
              movimente os componentes individualmente.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (produto?.tipo_kit === "FISICO") {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-3">
        <div className="flex items-start gap-2.5">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-green-600" aria-hidden="true" />
          <div>
            <h3 className="mb-1 text-sm font-semibold text-green-900">
              Kit fisico - estoque proprio com sensibilizacao
            </h3>
            <p className="text-xs leading-5 text-green-800">
              Este kit possui estoque proprio. Ao movimentar o kit, os componentes tambem sao
              sensibilizados automaticamente na mesma proporcao.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

function MetricCard({ children, className = "", label, sublabel, value }) {
  return (
    <div className={`rounded-xl border p-3 shadow-sm ${className}`}>
      <div className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-80">{label}</div>
      <div className="mt-2 text-2xl font-black">{value}</div>
      {sublabel ? <div className="mt-1 text-[11px] opacity-70">{sublabel}</div> : null}
      {children}
    </div>
  );
}

export default function MovimentacoesProdutoHeader({
  abrirModalReservas,
  estoqueAtual,
  estoqueMinimo,
  estoqueReservado,
  forcandoSync,
  formatarQuantidade,
  loadingReservas,
  onAbrirPainelBling,
  onForcarSyncProduto,
  onIncluirLancamento,
  onLancarGranel,
  onVoltarProdutos,
  podeLancarGranel,
  produto,
  saldoAposReserva,
  syncDisponivel,
  syncProduto,
  syncStatusLabel,
  totalEntradas,
  totalSaidas,
  unidade,
}) {
  const estoqueVisual = resolveEstoqueVisual(estoqueAtual, estoqueMinimo);
  const disponivelVisual = resolveDisponivelVisual(saldoAposReserva, estoqueMinimo);

  return (
    <>
      <KitNotice produto={produto} />

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <button
                type="button"
                onClick={onVoltarProdutos}
                className="mt-0.5 rounded-full border border-slate-200 p-1.5 text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
                aria-label="Voltar para produtos"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              </button>

              <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${estoqueVisual.heroIconBg}`}>
                <Boxes className={`h-6 w-6 ${estoqueVisual.heroIconColor}`} aria-hidden="true" />
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl font-black tracking-tight text-slate-900">{produto.nome}</h1>
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                      syncDisponivel ? "bg-sky-100 text-sky-700" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {syncStatusLabel}
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-600">
                  <div>
                    Codigo:{" "}
                    <span className="font-mono font-medium text-slate-900">{produto.codigo || produto.sku}</span>
                  </div>
                  {produto.codigo_barras ? (
                    <div>
                      EAN: <span className="font-mono font-medium text-slate-900">{produto.codigo_barras}</span>
                    </div>
                  ) : null}
                  {syncDisponivel ? (
                    <div>
                      Bling ID:{" "}
                      <span className="font-mono font-medium text-slate-900">{syncProduto?.bling_produto_id}</span>
                    </div>
                  ) : null}
                </div>

                <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50/80 p-3 text-xs text-slate-600">
                  <div className="font-semibold text-slate-900">Operacoes rapidas</div>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    <ActionButton
                      disabled={produto?.tipo_produto === "KIT" && produto?.tipo_kit === "VIRTUAL"}
                      icon={Plus}
                      intent="create"
                      onClick={onIncluirLancamento}
                    >
                      Incluir lancamento
                    </ActionButton>

                    {podeLancarGranel ? (
                      <ActionButton icon={PackageOpen} intent="warning" onClick={onLancarGranel} tone="soft">
                        Lancar granel
                      </ActionButton>
                    ) : null}

                    <ActionButton
                      disabled={!syncDisponivel || forcandoSync}
                      icon={RefreshCcw}
                      intent="info"
                      onClick={onForcarSyncProduto}
                      tone="soft"
                    >
                      {forcandoSync ? "Enviando sync..." : "Forcar sync no Bling"}
                    </ActionButton>

                    <ActionButton icon={ExternalLink} onClick={onAbrirPainelBling} tone="soft">
                      Abrir painel Bling
                    </ActionButton>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-2">
            <MetricCard
              className="border-emerald-200 bg-gradient-to-br from-emerald-50 to-white text-emerald-700"
              label="Total entradas"
              sublabel="Historico acumulado"
              value={formatarQuantidade(totalEntradas)}
            />

            <MetricCard
              className="border-rose-200 bg-gradient-to-br from-rose-50 to-white text-rose-700"
              label="Total saidas"
              sublabel="Historico acumulado"
              value={formatarQuantidade(totalSaidas)}
            />

            <MetricCard
              className={`${estoqueVisual.saldoCard} ${estoqueVisual.saldoValue}`}
              label="Saldo atual"
              sublabel={unidade}
              value={formatarQuantidade(estoqueAtual)}
            />

            <button
              type="button"
              onClick={abrirModalReservas}
              disabled={estoqueReservado <= 0 || loadingReservas}
              className={`rounded-xl border p-3 text-left shadow-sm ${
                estoqueReservado > 0
                  ? "cursor-pointer border-amber-200 bg-gradient-to-br from-amber-50 to-white transition hover:border-amber-300 hover:shadow-md"
                  : "cursor-default border-slate-200 bg-gradient-to-br from-slate-50 to-white"
              }`}
            >
              <div
                className={`text-[10px] font-semibold uppercase tracking-[0.18em] ${
                  estoqueReservado > 0 ? "text-amber-600" : "text-slate-500"
                }`}
              >
                Reservado
              </div>
              <div className={`mt-2 text-2xl font-black ${estoqueReservado > 0 ? "text-amber-700" : "text-slate-400"}`}>
                {formatarQuantidade(estoqueReservado)}
              </div>
              <div className="mt-1 text-[11px] text-slate-500">
                {estoqueReservado > 0 ? (loadingReservas ? "Carregando pedidos..." : "Pedidos em aberto") : unidade}
              </div>
            </button>

            <div className={`rounded-xl border p-3 shadow-sm sm:col-span-2 ${disponivelVisual.card}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className={`text-[10px] font-semibold uppercase tracking-[0.18em] ${disponivelVisual.label}`}>
                    Saldo disponivel
                  </div>
                  <div className={`mt-2 text-3xl font-black ${disponivelVisual.value}`}>
                    {formatarQuantidade(saldoAposReserva)} <span className="text-lg font-bold">{unidade}</span>
                  </div>
                </div>
                <div className="rounded-xl bg-white/80 px-3 py-2 text-right shadow-sm ring-1 ring-slate-200/70">
                  <div className="text-[11px] font-medium text-slate-500">Apos reservas</div>
                  <div className="mt-1 text-xs font-semibold text-slate-700">
                    Minimo: {formatarQuantidade(estoqueMinimo)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
