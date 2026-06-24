import api from "../../api";
import EmptyState from "../ui/EmptyState";
import { formatCacheAge, formatDate, formatNumber } from "../estoqueBlingUtils";
import { ISSUE_TONES, TAB_CONFIG } from "./estoqueBlingConfig";
import { PendingCard } from "./EstoqueBlingUi";

export function EstoqueBlingCreateTab({
  faltantesMeta,
  filteredCreate,
  rowActionKey,
  runRowAction,
}) {
  if (!faltantesMeta.snapshotDisponivel && !filteredCreate.length) {
    return (
      <EmptyState
        title="Ainda nao existe snapshot do catalogo do Bling"
        description="Use Atualizar agora para recalcular o catalogo apenas quando quiser. Depois disso, a tela abre pelo cache."
      />
    );
  }

  if (!filteredCreate.length) {
    return (
      <EmptyState
        title={TAB_CONFIG.criar.emptyTitle}
        description={TAB_CONFIG.criar.emptyDescription}
      />
    );
  }

  return (
    <div className="space-y-4">
      {filteredCreate.map((item) => (
        <PendingCard
          key={`criar-${item.id}-${item.codigo}`}
          title={item.descricao}
          subtitle={`Bling #${item.id || "-"} | Estoque no Bling: ${formatNumber(item.estoque)}`}
          tone={item.pronto_para_autocorrecao ? "amber" : "slate"}
          badges={[
            { label: "SKU", value: item.sku || item.codigo || "-", mono: true },
            { label: "Codigo de barras", value: item.codigo_barras || "-", mono: true },
          ]}
          reason={{
            title: item.acao_sugerida || "Criar cadastro local",
            description: item.motivo || "Produto do Bling sem correspondente local.",
          }}
          details={[
            { label: "Codigo no Bling", value: item.codigo || "-", mono: true },
            { label: "Ultima leitura", value: formatDate(faltantesMeta.atualizadoEm) },
            { label: "Cache", value: formatCacheAge(faltantesMeta.cacheIdadeSegundos) },
          ]}
          actions={[
            {
              label: rowActionKey === `create-${item.id}` ? "Criando..." : "Criar e vincular",
              onClick: () =>
                runRowAction(
                  `create-${item.id}`,
                  () => api.post("/estoque/sync/faltantes-bling/criar", { bling_id: item.id }),
                  "Produto criado e vinculado com sucesso.",
                ),
              disabled: !item.pronto_para_autocorrecao || rowActionKey !== "",
              className: ISSUE_TONES.emerald.button,
            },
          ]}
        />
      ))}
    </div>
  );
}

export function EstoqueBlingLinkTab({ vinculosMeta, filteredLink, rowActionKey, runRowAction }) {
  if (!vinculosMeta.snapshotDisponivel && !filteredLink.length) {
    return (
      <EmptyState
        title="Ainda nao existe snapshot dos itens para vincular"
        description="Use Atualizar agora para montar esse recorte do catalogo do Bling e depois abrir a tela pelo cache."
      />
    );
  }

  if (!filteredLink.length) {
    return (
      <EmptyState
        title={TAB_CONFIG.vincular.emptyTitle}
        description={TAB_CONFIG.vincular.emptyDescription}
      />
    );
  }

  return (
    <div className="space-y-4">
      {filteredLink.map((item) => {
        const isParentProduct =
          String(item.tipo_produto || "").toUpperCase() === "PAI" ||
          item.sincroniza_estoque === false;
        const actionLabel = isParentProduct ? "Vincular sem sync" : "Vincular agora";
        const successMessage = isParentProduct
          ? "Produto PAI vinculado para catalogo. O estoque continuou fora do sync automatico."
          : "Produto vinculado com sucesso.";

        return (
          <PendingCard
            key={`vincular-${item.id}`}
            title={item.nome}
            subtitle={`Bling: ${item.bling_nome || "-"} | SKU igual${isParentProduct ? " | Produto PAI" : ""}`}
            tone={isParentProduct ? "slate" : "sky"}
            badges={[
              { label: "SKU local", value: item.codigo || "-", mono: true },
              {
                label: "SKU Bling",
                value: item.bling_sku || item.bling_codigo || "-",
                mono: true,
              },
              { label: "Cod. barras local", value: item.codigo_barras || "-", mono: true },
              { label: "Tipo local", value: item.tipo_produto || "SIMPLES" },
            ]}
            reason={{
              title: item.acao_sugerida || "Vinculo pendente",
              description:
                item.motivo || "O produto ja existe dos dois lados, falta apenas criar o vinculo.",
            }}
            details={[
              { label: "ID Bling", value: item.bling_id || "-", mono: true },
              { label: "Cod. barras Bling", value: item.bling_codigo_barras || "-", mono: true },
              {
                label: isParentProduct ? "Sync de estoque" : "Estoque local",
                value: isParentProduct
                  ? "Desabilitado para produto PAI"
                  : formatNumber(item.estoque_atual),
              },
            ]}
            actions={[
              {
                label: rowActionKey === `link-${item.id}` ? "Vinculando..." : actionLabel,
                onClick: () =>
                  runRowAction(
                    `link-${item.id}`,
                    () =>
                      api.post("/estoque/sync/vincular", {
                        produto_id: item.id,
                        bling_id: item.bling_id,
                      }),
                    successMessage,
                  ),
                disabled: rowActionKey !== "",
                className: isParentProduct ? ISSUE_TONES.slate.button : ISSUE_TONES.sky.button,
              },
            ]}
          />
        );
      })}
    </div>
  );
}

export function EstoqueBlingLocalTab({
  localLoading,
  localMeta,
  localError,
  filteredLocal,
  manualBlingLookup,
  manualSearchTerms,
  manualSearchKey,
  rowActionKey,
  updateManualSearchTerm,
  buscarBlingParaProdutoLocal,
  vincularProdutoLocalAoBling,
}) {
  if (localLoading && !localMeta.loaded) {
    return (
      <EmptyState
        title="Carregando produtos locais"
        description="Esta leitura usa apenas o cadastro local e nao consulta o Bling."
      />
    );
  }

  if (localError && !filteredLocal.length) {
    return <EmptyState title="Nao foi possivel carregar a lista local" description={localError} />;
  }

  if (!filteredLocal.length) {
    return (
      <EmptyState
        title={TAB_CONFIG.local.emptyTitle}
        description={TAB_CONFIG.local.emptyDescription}
      />
    );
  }

  return (
    <div className="space-y-4">
      {filteredLocal.map((item) => {
        const key = String(item.id);
        const lookup = manualBlingLookup[key] || {};
        const searchTerm = manualSearchTerms[key] ?? item.codigo ?? "";

        return (
          <PendingCard
            key={`local-${item.id}`}
            title={item.nome}
            subtitle={`SKU local ${item.codigo || "-"} | Estoque ${formatNumber(item.estoque_atual)}`}
            tone="slate"
            badges={[
              { label: "SKU local", value: item.codigo || "-", mono: true },
              { label: "ID local", value: item.id, mono: true },
            ]}
            reason={{
              title: "Opcional para loja fisica",
              description:
                "Este produto ainda nao tem vinculo com o Bling. Busque no Bling somente se ele tambem for vendido online ou por marketplace.",
            }}
            details={[
              { label: "Estoque local", value: formatNumber(item.estoque_atual) },
              { label: "Lista local", value: formatDate(localMeta.atualizadoEm) },
              {
                label: "Consulta Bling",
                value: lookup.searched ? "Feita sob demanda" : "Nao feita",
              },
            ]}
            actions={[
              {
                label: manualSearchKey === key ? "Buscando..." : "Buscar no Bling",
                onClick: () => buscarBlingParaProdutoLocal(item),
                disabled: manualSearchKey !== "" || rowActionKey !== "",
                className: ISSUE_TONES.slate.button,
              },
            ]}
          >
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                value={searchTerm}
                onChange={(event) => updateManualSearchTerm(key, event.target.value)}
                placeholder="SKU, codigo, ID ou nome no Bling"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-slate-500"
              />
              <button
                type="button"
                onClick={() => buscarBlingParaProdutoLocal(item)}
                disabled={manualSearchKey !== "" || rowActionKey !== ""}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
              >
                Buscar
              </button>
            </div>

            {lookup.error ? (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {lookup.error}
              </div>
            ) : null}

            {lookup.searched && !lookup.loading && !lookup.error && !lookup.items?.length ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                Nenhum item do Bling retornou para esse termo.
              </div>
            ) : null}

            {lookup.items?.length ? (
              <div className="space-y-2">
                {lookup.items.map((blingItem) => (
                  <div
                    key={`${item.id}-${blingItem.id}`}
                    className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-slate-900">
                        {blingItem.descricao || "Produto Bling"}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        ID {blingItem.id || "-"} | SKU {blingItem.codigo || "-"} | Estoque{" "}
                        {formatNumber(blingItem.estoque)}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => vincularProdutoLocalAoBling(item, blingItem)}
                      disabled={rowActionKey !== ""}
                      className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                      {rowActionKey === `manual-link-${item.id}-${blingItem.id}`
                        ? "Vinculando..."
                        : "Vincular"}
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </PendingCard>
        );
      })}
    </div>
  );
}

export function EstoqueBlingFixTab({
  syncLoading,
  syncLoaded,
  syncError,
  filteredFix,
  shouldShowReconnectWarning,
  rowActionKey,
  handleReconnectBling,
  handleFixItem,
}) {
  if (syncLoading && !syncLoaded) {
    return (
      <EmptyState
        title="Carregando fila de falhas"
        description="Estamos buscando apenas os itens com problema de sincronizacao para evitar travar a tela."
      />
    );
  }

  if (syncError && !filteredFix.length) {
    return <EmptyState title="Nao foi possivel carregar as falhas agora" description={syncError} />;
  }

  if (!filteredFix.length) {
    return (
      <EmptyState
        title={TAB_CONFIG.corrigir.emptyTitle}
        description={TAB_CONFIG.corrigir.emptyDescription}
      />
    );
  }

  return (
    <div className="space-y-4">
      {shouldShowReconnectWarning ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm">
          <div className="font-semibold">A integracao com o Bling precisa ser reconectada.</div>
          <div className="mt-1">
            Enquanto o token do Bling estiver invalido, reprocessar falhas ou forcar sincronizacao
            vai continuar falhando.
          </div>
          <button
            type="button"
            onClick={handleReconnectBling}
            className="mt-3 rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-600"
          >
            Reconectar Bling
          </button>
        </div>
      ) : null}

      {filteredFix.some((item) => item.issue?.category === "rate_limit") ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm">
          Abrir ou atualizar a pagina nao envia estoque para o Bling. Quando aparecer aviso de
          limite, isso se refere a uma tentativa anterior ja registrada pela fila.
        </div>
      ) : null}

      {filteredFix.map((item) => (
        <PendingCard
          key={`corrigir-${item.produto_id}`}
          title={item.produto_nome}
          subtitle={`Bling ID ${item.bling_produto_id || "-"} | Status ${item.status}${item.queue_status ? ` | Fila ${item.queue_status}` : ""}`}
          tone={item.issue?.tone || "slate"}
          badges={[
            { label: "SKU", value: item.sku || "-", mono: true },
            { label: "Divergencia", value: formatNumber(item.divergencia) },
            { label: "Tentativas", value: String(item.tentativas_sync || 0) },
          ]}
          reason={{
            title: item.issue?.title || "Pendencia de sincronizacao",
            description:
              item.issue?.description || "Existe uma divergencia ou falha pendente neste item.",
          }}
          details={[
            { label: "Ultima sync", value: formatDate(item.ultima_sincronizacao) },
            { label: "Ultima tentativa", value: formatDate(item.ultima_tentativa_sync) },
            {
              label: item.issue?.detailLabel || "Ultimo registro",
              value: item.issue?.detailValue || "Sem detalhe adicional.",
            },
            { label: "Detalhe tecnico", value: item.issue?.technicalValue || "-" },
          ]}
          actions={[
            {
              label:
                rowActionKey === `fix-${item.produto_id}`
                  ? "Corrigindo..."
                  : item.issue?.buttonLabel || "Corrigir agora",
              onClick: () => handleFixItem(item),
              disabled: rowActionKey !== "",
              className: (ISSUE_TONES[item.issue?.tone] || ISSUE_TONES.slate).button,
            },
          ]}
        />
      ))}
    </div>
  );
}
