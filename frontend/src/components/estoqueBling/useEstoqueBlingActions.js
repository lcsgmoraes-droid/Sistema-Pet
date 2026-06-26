import { toast } from "react-hot-toast";

import api from "../../api";
import { getErrorMessage } from "../estoqueBlingUtils";
import {
  HEAVY_REQUEST_TIMEOUT_MS,
  MASS_LINK_BATCH_SIZE,
  MASS_LINK_MAX_BATCHES,
} from "./estoqueBlingConfig";

export function useEstoqueBlingActions({
  activeTab,
  filteredCreate,
  loadDashboard,
  loadSyncProblems,
  manualSearchTerms,
  setLocalMeta,
  setManualBlingLookup,
  setManualSearchKey,
  setManualSearchTerms,
  setMassLinkProgress,
  setProdutosLocaisSemBling,
  setProdutosSemVinculo,
  setRowActionKey,
  setRunningAction,
  setVinculosMeta,
  skuLinkSuggestions,
  syncProblems,
}) {
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

  return {
    buscarBlingParaProdutoLocal,
    criarPrimeirosFaltantes,
    handleFixItem,
    handleImportImagesFromBling,
    handleReconnectBling,
    handleReconcileRecentes,
    handleReprocessFailures,
    runMassLinkBySku,
    runRowAction,
    updateManualSearchTerm,
    vincularProdutoLocalAoBling,
  };
}
