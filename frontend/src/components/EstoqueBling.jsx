import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import api from "../api";
import { buildSyncIssue, formatNumber, getErrorMessage, includesSearch } from "./estoqueBlingUtils";

import {
  EMPTY_BLING_CONNECTION,
  EMPTY_COBERTURA,
  EMPTY_FALTANTES_META,
  EMPTY_LOCAL_META,
  EMPTY_VINCULOS_META,
  HEAVY_REQUEST_TIMEOUT_MS,
  MASS_LINK_BATCH_SIZE,
  MASS_LINK_MAX_BATCHES,
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

  const applyResumo = (data = {}) => {
    setCobertura({
      ...EMPTY_COBERTURA,
      ...data,
      snapshot_disponivel: Boolean(data.snapshot_disponivel),
      precisa_atualizar: Boolean(data.precisa_atualizar),
    });
  };

  const applyFaltantes = (data = {}) => {
    setFaltantesBling(data.items || []);
    setFaltantesMeta({
      ...EMPTY_FALTANTES_META,
      total: Number(data.total || 0),
      snapshotDisponivel: Boolean(data.snapshot_disponivel),
      coletaCompleta: Boolean(data.coleta_bling_completa ?? true),
      atualizadoEm: data.atualizado_em || null,
      cacheIdadeSegundos: Number(data.cache_idade_segundos || 0),
      precisaAtualizar: Boolean(data.precisa_atualizar),
    });
  };

  const applyVinculos = (data = {}) => {
    setProdutosSemVinculo(data.items || []);
    setVinculosMeta({
      ...EMPTY_VINCULOS_META,
      total: Number(data.total || 0),
      snapshotDisponivel: Boolean(data.snapshot_disponivel),
      atualizadoEm: data.atualizado_em || null,
      cacheIdadeSegundos: Number(data.cache_idade_segundos || 0),
      coletaCompleta: Boolean(data.coleta_bling_completa ?? true),
      precisaAtualizar: Boolean(data.precisa_atualizar),
    });
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
      setProdutosLocaisSemBling(data.items || []);
      setLocalMeta({
        total: Number(data.total || 0),
        loaded: true,
        atualizadoEm: new Date().toISOString(),
      });
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
  const knownPendingCount = hasAnySnapshot
    ? Number(faltantesMeta.snapshotDisponivel ? faltantesMeta.total || 0 : 0) +
      Number(vinculosMeta.snapshotDisponivel ? vinculosMeta.total || 0 : 0) +
      Number(syncLoaded || cobertura.snapshot_disponivel ? syncProblemCount : 0)
    : null;
  const healthBaseTotal = Math.max(
    Number(cobertura.total_bling || 0),
    Number(knownPendingCount || 0),
    1,
  );
  const healthPercent =
    knownPendingCount === null
      ? 0
      : knownPendingCount <= 0
        ? 100
        : Math.max(
            0,
            Math.min(
              100,
              Math.round(((healthBaseTotal - knownPendingCount) / healthBaseTotal) * 100),
            ),
          );
  const healthTone =
    knownPendingCount === null
      ? "slate"
      : knownPendingCount === 0
        ? "emerald"
        : knownPendingCount <= 20
          ? "amber"
          : "red";
  const healthDetail =
    knownPendingCount === null
      ? "Sem leitura valida ainda. Ao atualizar, a central deve mostrar o termometro e as pendencias abertas."
      : knownPendingCount === 0
        ? "Sem pendencias nesta leitura. O catalogo atual ficou coberto e sem fila aberta."
        : `${formatNumber(knownPendingCount)} pendencia(s) aberta(s) nesta leitura. A central ja mostra o recorte que pede acao.`;

  const applyMassLinkBatchLocally = (result) => {
    const linkedIds = new Set(
      (result?.detalhes_vinculados || [])
        .map((item) => Number(item?.produto_id))
        .filter((item) => Number.isFinite(item) && item > 0),
    );

    if (!linkedIds.size) return;

    setProdutosSemVinculo((current) => current.filter((item) => !linkedIds.has(Number(item.id))));
    setVinculosMeta((current) => ({
      ...current,
      total: Math.max(Number(current.total || 0) - linkedIds.size, 0),
      atualizadoEm: new Date().toISOString(),
      cacheIdadeSegundos: 0,
    }));
  };

  const runMassLinkBySku = async () => {
    const initialTotal = Number(skuLinkSuggestions.length || 0);
    if (!initialTotal) {
      toast("Nao ha produtos pendentes para vincular neste momento.");
      return;
    }

    const maxBatches = Math.max(
      1,
      Math.min(MASS_LINK_MAX_BATCHES, Math.ceil(initialTotal / MASS_LINK_BATCH_SIZE)),
    );
    const startedAt = new Date().toISOString();

    setRunningAction("vincular-lote");
    setMassLinkProgress({
      running: true,
      startedAt,
      finishedAt: null,
      initialTotal,
      batchSize: MASS_LINK_BATCH_SIZE,
      maxBatches,
      batchesCompleted: 0,
      attempted: 0,
      linked: 0,
      syncOk: 0,
      syncErrors: 0,
      notFound: 0,
      apiErrors: 0,
      remaining: initialTotal,
      elapsedMs: 0,
      message: `Preparando ${maxBatches} lote(s) de ate ${MASS_LINK_BATCH_SIZE} item(ns).`,
      history: [],
    });

    let accumulated = {
      attempted: 0,
      linked: 0,
      syncOk: 0,
      syncErrors: 0,
      notFound: 0,
      apiErrors: 0,
      remaining: initialTotal,
      history: [],
    };

    try {
      for (let batchNumber = 1; batchNumber <= maxBatches; batchNumber += 1) {
        setMassLinkProgress((current) => ({
          ...current,
          running: true,
          message: `Processando lote ${batchNumber} de ${maxBatches}...`,
        }));

        const response = await api.post(
          "/estoque/sync/vincular-todos",
          {},
          {
            timeout: HEAVY_REQUEST_TIMEOUT_MS,
            params: {
              limite: MASS_LINK_BATCH_SIZE,
              timeout_seconds: 15,
            },
          },
        );

        const result = response?.data || {};
        const linked = Number(result.vinculados || 0);
        const attempted = Number(result.total_processados || 0);
        const syncOk = Number(result.sincronizados_com_sucesso || 0);
        const syncErrors = Number(result.sincronizados_com_erro || 0);
        const notFound = Number(result.nao_encontrados_no_bling || 0);
        const apiErrors = Number(result.erros || 0);
        const remaining = Math.max(
          Number(result.restantes_para_proximo_lote ?? accumulated.remaining - linked),
          0,
        );
        const elapsedMs = Number(result.tempo_execucao_ms || 0);

        accumulated = {
          attempted: accumulated.attempted + attempted,
          linked: accumulated.linked + linked,
          syncOk: accumulated.syncOk + syncOk,
          syncErrors: accumulated.syncErrors + syncErrors,
          notFound: accumulated.notFound + notFound,
          apiErrors: accumulated.apiErrors + apiErrors,
          remaining,
          history: [
            ...accumulated.history,
            {
              batchNumber,
              linked,
              errors: apiErrors + notFound,
              remaining,
              elapsedMs,
            },
          ].slice(-5),
        };

        applyMassLinkBatchLocally(result);

        const batchMessage =
          linked > 0
            ? `Lote ${batchNumber} concluido: ${linked} vinculado(s), ${remaining} restante(s).`
            : apiErrors || notFound
              ? `Lote ${batchNumber} sem avancos. Encontramos ${apiErrors + notFound} pendencia(s) que precisam revisao.`
              : `Lote ${batchNumber} nao encontrou novos itens para vincular.`;

        setMassLinkProgress((current) => ({
          ...current,
          running: batchNumber < maxBatches && remaining > 0 && linked > 0,
          batchesCompleted: batchNumber,
          attempted: accumulated.attempted,
          linked: accumulated.linked,
          syncOk: accumulated.syncOk,
          syncErrors: accumulated.syncErrors,
          notFound: accumulated.notFound,
          apiErrors: accumulated.apiErrors,
          remaining: accumulated.remaining,
          elapsedMs: Number(current?.elapsedMs || 0) + elapsedMs,
          message: batchMessage,
          history: accumulated.history,
        }));

        if (remaining <= 0 || linked <= 0) {
          break;
        }
      }

      setMassLinkProgress((current) => ({
        ...current,
        running: false,
        finishedAt: new Date().toISOString(),
        message:
          accumulated.linked > 0
            ? `Execucao finalizada. ${accumulated.linked} item(ns) vinculado(s) e ${accumulated.remaining} restante(s).`
            : "Execucao finalizada sem avancos. Revise os itens que continuam pendentes.",
      }));

      if (accumulated.linked > 0) {
        toast.success(`Vinculo em lotes concluido. ${accumulated.linked} item(ns) vinculado(s).`);
      } else {
        toast("Nenhum vinculo novo foi criado neste lote.");
      }

      await loadDashboard();
    } catch (error) {
      setMassLinkProgress((current) => ({
        ...current,
        running: false,
        finishedAt: new Date().toISOString(),
        message: error.response?.data?.detail || "Nao foi possivel concluir o vinculo em lotes.",
      }));
      toast.error(error.response?.data?.detail || "Nao foi possivel concluir o vinculo em lotes.");
    } finally {
      setRunningAction("");
    }
  };

  const handleImportImagesFromBling = async () => {
    const confirmed = window.confirm(
      "Importar imagens do Bling para os produtos do sistema que ainda estao sem foto? A rotina usa o SKU/codigo atual e roda mais devagar para respeitar o limite da API.",
    );

    if (!confirmed) {
      return;
    }

    setRunningAction("importar-imagens");
    try {
      const response = await api.post(
        "/estoque/sync/importar-imagens",
        {},
        {
          timeout: 0,
          params: {
            limite: 100,
            apenas_sem_imagem: true,
            atraso_ms: 900,
          },
        },
      );

      const data = response?.data || {};
      const imported = Number(data.importados || 0);
      const noMatch = Number(data.sem_match_por_sku || 0);
      const noImage = Number(data.sem_imagem_no_bling || 0);
      const errors = Number(data.erros || 0);

      if (imported > 0) {
        toast.success(
          `Importacao concluida: ${imported} imagem(ns) nova(s). Sem match por SKU: ${noMatch}. Sem imagem no Bling: ${noImage}.`,
        );
      } else {
        toast(
          `Nenhuma imagem nova entrou nesta rodada. Sem match por SKU: ${noMatch}. Sem imagem no Bling: ${noImage}.`,
        );
      }

      if (errors > 0) {
        toast(`${errors} item(ns) tiveram erro e ficaram fora desta rodada.`);
      }

      await loadDashboard();
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Nao foi possivel importar as imagens do Bling agora.",
      );
    } finally {
      setRunningAction("");
    }
  };

  const runRowAction = async (key, action, successMessage) => {
    setRowActionKey(key);
    try {
      const response = await action();
      const data = response?.data || {};
      const resolvedMessage =
        typeof successMessage === "function"
          ? successMessage(data)
          : data.message || successMessage;

      if (data.ok === false && !data.rate_limited) {
        throw new Error(data.detail || data.erro || "Nao foi possivel concluir a acao.");
      }

      if (data.rate_limited) {
        toast(data.message || "O Bling pediu uma pausa. O item foi reagendado automaticamente.");
      } else {
        toast.success(resolvedMessage);
      }
      await loadDashboard();
      if (activeTab === "corrigir") {
        await loadSyncProblems();
      }
    } catch (error) {
      toast.error(
        error.response?.data?.detail || error.message || "Nao foi possivel concluir a acao.",
      );
    } finally {
      setRowActionKey("");
    }
  };

  const runGlobalAction = async (key, action, successMessage, refreshOptions = {}) => {
    setRunningAction(key);
    try {
      await action();
      toast.success(successMessage);
      await loadDashboard(refreshOptions);
      if (activeTab === "corrigir" || refreshOptions.refreshSyncProblems) {
        await loadSyncProblems();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel concluir a acao.");
    } finally {
      setRunningAction("");
    }
  };

  const handleReprocessFailures = async () => {
    setRunningAction("reprocessar");
    try {
      const response = await api.post(
        "/estoque/sync/reprocessar-falhas",
        { limit: 30 },
        { timeout: HEAVY_REQUEST_TIMEOUT_MS },
      );
      const data = response?.data || {};
      const scheduled = Number(data.reprocessados || 0);
      const normalizedBefore = Number(data.normalizados_antes || 0);
      const requeuedWithoutQueue = Number(data.sem_fila_reenfileirados || 0);
      const processedNow = Number(data.processados_agora || 0);
      const remaining = Number(data.restantes_para_scheduler || 0);
      const rateLimited = Boolean(data.rate_limited);
      const cooldown = Number(data.cooldown_seconds || 0);
      const followUpDelayMs = Math.max(cooldown ? Math.ceil(cooldown) : 4, 4) * 1000 + 1000;

      if (scheduled <= 0) {
        const visibleIssues = Number(syncProblems.length || 0);
        toast(
          normalizedBefore > 0
            ? `${normalizedBefore} item(ns) antigos foram ajustados de volta ao estado correto. Nao havia falhas reais prontas para reprocessar agora.`
            : visibleIssues > 0
              ? `Os ${visibleIssues} item(ns) visiveis agora pedem revisao ou reconciliacao individual. Nao havia falhas de fila prontas para reprocessar em lote.`
              : "Nao havia falhas prontas para reprocessar.",
        );
      } else if (rateLimited) {
        toast.success(
          `Reagendamos ${scheduled} falha(s). ${processedNow} passaram agora, ${remaining} seguem na fila segura, ${requeuedWithoutQueue} vieram de erro sem fila e ${normalizedBefore} item(ns) antigos foram limpos${cooldown ? ` (${Math.ceil(cooldown)}s de respiro).` : "."}`,
        );
      } else {
        toast.success(
          `Reagendamos ${scheduled} falha(s). ${processedNow} foram processadas agora, ${remaining} seguem na fila segura, ${requeuedWithoutQueue} vieram de erro sem fila e ${normalizedBefore} item(ns) antigos foram limpos.`,
        );
      }

      await loadDashboard({ refreshSyncProblems: true });
      window.setTimeout(() => {
        loadDashboard({ refreshSyncProblems: true }).catch(() => {});
      }, followUpDelayMs);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Nao foi possivel reprocessar as falhas agora.");
    } finally {
      setRunningAction("");
    }
  };

  const handleReconnectBling = async () => {
    try {
      const authRedirectUrl = `${window.location.origin}/api/auth/bling/link-autorizacao?redirect=1`;
      const opened = window.open(authRedirectUrl, "_blank", "noopener,noreferrer");

      if (!opened) {
        window.location.assign(authRedirectUrl);
      }

      toast.success("Abrimos a autorizacao do Bling em nova aba para reconectar a integracao.");
    } catch (error) {
      toast.error(
        error.response?.data?.detail ||
          error.message ||
          "Nao foi possivel abrir a autorizacao do Bling agora.",
      );
    }
  };

  const updateManualSearchTerm = (produtoId, value) => {
    setManualSearchTerms((current) => ({
      ...current,
      [produtoId]: value,
    }));
  };

  const buscarBlingParaProdutoLocal = async (produto) => {
    const key = String(produto.id);
    const termo = String(manualSearchTerms[key] ?? produto.codigo ?? "").trim();

    if (!termo) {
      toast("Informe SKU, codigo, ID ou nome para buscar no Bling.");
      return;
    }

    setManualSearchKey(key);
    setManualBlingLookup((current) => ({
      ...current,
      [key]: { loading: true, searched: true, items: [], error: "" },
    }));

    try {
      const response = await api.get("/estoque/sync/produtos-bling", {
        timeout: 30000,
        params: {
          busca: termo,
          limite: 10,
        },
      });
      setManualBlingLookup((current) => ({
        ...current,
        [key]: {
          loading: false,
          searched: true,
          items: response?.data || [],
          error: "",
        },
      }));
    } catch (error) {
      const message = getErrorMessage(error, "Nao foi possivel buscar esse produto no Bling.");
      setManualBlingLookup((current) => ({
        ...current,
        [key]: { loading: false, searched: true, items: [], error: message },
      }));
      toast.error(message);
    } finally {
      setManualSearchKey("");
    }
  };

  const vincularProdutoLocalAoBling = async (produto, itemBling) => {
    const key = `manual-link-${produto.id}-${itemBling.id}`;
    setRowActionKey(key);

    try {
      await api.post("/estoque/sync/vincular", {
        produto_id: produto.id,
        bling_id: String(itemBling.id),
      });

      setProdutosLocaisSemBling((current) =>
        current.filter((item) => Number(item.id) !== Number(produto.id)),
      );
      setLocalMeta((current) => ({
        ...current,
        total: Math.max(Number(current.total || 0) - 1, 0),
        atualizadoEm: new Date().toISOString(),
      }));
      setManualBlingLookup((current) => {
        const next = { ...current };
        delete next[String(produto.id)];
        return next;
      });

      toast.success("Produto local vinculado ao item escolhido do Bling.");
      await loadDashboard();
    } catch (error) {
      toast.error(
        error.response?.data?.detail || error.message || "Nao foi possivel criar o vinculo.",
      );
    } finally {
      setRowActionKey("");
    }
  };

  const criarPrimeirosFaltantes = async () => {
    const candidatos = filteredCreate
      .filter((item) => item.pronto_para_autocorrecao && item.id)
      .slice(0, 20);

    if (!candidatos.length) {
      toast("Nenhum item pronto para autocorrecao neste recorte.");
      return;
    }

    setRunningAction("criar-lote");
    let sucesso = 0;
    let falhas = 0;

    try {
      for (const item of candidatos) {
        try {
          await api.post("/estoque/sync/faltantes-bling/criar", { bling_id: item.id });
          sucesso += 1;
        } catch {
          falhas += 1;
        }
      }
      toast.success(`Lote concluido. Sucesso: ${sucesso} | Falhas: ${falhas}`);
      await loadDashboard();
    } finally {
      setRunningAction("");
    }
  };

  const handleFixItem = async (item) => {
    const issue = item.issue;
    if (!issue) return;

    if (issue.action === "reauthorize") {
      await handleReconnectBling();
      return;
    }

    if (issue.action === "reconcile") {
      await runRowAction(
        `fix-${item.produto_id}`,
        () => api.post(`/estoque/sync/reconciliar/${item.produto_id}?origem=sistema`),
        "Reconcilicao enviada para o Bling.",
      );
      return;
    }

    await runRowAction(
      `fix-${item.produto_id}`,
      () => api.post(`/estoque/sync/forcar/${item.produto_id}`),
      "Nova tentativa enviada com sucesso.",
    );
  };

  const handleReconcileRecentes = () =>
    runGlobalAction(
      "recentes",
      () =>
        api.post("/estoque/sync/reconciliar-recentes", { limit: 150, minutes: 30 }, { timeout: 0 }),
      "Revisao dos recentes concluida.",
    );

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
          manualBlingLookup={manualBlingLookup}
          manualSearchTerms={manualSearchTerms}
          manualSearchKey={manualSearchKey}
          rowActionKey={rowActionKey}
          updateManualSearchTerm={updateManualSearchTerm}
          buscarBlingParaProdutoLocal={buscarBlingParaProdutoLocal}
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
