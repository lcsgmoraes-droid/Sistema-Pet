import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';

import api from '../api';

const STATUS_STYLES = {
  ativo: 'bg-emerald-100 text-emerald-700',
  pendente: 'bg-amber-100 text-amber-700',
  erro: 'bg-red-100 text-red-700',
  falha_final: 'bg-red-100 text-red-700',
  pausado: 'bg-zinc-200 text-zinc-700',
};

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('pt-BR');
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
  return Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

function EstoqueBling() {
  const PRODUCTS_PAGE_SIZE = 99999;
  const MASS_LINK_BATCH_SIZE = 50;
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('todos');
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [products, setProducts] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [syncItems, setSyncItems] = useState([]);
  const [health, setHealth] = useState({ ativos: 0, pendentes: 0, erros: 0, divergentes: 0 });
  const [blingSearch, setBlingSearch] = useState('');
  const [blingProducts, setBlingProducts] = useState([]);
  const [runningAction, setRunningAction] = useState('');
  const [rowActionId, setRowActionId] = useState(null);
  const [lastBatchResult, setLastBatchResult] = useState(null);

  const loadPage = async (currentSearch = search) => {
    setLoading(true);

    // Produtos são prioridade visual: preencher a tabela sem esperar status/health.
    const productsRequest = api.get('/produtos/', {
      params: {
        page: 1,
        page_size: PRODUCTS_PAGE_SIZE,
      },
    });
    const healthRequest = api.get('/estoque/sync/health');
    const syncRequest = api.get('/estoque/sync/status', { params: currentSearch ? { busca: currentSearch } : {} });

    productsRequest
      .then((response) => {
        const payload = response?.data;

        if (Array.isArray(payload)) {
          setProducts(payload);
          setTotalProducts(payload.length);
          return;
        }

        if (Array.isArray(payload?.items)) {
          setProducts(payload.items);
          setTotalProducts(Number(payload?.total ?? payload.items.length ?? 0));
          return;
        }

        if (Array.isArray(payload?.produtos)) {
          setProducts(payload.produtos);
          setTotalProducts(Number(payload?.total ?? payload.produtos.length ?? 0));
          return;
        }

        setProducts([]);
        setTotalProducts(0);
      })
      .catch((error) => {
        setProducts([]);
        setTotalProducts(0);
        toast.error(error.response?.data?.detail || 'Falha ao carregar produtos');
      })
      .finally(() => {
        setLoading(false);
      });

    healthRequest
      .then((response) => {
        setHealth(response?.data || { ativos: 0, pendentes: 0, erros: 0, divergentes: 0 });
      })
      .catch(() => {
        setHealth({ ativos: 0, pendentes: 0, erros: 0, divergentes: 0 });
      });

    syncRequest
      .then((response) => {
        setSyncItems(response?.data || []);
      })
      .catch((error) => {
        setSyncItems([]);
        toast.error(error.response?.data?.detail || 'Falha ao carregar status de sincronização');
      });
  };

  useEffect(() => {
    loadPage('');
  }, []);

  const syncMap = useMemo(() => {
    const map = new Map();
    for (const item of syncItems) {
      map.set(item.produto_id, item);
    }
    return map;
  }, [syncItems]);

  const baseRows = useMemo(() => {
    return products.map((product) => {
      const sync = syncMap.get(product.id);
      return {
        id: product.id,
        codigo: product.codigo,
        nome: product.nome,
        estoqueAtual: product.estoque_atual ?? 0,
        sku: product.sku,
        blingId: sync?.bling_produto_id || '',
        status: sync?.status || 'nao_vinculado',
        queueStatus: sync?.queue_status || null,
        ultimaSincronizacao: sync?.ultima_sincronizacao || null,
        ultimaTentativa: sync?.ultima_tentativa_sync || null,
        proximaTentativa: sync?.proxima_tentativa_sync || null,
        ultimaConferencia: sync?.ultima_conferencia_bling || null,
        ultimoErro: sync?.ultimo_erro || '',
        tentativas: sync?.tentativas_sync || 0,
        estoqueBling: sync?.estoque_bling,
        divergencia: sync?.divergencia,
        vinculado: Boolean(sync?.bling_produto_id),
      };
    });
  }, [products, syncMap]);

  const mergedRows = useMemo(() => {
    return baseRows.filter((row) => {
      const normalizedSearch = search.trim().toLowerCase();
      const matchesSearch =
        !normalizedSearch ||
        row.nome?.toLowerCase().includes(normalizedSearch) ||
        row.codigo?.toLowerCase().includes(normalizedSearch) ||
        row.sku?.toLowerCase().includes(normalizedSearch) ||
        row.blingId?.toLowerCase().includes(normalizedSearch);

      if (!matchesSearch) return false;
      if (statusFilter === 'todos') return true;
      if (statusFilter === 'vinculado') return row.vinculado;
      if (statusFilter === 'erro') return row.status === 'erro' || row.queueStatus === 'falha_final';
      if (statusFilter === 'pendente') return row.status === 'pendente' || row.queueStatus === 'pendente' || row.queueStatus === 'erro';
      if (statusFilter === 'divergente') return Math.abs(Number(row.divergencia || 0)) >= 0.01;
      if (statusFilter === 'nao_vinculado') return !row.vinculado;
      return row.status === statusFilter;
    });
  }, [baseRows, search, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(mergedRows.length / pageSize));
  const pageSafe = Math.min(page, totalPages);
  const pageStart = (pageSafe - 1) * pageSize;
  const pageEnd = pageStart + pageSize;
  const pagedRows = mergedRows.slice(pageStart, pageEnd);

  const naoVinculados = useMemo(
    () => baseRows.filter((row) => !row.vinculado),
    [baseRows],
  );

  const comMatchNoBling = useMemo(
    () => baseRows.filter((row) => row.vinculado).length,
    [baseRows],
  );

  const vinculadosSemSync = useMemo(
    () => baseRows.filter((row) => {
      if (!row.vinculado) return false;
      const statusComProblema = row.status !== 'ativo';
      const filaComProblema = ['pendente', 'erro', 'falha_final'].includes(row.queueStatus);
      return statusComProblema || filaComProblema;
    }).length,
    [baseRows],
  );

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const runRowAction = async (produtoId, action, successMessage) => {
    setRowActionId(produtoId);
    try {
      await action();
      toast.success(successMessage);
      await loadPage(search);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao executar ação');
    } finally {
      setRowActionId(null);
    }
  };

  const runGlobalAction = async (key, action, successMessage) => {
    setRunningAction(key);
    try {
      const response = await action();
      const message = successMessage(response);
      toast.success(message, { duration: 9000 });
      await loadPage(search);
      return response;
    } catch (error) {
      if (error.code === 'ECONNABORTED') {
        toast.error('A ação em lote demorou além do tempo limite. Tente novamente ou use menos itens por vez.');
      } else if (error.response?.status === 504) {
        toast.error('A ação demorou no servidor (504). Vamos processar em partes menores: clique novamente para continuar.');
      } else {
        toast.error(error.response?.data?.detail || 'Erro ao executar ação em lote');
      }
      return null;
    } finally {
      setRunningAction('');
    }
  };

  const searchBlingProducts = async (customTerm = '') => {
    setRunningAction('buscar-bling');
    try {
      const term = (customTerm || blingSearch || '').trim();
      const response = await api.get('/estoque/sync/produtos-bling', {
        params: term ? { busca: term } : {},
      });
      setBlingProducts(response.data || []);
      toast.success(`Busca concluída: ${(response.data || []).length} item(ns) no Bling`);
    } catch (error) {
      const detalhe = error.response?.data?.detail;
      if (error.response?.status === 429) {
        toast.error(detalhe || 'Bling está com limite temporário. Aguarde alguns segundos e tente novamente.');
      } else {
        toast.error(detalhe || 'Erro ao buscar produtos no Bling');
      }
    } finally {
      setRunningAction('');
    }
  };

  const vincularTodosPorSku = async () => {
    const confirma = globalThis.confirm(`Executar vínculo em massa por SKU em lote de ${MASS_LINK_BATCH_SIZE} itens agora?`);
    if (!confirma) return;

    const response = await runGlobalAction(
      'vincular-massa',
      () => api.post('/estoque/sync/vincular-todos', {}, {
        timeout: 0,
        params: { limite: MASS_LINK_BATCH_SIZE, timeout_seconds: 25 },
      }),
      (response) => {
        const data = response.data || {};
        const parcial = data.interrompido_por_tempo ? ' | Parcial por tempo' : '';
        return `Lote concluído. Vinculados: ${data.vinculados || 0} | Não encontrados: ${data.nao_encontrados_no_bling || 0} | Erros: ${data.erros || 0} | Restantes: ${data.restantes_para_proximo_lote || 0}${parcial}`;
      },
    );

    if (response?.data) {
      setLastBatchResult(response.data);
    }
  };

  const sincronizarDivergentes = async () => {
    const divergentes = baseRows.filter(
      (row) => row.vinculado && Math.abs(Number(row.divergencia || 0)) >= 0.01,
    );

    if (divergentes.length === 0) {
      toast('Não há divergências para sincronizar agora.');
      return;
    }

    const confirma = globalThis.confirm(`Sincronizar ${divergentes.length} item(ns) divergente(s) do sistema para o Bling?`);
    if (!confirma) return;

    setRunningAction('sync-divergentes');
    let ok = 0;
    let falhas = 0;

    try {
      for (const row of divergentes) {
        try {
          await api.post(`/estoque/sync/reconciliar/${row.id}?origem=sistema`);
          ok += 1;
        } catch {
          falhas += 1;
        }
      }
      toast.success(`Sincronização em lote concluída. Sucesso: ${ok} | Falhas: ${falhas}`);
      await loadPage(search);
    } finally {
      setRunningAction('');
    }
  };

  const stats = {
    total: totalProducts,
    vinculados: comMatchNoBling,
    naoVinculados: naoVinculados.length,
    vinculadosSemSync,
    erros: health.erros || 0,
    divergentes: health.divergentes || 0,
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sincronização Bling</h1>
        <p className="text-sm text-gray-600 mt-1">
          Objetivo: manter 100% dos produtos vinculados com o Bling e com sincronização automática + manual funcionando.
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Regra dos números: Sistema Pet (total) = Com match no Bling + Faltam vincular.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-6">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Sistema Pet (total)</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">{stats.total}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Com match no Bling</div>
          <div className="mt-2 text-3xl font-semibold text-emerald-700">{stats.vinculados}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Faltam vincular</div>
          <div className="mt-2 text-3xl font-semibold text-slate-800">{stats.naoVinculados}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Com match sem sync ok</div>
          <div className="mt-2 text-3xl font-semibold text-orange-700">{stats.vinculadosSemSync}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Com erro</div>
          <div className="mt-2 text-3xl font-semibold text-red-700">{stats.erros}</div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Divergentes</div>
          <div className="mt-2 text-3xl font-semibold text-amber-700">{stats.divergentes}</div>
        </div>
      </div>

      <div className="rounded-xl border border-sky-200 bg-sky-50 p-5 shadow-sm">
        <h2 className="text-base font-semibold text-sky-900">Como usar esta tela (guia rápido)</h2>
        <div className="mt-2 grid gap-2 text-sm text-sky-900 md:grid-cols-2">
          <div><strong>Buscar no Bling:</strong> procura por código, SKU e nome para encontrar match.</div>
          <div><strong>Vincular em massa por SKU:</strong> tenta vincular vários itens de uma vez automaticamente.</div>
          <div><strong>Forçar sync:</strong> envia o estoque agora (se não tiver vínculo, tenta vincular antes).</div>
          <div><strong>Reconciliar:</strong> compara sistema x Bling e corrige divergência de estoque.</div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Ações automáticas</h2>
          <p className="text-sm text-gray-500 mt-1">
            Use essas ações para destravar fila, revisar itens recentes e rodar uma conferência completa.
          </p>
        </div>
        {lastBatchResult && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            <div className="font-semibold">Último resultado do vínculo em massa</div>
            <div className="mt-1">
              Processados: {lastBatchResult.total_processados || 0} | Vinculados: {lastBatchResult.vinculados || 0} | Sync ok: {lastBatchResult.sincronizados_com_sucesso || 0} | Sync erro: {lastBatchResult.sincronizados_com_erro || 0}
            </div>
            <div>
              Não encontrados: {lastBatchResult.nao_encontrados_no_bling || 0} | Erros: {lastBatchResult.erros || 0} | Restantes: {lastBatchResult.restantes_para_proximo_lote || 0}
            </div>
            {lastBatchResult.interrompido_por_tempo && (
              <div className="mt-1 font-medium">Processamento parcial por tempo. Clique no botão novamente para continuar do ponto seguinte.</div>
            )}
          </div>
        )}
        <div className="grid gap-3 md:grid-cols-3">
          <button
            onClick={() => runGlobalAction(
              'reprocessar',
              () => api.post('/estoque/sync/reprocessar-falhas', { limit: 100 }),
              (response) => `Falhas reagendadas: ${response.data?.reprocessados || 0}`,
            )}
            disabled={runningAction !== ''}
            className="rounded-lg bg-red-600 px-4 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {runningAction === 'reprocessar' ? 'Processando...' : 'Reprocessar falhas'}
          </button>
          <button
            onClick={() => runGlobalAction(
              'recentes',
              () => api.post('/estoque/sync/reconciliar-recentes', { limit: 150, minutes: 30 }, { timeout: 0 }),
              (response) => `Recentes avaliados: ${response.data?.avaliados || 0} | divergências: ${response.data?.divergencias || 0}`,
            )}
            disabled={runningAction !== ''}
            className="rounded-lg bg-amber-600 px-4 py-3 text-sm font-semibold text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {runningAction === 'recentes' ? 'Processando...' : 'Reconciliar recentes'}
          </button>
          <button
            onClick={() => runGlobalAction(
              'geral',
              () => api.post('/estoque/sync/reconciliar-geral', { limit: 500, minutes: 30 }, { timeout: 0 }),
              (response) => {
                if (response.data?.status === 'started') return 'Auditoria geral iniciada em segundo plano';
                if (response.data?.status === 'running') return 'Auditoria geral já está em execução';
                return `Auditoria geral: ${response.data?.avaliados || 0} itens | divergências: ${response.data?.divergencias || 0}`;
              },
            )}
            disabled={runningAction !== ''}
            className="rounded-lg bg-slate-800 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {runningAction === 'geral' ? 'Processando...' : 'Auditoria geral'}
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <button
            onClick={vincularTodosPorSku}
            disabled={runningAction !== ''}
            className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
          >
            {runningAction === 'vincular-massa' ? 'Vinculando...' : 'Vincular em massa por SKU'}
          </button>
          <button
            onClick={sincronizarDivergentes}
            disabled={runningAction !== ''}
            className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800 hover:bg-amber-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
          >
            {runningAction === 'sync-divergentes' ? 'Sincronizando...' : 'Sincronizar divergentes (sistema -> Bling)'}
          </button>
        </div>
      </div>

      {naoVinculados.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Produtos não vinculados</h2>
              <p className="text-sm text-gray-500 mt-1">
                Mostrando os primeiros 20 para agilizar seu trabalho. Use os botões para filtrar e buscar no Bling.
              </p>
            </div>
            <button
              onClick={() => setStatusFilter('nao_vinculado')}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Ver todos os não vinculados
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Produto</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Código / SKU</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Estoque</th>
                  <th className="px-4 py-3 text-left font-semibold text-slate-700">Ação rápida</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {naoVinculados.slice(0, 20).map((row) => (
                  <tr key={`nao-vinculado-${row.id}`}>
                    <td className="px-4 py-3 text-slate-800 font-medium">{row.nome}</td>
                    <td className="px-4 py-3 text-slate-600">{row.codigo || '-'} / {row.sku || '-'}</td>
                    <td className="px-4 py-3 text-slate-600">{formatNumber(row.estoqueAtual)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => {
                          const termo = row.codigo || row.sku || row.nome;
                          setBlingSearch(termo || '');
                          searchBlingProducts(termo || '');
                        }}
                        disabled={runningAction !== ''}
                        className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
                      >
                        Buscar no Bling
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Vincular produtos ao Bling</h2>
          <p className="text-sm text-gray-500 mt-1">
            Busque um item no Bling e vincule ao produto local para habilitar a sincronização automática.
          </p>
        </div>
        <div className="flex gap-3">
          <input
            value={blingSearch}
            onChange={(event) => setBlingSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') searchBlingProducts();
            }}
            placeholder="Buscar produto no Bling"
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />
          <button
            onClick={searchBlingProducts}
            disabled={runningAction !== ''}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {runningAction === 'buscar-bling' ? 'Buscando...' : 'Buscar no Bling'}
          </button>
        </div>
        {blingProducts.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <div className="max-h-64 overflow-auto divide-y divide-slate-100">
              {blingProducts.map((item) => (
                <div key={item.id} className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="font-medium text-slate-900">{item.descricao}</div>
                    <div className="text-xs text-gray-500">ID Bling: {item.id} | Código: {item.codigo || '-'} | Estoque: {formatNumber(item.estoque)}</div>
                  </div>
                  <select
                    defaultValue=""
                    onChange={(event) => {
                      const productId = Number(event.target.value);
                      if (!productId) return;
                      runGlobalAction(
                        `vincular-${item.id}`,
                        () => api.post('/estoque/sync/vincular', { produto_id: productId, bling_id: item.id }),
                        () => 'Produto vinculado com sucesso',
                      );
                    }}
                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  >
                    <option value="">Selecionar produto local...</option>
                    {products
                      .filter((product) => !syncMap.get(product.id)?.bling_produto_id)
                      .map((product) => (
                        <option key={product.id} value={product.id}>
                          {product.codigo} - {product.nome}
                        </option>
                      ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Produtos e status</h2>
            <p className="text-sm text-gray-500 mt-1">
              Se você vir um erro em um item, use o botão "Forçar sync" naquela linha. A tabela usa paginação leve de 20 itens para ficar mais fluida.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nome, código, SKU ou ID Bling"
              className="w-72 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:border-slate-500 focus:outline-none"
            />
            <button
              onClick={() => loadPage(search)}
              disabled={loading}
              className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {loading ? 'Atualizando...' : 'Atualizar'}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            ['todos', 'Todos'],
            ['vinculado', 'Vinculados'],
            ['nao_vinculado', 'Não vinculados'],
            ['erro', 'Erro'],
            ['pendente', 'Pendentes'],
            ['divergente', 'Divergentes'],
          ].map(([value, label]) => (
            <button
              key={value}
              onClick={() => setStatusFilter(value)}
              className={`rounded-full px-4 py-2 text-sm font-medium ${statusFilter === value ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Produto</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Estoque</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Bling</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Últimos eventos</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {pagedRows.map((row) => {
                const statusClass = STATUS_STYLES[row.status] || 'bg-slate-100 text-slate-700';
                const queueClass = STATUS_STYLES[row.queueStatus] || 'bg-slate-100 text-slate-700';
                return (
                  <tr key={row.id} className="align-top">
                    <td className="px-4 py-4">
                      <div className="font-semibold text-slate-900">{row.nome}</div>
                      <div className="text-xs text-gray-500">Código: {row.codigo || '-'} | SKU: {row.sku || '-'}</div>
                    </td>
                    <td className="px-4 py-4 text-slate-700">
                      <div>Sistema: {formatNumber(row.estoqueAtual)}</div>
                      <div>Bling: {formatNumber(row.estoqueBling)}</div>
                      <div className={`${Math.abs(Number(row.divergencia || 0)) >= 0.01 ? 'text-amber-700 font-medium' : 'text-gray-500'} text-xs`}>
                        Divergência: {formatNumber(row.divergencia)}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-slate-700">
                      {row.vinculado ? (
                        <div>
                          <div className="font-medium">ID {row.blingId}</div>
                          <div className="text-xs text-gray-500">Sincronização ativa</div>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-500">Sem vínculo</span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-col gap-2">
                        <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass}`}>
                          {row.status}
                        </span>
                        {row.queueStatus && (
                          <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${queueClass}`}>
                            fila: {row.queueStatus}
                          </span>
                        )}
                        {row.tentativas > 0 && (
                          <span className="text-xs text-gray-500">Tentativas: {row.tentativas}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-xs text-gray-600">
                      <div>Última sync: {formatDate(row.ultimaSincronizacao)}</div>
                      <div>Última tentativa: {formatDate(row.ultimaTentativa)}</div>
                      <div>Próxima tentativa: {formatDate(row.proximaTentativa)}</div>
                      <div>Última conferência: {formatDate(row.ultimaConferencia)}</div>
                      {row.ultimoErro && <div className="mt-2 max-w-xs text-red-700">Erro: {row.ultimoErro}</div>}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-col gap-2">
                        <button
                          onClick={() => runRowAction(
                            row.id,
                            async () => {
                              if (!row.vinculado) {
                                await api.post(`/estoque/sync/vincular-automatico/${row.id}`);
                              }
                              await api.post(`/estoque/sync/forcar/${row.id}`);
                            },
                            row.vinculado
                              ? 'Sincronização forçada concluída'
                              : 'Produto vinculado e sincronizado com sucesso',
                          )}
                          disabled={rowActionId === row.id}
                          className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
                        >
                          {rowActionId === row.id ? 'Processando...' : 'Forçar sync'}
                        </button>
                        <button
                          onClick={() => runRowAction(
                            row.id,
                            () => api.post(`/estoque/sync/reconciliar/${row.id}?origem=sistema`),
                            'Reconciliação solicitada',
                          )}
                          disabled={!row.vinculado || rowActionId === row.id}
                          className="rounded-lg bg-slate-700 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-gray-300"
                        >
                          Reconciliar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!loading && mergedRows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-gray-500">
                    Nenhum produto encontrado com os filtros atuais.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {mergedRows.length > 0 && (
          <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 text-sm text-slate-600 md:flex-row md:items-center md:justify-between">
            <div>
              Exibindo {pageStart + 1} a {Math.min(pageEnd, mergedRows.length)} de {mergedRows.length} item(ns)
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={pageSafe === 1}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="px-2">Página {pageSafe} de {totalPages}</span>
              <button
                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={pageSafe === totalPages}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Próxima
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default EstoqueBling;