import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import api from "../api";
import { buildSyncIssue, getErrorMessage, includesSearch } from "./estoqueBlingUtils";

import {
  EMPTY_BLING_CONNECTION,
  EMPTY_COBERTURA,
  EMPTY_FALTANTES_META,
  EMPTY_LOCAL_META,
  EMPTY_VINCULOS_META,
  HEAVY_REQUEST_TIMEOUT_MS,
  SNAPSHOT_LIMIT,
  SYNC_PROBLEMS_LIMIT,
} from "./estoqueBling/estoqueBlingConfig";
import { MassLinkProgressPanel } from "./estoqueBling/EstoqueBlingUi";
import {
  EstoqueBlingHeader,
  EstoqueBlingStatusPanel,
  EstoqueBlingSummaryGrid,
  EstoqueBlingToolbar,
} from "./estoqueBling/EstoqueBlingPanels";
import {
  EstoqueBlingCreateTab,
  EstoqueBlingFixTab,
  EstoqueBlingLinkTab,
  EstoqueBlingLocalTab,
} from "./estoqueBling/EstoqueBlingTabs";
import {
  montarResumoSaudeBling,
  normalizarFaltantesBling,
  normalizarProdutosLocaisSemBling,
  normalizarResumoBling,
  normalizarVinculosBling,
} from "./estoqueBling/estoqueBlingNormalizers";
import { useEstoqueBlingActions } from "./estoqueBling/useEstoqueBlingActions";

function EstoqueBling() {
  const [activeTab, setActiveTab] = useState("criar");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState("Abrindo pelo cache da central do Bling...");
  const [coreWarning, setCoreWarning] = useState("");
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [runningAction, setRunningAction] = useState("");
  const [rowActionKey, setRowActionKey] = useState("");
  const [massLinkProgress, setMassLinkProgress] = useState(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncLoaded, setSyncLoaded] = useState(false);
  const [syncError, setSyncError] = useState("");
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState("");
  const [manualSearchKey, setManualSearchKey] = useState("");

  const [cobertura, setCobertura] = useState(EMPTY_COBERTURA);
  const [faltantesBling, setFaltantesBling] = useState([]);
  const [faltantesMeta, setFaltantesMeta] = useState(EMPTY_FALTANTES_META);
  const [produtosSemVinculo, setProdutosSemVinculo] = useState([]);
  const [vinculosMeta, setVinculosMeta] = useState(EMPTY_VINCULOS_META);
  const [produtosLocaisSemBling, setProdutosLocaisSemBling] = useState([]);
  const [localMeta, setLocalMeta] = useState(EMPTY_LOCAL_META);
  const [manualBlingLookup, setManualBlingLookup] = useState({});
  const [manualSearchTerms, setManualSearchTerms] = useState({});
  const [syncItems, setSyncItems] = useState([]);
  const [blingConnection, setBlingConnection] = useState(EMPTY_BLING_CONNECTION);
  const [selectedLocalIds, setSelectedLocalIds] = useState(() => new Set());

  const applyResumo = (data = {}) => {
    setCobertura(normalizarResumoBling(data));
  };

  const applyFaltantes = (data = {}) => {
    const { items, meta } = normalizarFaltantesBling(data);
    setFaltantesBling(items);
    setFaltantesMeta(meta);
  };

  const applyVinculos = (data = {}) => {
    const { items, meta } = normalizarVinculosBling(data);
    setProdutosSemVinculo(items);
    setVinculosMeta(meta);
  };

  const loadBlingConnectionStatus = async ({ silent = true } = {}) => {
    try {
      const response = await api.get("/bling/teste-conexao", { timeout: 15000 });
      const data = response?.data || {};
      setBlingConnection({
        checked: true,
        connected: Boolean(data.conectado || data.success),
        message: data.message || "",
        detail: data.detail || "",
      });
    } catch (error) {
      const detail = getErrorMessage(error, "Nao foi possivel verificar a conexao atual do Bling.");
      setBlingConnection((current) => ({
        checked: true,
        connected: current.checked ? current.connected : null,
        message: current.checked
          ? current.message || "Mantivemos o ultimo estado conhecido da conexao com o Bling."
          : "Nao foi possivel validar a conexao com o Bling.",
        detail,
      }));
      if (!silent) {
        toast.error(detail);
      }
    }
  };

  const loadSyncProblems = async ({ silent = true } = {}) => {
    setSyncLoading(true);
    setSyncError("");

    try {
      const response = await api.get("/estoque/sync/status-problemas", {
        timeout: HEAVY_REQUEST_TIMEOUT_MS,
        params: {
          limit: SYNC_PROBLEMS_LIMIT,
          offset: 0,
        },
      });

      setSyncItems(response?.data || []);
      setSyncLoaded(true);
    } catch (error) {
      const message = getErrorMessage(error, "Nao foi possivel carregar a fila de falhas agora.");
      setSyncError(message);
      setSyncLoaded(true);
      if (!silent) {
        toast.error(message);
      }
    } finally {
      setSyncLoading(false);
    }
  };

  const loadLocalProductsWithoutBling = async ({ silent = true } = {}) => {
    setLocalLoading(true);
    setLocalError("");

    try {
      const response = await api.get("/estoque/sync/produtos-sem-vinculo", {
        timeout: 30000,
        params: {
          limit: 200,
          offset: 0,
          apenas_com_match_bling: false,
        },
      });
      const data = response?.data || {};
      const { items, meta } = normalizarProdutosLocaisSemBling(data);
      setProdutosLocaisSemBling(items);
      setLocalMeta(meta);
    } catch (error) {
      const message = getErrorMessage(
        error,
        "Nao foi possivel carregar produtos locais sem Bling.",
      );
      setLocalError(message);
      setLocalMeta((current) => ({ ...current, loaded: true }));
      if (!silent) {
        toast.error(message);
      }
    } finally {
      setLocalLoading(false);
    }
  };

  const loadDashboard = async ({
    forceRefresh = false,
    showToast = false,
    refreshSyncProblems = false,
  } = {}) => {
    if (hasLoadedOnce) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setCoreWarning("");
    setRefreshMessage(
      forceRefresh
        ? "Atualizando painel do Bling em uma leitura consolidada..."
        : "Abrindo pelo cache da central do Bling...",
    );

    try {
      await loadBlingConnectionStatus({ silent: true });

      const response = await api.get("/estoque/sync/dashboard", {
        timeout: HEAVY_REQUEST_TIMEOUT_MS,
        params: {
          limit: SNAPSHOT_LIMIT,
          offset: 0,
          ...(forceRefresh ? { force_refresh: true } : {}),
        },
      });

      const payload = response?.data || {};
      applyResumo(payload.resumo || {});
      applyFaltantes(payload.faltantes || {});
      applyVinculos(payload.vinculos || {});

      const snapshotReturned = Boolean(
        payload?.resumo?.snapshot_disponivel ||
        payload?.faltantes?.snapshot_disponivel ||
        payload?.vinculos?.snapshot_disponivel,
      );
      const dashboardWarnings = [
        payload?.resumo?.erro_coleta_bling,
        payload?.faltantes?.erro_coleta_bling,
        payload?.vinculos?.erro_coleta_bling,
      ].filter(Boolean);

      if (dashboardWarnings.length) {
        setCoreWarning(String(dashboardWarnings[0]));
      }

      if (refreshSyncProblems) {
        setRefreshMessage(
          forceRefresh ? "Carregando fila de falhas..." : "Lendo fila de falhas...",
        );
        await loadSyncProblems({ silent: !showToast });
      }

      if (showToast) {
        if (forceRefresh && !snapshotReturned) {
          toast.error(
            dashboardWarnings[0] ||
              "A leitura terminou, mas o snapshot do Bling nao ficou disponivel.",
          );
        } else if (dashboardWarnings.length) {
          toast(dashboardWarnings[0]);
        } else {
          toast.success(
            forceRefresh ? "Painel atualizado com leitura nova do Bling." : "Painel atualizado.",
          );
        }
      }
    } catch (error) {
      const message = getErrorMessage(error, "Nao foi possivel abrir a central do Bling agora.");
      setCoreWarning(message);

      if (!hasLoadedOnce) {
        applyResumo(EMPTY_COBERTURA);
        setFaltantesBling([]);
        setFaltantesMeta(EMPTY_FALTANTES_META);
        setProdutosSemVinculo([]);
        setVinculosMeta(EMPTY_VINCULOS_META);
      }

      if (showToast) {
        toast.error(message);
      }
    } finally {
      setHasLoadedOnce(true);
      setLoading(false);
      setRefreshing(false);
      setRefreshMessage("");
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    const refreshConnectionOnFocus = () => {
      if (document.visibilityState === "hidden") return;
      loadBlingConnectionStatus({ silent: true }).catch(() => {});
    };

    window.addEventListener("focus", refreshConnectionOnFocus);
    document.addEventListener("visibilitychange", refreshConnectionOnFocus);

    return () => {
      window.removeEventListener("focus", refreshConnectionOnFocus);
      document.removeEventListener("visibilitychange", refreshConnectionOnFocus);
    };
  }, []);

  useEffect(() => {
    if (activeTab === "corrigir" && !syncLoaded && !syncLoading) {
      loadSyncProblems();
    }
  }, [activeTab, syncLoaded, syncLoading]);

  useEffect(() => {
    if (activeTab === "local" && !localMeta.loaded && !localLoading) {
      loadLocalProductsWithoutBling();
    }
  }, [activeTab, localMeta.loaded, localLoading]);

  useEffect(() => {
    setSelectedLocalIds((current) => {
      if (!current.size) return current;

      const visibleIds = new Set(produtosLocaisSemBling.map((item) => Number(item.id)));
      const next = new Set();
      current.forEach((id) => {
        if (visibleIds.has(Number(id))) {
          next.add(Number(id));
        }
      });

      return next.size === current.size ? current : next;
    });
  }, [produtosLocaisSemBling]);

  const syncProblems = useMemo(() => {
    return (syncItems || [])
      .map((item) => ({
        ...item,
        issue: buildSyncIssue(item, { blingConnected: blingConnection.connected }),
      }))
      .filter((item) => item.issue);
  }, [blingConnection.connected, syncItems]);

  const filteredCreate = useMemo(() => {
    return faltantesBling.filter((item) =>
      includesSearch(search, [
        item.descricao,
        item.codigo,
        item.sku,
        item.codigo_barras,
        item.id,
        item.motivo,
      ]),
    );
  }, [faltantesBling, search]);

  const skuLinkSuggestions = useMemo(() => {
    return produtosSemVinculo.filter((item) => item.match_origem === "sku");
  }, [produtosSemVinculo]);

  const filteredLink = useMemo(() => {
    return skuLinkSuggestions.filter((item) =>
      includesSearch(search, [
        item.nome,
        item.codigo,
        item.codigo_barras,
        item.bling_nome,
        item.bling_codigo,
        item.bling_sku,
        item.bling_codigo_barras,
        item.motivo,
      ]),
    );
  }, [search, skuLinkSuggestions]);

  const filteredLocal = useMemo(() => {
    return produtosLocaisSemBling.filter((item) =>
      includesSearch(search, [item.nome, item.codigo, item.id, item.estoque_atual]),
    );
  }, [produtosLocaisSemBling, search]);

  const filteredFix = useMemo(() => {
    return syncProblems.filter((item) =>
      includesSearch(search, [
        item.produto_nome,
        item.sku,
        item.bling_produto_id,
        item.issue?.title,
        item.issue?.description,
        item.ultimo_erro,
      ]),
    );
  }, [search, syncProblems]);

  const hasAuthInvalidIssues = filteredFix.some((item) => item.issue?.category === "auth_invalid");
  const shouldShowReconnectWarning = hasAuthInvalidIssues && blingConnection.connected !== true;

  const hasAnySnapshot = Boolean(
    cobertura.snapshot_disponivel ||
    faltantesMeta.snapshotDisponivel ||
    vinculosMeta.snapshotDisponivel,
  );
  const dashboardSyncProblemCount = cobertura.snapshot_disponivel
    ? Number((cobertura.sync_problemas_abertos ?? cobertura.bling_com_problema) || 0)
    : 0;
  const syncProblemCount = syncLoaded ? syncProblems.length : dashboardSyncProblemCount;
  const counts = {
    criar: faltantesMeta.snapshotDisponivel ? Number(faltantesMeta.total || 0) : "-",
    vincular: vinculosMeta.snapshotDisponivel ? skuLinkSuggestions.length : "-",
    local: localMeta.loaded ? Number(localMeta.total || 0) : "-",
    corrigir: syncLoaded || cobertura.snapshot_disponivel ? syncProblemCount : "-",
  };
  const selectedLocalCount = selectedLocalIds.size;
  const { healthPercent, healthTone, healthDetail } = montarResumoSaudeBling({
    hasAnySnapshot,
    faltantesMeta,
    vinculosMeta,
    syncLoaded,
    cobertura,
    syncProblemCount,
  });

  const {
    buscarBlingParaProdutoLocal,
    criarPrimeirosFaltantes,
    exportarProdutoLocalParaBling,
    exportarSelecionadosParaBling,
    handleFixItem,
    handleImportImagesFromBling,
    handleReconnectBling,
    handleReconcileRecentes,
    handleReprocessFailures,
    runMassLinkBySku,
    runRowAction,
    updateManualSearchTerm,
    vincularProdutoLocalAoBling,
  } = useEstoqueBlingActions({
    activeTab,
    filteredCreate,
    loadDashboard,
    loadSyncProblems,
    manualSearchTerms,
    selectedLocalIds,
    setLocalMeta,
    setManualBlingLookup,
    setManualSearchKey,
    setManualSearchTerms,
    setMassLinkProgress,
    setProdutosLocaisSemBling,
    setProdutosSemVinculo,
    setRowActionKey,
    setRunningAction,
    setSelectedLocalIds,
    setVinculosMeta,
    skuLinkSuggestions,
    syncProblems,
  });

  const toggleLocalSelection = (produtoId) => {
    setSelectedLocalIds((current) => {
      const id = Number(produtoId);
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const searchPlaceholder = {
    criar: "Buscar por nome, SKU ou codigo de barras",
    vincular: "Buscar por SKU igual, produto local ou item do Bling",
    local: "Buscar produto local sem vinculo",
    corrigir: "Buscar por produto, SKU, ID Bling ou erro",
  }[activeTab];

  return (
    <div className="space-y-6 p-6">
      <EstoqueBlingHeader
        activeTab={activeTab}
        refreshing={refreshing}
        runningAction={runningAction}
        onImportImages={handleImportImagesFromBling}
        onRefreshDashboard={loadDashboard}
      />

      <EstoqueBlingSummaryGrid counts={counts} />

      <EstoqueBlingStatusPanel
        cobertura={cobertura}
        coreWarning={coreWarning}
        faltantesMeta={faltantesMeta}
        hasAnySnapshot={hasAnySnapshot}
        healthDetail={healthDetail}
        healthPercent={healthPercent}
        healthTone={healthTone}
        loading={loading}
        refreshMessage={refreshMessage}
        refreshing={refreshing}
        vinculosMeta={vinculosMeta}
      />

      <EstoqueBlingToolbar
        activeTab={activeTab}
        counts={counts}
        faltantesMeta={faltantesMeta}
        localLoading={localLoading}
        onCreateBatch={criarPrimeirosFaltantes}
        onExportLocalSelected={exportarSelecionadosParaBling}
        onMassLinkBySku={runMassLinkBySku}
        onReconnectBling={handleReconnectBling}
        onRefreshLocal={() => loadLocalProductsWithoutBling({ silent: false })}
        onReconcileRecentes={handleReconcileRecentes}
        onReprocessFailures={handleReprocessFailures}
        onSearchChange={setSearch}
        onTabChange={setActiveTab}
        runningAction={runningAction}
        search={search}
        searchPlaceholder={searchPlaceholder}
        selectedLocalCount={selectedLocalCount}
        shouldShowReconnectWarning={shouldShowReconnectWarning}
        skuLinkSuggestions={skuLinkSuggestions}
        syncLoading={syncLoading}
        vinculosMeta={vinculosMeta}
      />

      {activeTab === "vincular" && massLinkProgress ? (
        <MassLinkProgressPanel
          progress={massLinkProgress}
          onClose={() => setMassLinkProgress(null)}
        />
      ) : null}

      {activeTab === "corrigir" && syncError && filteredFix.length > 0 ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm">
          Exibindo a ultima lista de falhas carregada. Nao conseguimos atualizar agora: {syncError}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm">
          {refreshMessage || "Carregando central de pendencias do Bling..."}
        </div>
      ) : null}

      {!loading && activeTab === "criar" ? (
        <EstoqueBlingCreateTab
          faltantesMeta={faltantesMeta}
          filteredCreate={filteredCreate}
          rowActionKey={rowActionKey}
          runRowAction={runRowAction}
        />
      ) : null}
      {!loading && activeTab === "vincular" ? (
        <EstoqueBlingLinkTab
          vinculosMeta={vinculosMeta}
          filteredLink={filteredLink}
          rowActionKey={rowActionKey}
          runRowAction={runRowAction}
        />
      ) : null}
      {!loading && activeTab === "local" ? (
        <EstoqueBlingLocalTab
          localLoading={localLoading}
          localMeta={localMeta}
          localError={localError}
          filteredLocal={filteredLocal}
          selectedLocalIds={selectedLocalIds}
          manualBlingLookup={manualBlingLookup}
          manualSearchTerms={manualSearchTerms}
          manualSearchKey={manualSearchKey}
          rowActionKey={rowActionKey}
          toggleLocalSelection={toggleLocalSelection}
          updateManualSearchTerm={updateManualSearchTerm}
          buscarBlingParaProdutoLocal={buscarBlingParaProdutoLocal}
          exportarProdutoLocalParaBling={exportarProdutoLocalParaBling}
          vincularProdutoLocalAoBling={vincularProdutoLocalAoBling}
        />
      ) : null}
      {!loading && activeTab === "corrigir" ? (
        <EstoqueBlingFixTab
          syncLoading={syncLoading}
          syncLoaded={syncLoaded}
          syncError={syncError}
          filteredFix={filteredFix}
          shouldShowReconnectWarning={shouldShowReconnectWarning}
          rowActionKey={rowActionKey}
          handleReconnectBling={handleReconnectBling}
          handleFixItem={handleFixItem}
        />
      ) : null}
    </div>
  );
}

export default EstoqueBling;
