import { formatCacheAge, formatDate } from "../estoqueBlingUtils";
import { MASS_LINK_BATCH_SIZE, TAB_CONFIG } from "./estoqueBlingConfig";
import { HealthMeter, SummaryCard, TabButton } from "./EstoqueBlingUi";

export function EstoqueBlingHeader({
  activeTab,
  refreshing,
  runningAction,
  onImportImages,
  onRefreshDashboard,
}) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-2">
        <div className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
          Central de pendencias Bling
        </div>
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Sincronizacao Bling</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            O Bling precisa ter cadastro correspondente no CorePet. Produtos apenas da loja fisica
            aparecem em uma area opcional e nao viram pendencia.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={onImportImages}
          disabled={refreshing || runningAction !== ""}
          className="rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {runningAction === "importar-imagens"
            ? "Importando imagens..."
            : "Importar imagens do Bling"}
        </button>
        <button
          onClick={() =>
            onRefreshDashboard({
              forceRefresh: true,
              showToast: true,
              refreshSyncProblems: activeTab === "corrigir",
            })
          }
          disabled={refreshing || runningAction !== ""}
          className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {refreshing ? "Atualizando..." : "Atualizar agora"}
        </button>
      </div>
    </div>
  );
}

export function EstoqueBlingSummaryGrid({ counts }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
      <SummaryCard label="Bling sem CorePet" value={counts.criar} tone="amber" />
      <SummaryCard label="Sugestoes SKU igual" value={counts.vincular} tone="sky" />
      <SummaryCard label="Local sem Bling" value={counts.local} hint="opcional" tone="slate" />
      <SummaryCard label="Sync com problema" value={counts.corrigir} tone="red" />
    </div>
  );
}

export function EstoqueBlingStatusPanel({
  cobertura,
  coreWarning,
  faltantesMeta,
  hasAnySnapshot,
  healthDetail,
  healthPercent,
  healthTone,
  loading,
  refreshMessage,
  refreshing,
  vinculosMeta,
}) {
  const lastSnapshotAt =
    cobertura.atualizado_em || faltantesMeta.atualizadoEm || vinculosMeta.atualizadoEm;
  const cacheAge =
    cobertura.cache_idade_segundos ||
    faltantesMeta.cacheIdadeSegundos ||
    vinculosMeta.cacheIdadeSegundos;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="space-y-1">
          {hasAnySnapshot ? (
            <>
              <div className="text-sm font-semibold text-slate-900">
                Cobertura atual: {Number(cobertura.bling_com_match_no_sistema || 0)} com match
                local, {Number(cobertura.bling_sync_ok || 0)} com sync ok.
              </div>
              <div className="text-sm text-slate-500">
                Ultima leitura: {formatDate(lastSnapshotAt)} | Cache: {formatCacheAge(cacheAge)}
              </div>
            </>
          ) : (
            <>
              <div className="text-sm font-semibold text-slate-900">
                Ainda nao existe snapshot desta central.
              </div>
              <div className="text-sm text-slate-500">
                A pagina abriu leve, sem ler o Bling inteiro. Clique em Atualizar agora quando
                quiser montar o cache.
              </div>
            </>
          )}
          {!faltantesMeta.coletaCompleta || !vinculosMeta.coletaCompleta ? (
            <div className="text-sm text-amber-700">
              A ultima coleta do Bling foi parcial. Atualize quando quiser refazer o catalogo
              completo.
            </div>
          ) : null}
          {coreWarning ? <div className="text-sm text-red-600">{coreWarning}</div> : null}
        </div>

        <div className="w-full max-w-md space-y-3">
          <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {refreshing || loading
              ? refreshMessage || "Carregando..."
              : "A tela abre pelo cache e so refaz o catalogo completo quando voce mandar."}
          </div>
          <HealthMeter
            percent={healthPercent}
            tone={healthTone}
            label="Termometro da central"
            detail={healthDetail}
          />
        </div>
      </div>
    </div>
  );
}

export function EstoqueBlingToolbar({
  activeTab,
  counts,
  faltantesMeta,
  localLoading,
  onCreateBatch,
  onMassLinkBySku,
  onReconnectBling,
  onRefreshLocal,
  onReconcileRecentes,
  onReprocessFailures,
  onSearchChange,
  onTabChange,
  runningAction,
  search,
  searchPlaceholder,
  shouldShowReconnectWarning,
  skuLinkSuggestions,
  syncLoading,
  vinculosMeta,
}) {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <div className="flex flex-wrap gap-2">
        {Object.entries(TAB_CONFIG).map(([key, config]) => (
          <TabButton
            key={key}
            active={activeTab === key}
            label={config.label}
            count={counts[key]}
            onClick={() => onTabChange(key)}
          />
        ))}
      </div>

      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-slate-500 xl:max-w-xl"
        />

        <div className="flex flex-wrap gap-3">
          {activeTab === "criar" ? (
            <button
              onClick={onCreateBatch}
              disabled={runningAction !== "" || !faltantesMeta.snapshotDisponivel}
              className="rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {runningAction === "criar-lote" ? "Criando lote..." : "Criar 20 primeiros"}
            </button>
          ) : null}

          {activeTab === "vincular" ? (
            <button
              onClick={onMassLinkBySku}
              disabled={
                runningAction !== "" ||
                !vinculosMeta.snapshotDisponivel ||
                skuLinkSuggestions.length <= 0
              }
              className="rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {runningAction === "vincular-lote"
                ? "Vinculando em lotes..."
                : `Rodar lotes de ${MASS_LINK_BATCH_SIZE} por SKU`}
            </button>
          ) : null}

          {activeTab === "local" ? (
            <button
              onClick={onRefreshLocal}
              disabled={localLoading || runningAction !== ""}
              className="rounded-xl bg-slate-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {localLoading ? "Atualizando..." : "Atualizar lista local"}
            </button>
          ) : null}

          {activeTab === "corrigir" ? (
            <>
              <button
                onClick={shouldShowReconnectWarning ? onReconnectBling : onReprocessFailures}
                disabled={runningAction !== "" || syncLoading}
                className="rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {shouldShowReconnectWarning
                  ? "Reconectar Bling"
                  : runningAction === "reprocessar"
                    ? "Reenfileirando..."
                    : "Reprocessar falhas"}
              </button>
              <button
                onClick={onReconcileRecentes}
                disabled={runningAction !== "" || syncLoading}
                className="rounded-xl bg-amber-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {runningAction === "recentes" ? "Reconciliando..." : "Reconciliar recentes"}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
