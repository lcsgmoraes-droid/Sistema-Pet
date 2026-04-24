import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';

import api from '../api';

const HEAVY_REQUEST_TIMEOUT_MS = 60000;
const SNAPSHOT_LIMIT = 200;
const MASS_LINK_BATCH_SIZE = 20;
const MASS_LINK_MAX_BATCHES = 5;
const SYNC_PROBLEMS_LIMIT = 300;

const EMPTY_COBERTURA = {
  total_bling: 0,
  bling_com_match_no_sistema: 0,
  bling_sem_match_no_sistema: 0,
  bling_sync_ok: 0,
  bling_com_problema: 0,
  atualizado_em: null,
  cache_idade_segundos: 0,
  snapshot_disponivel: false,
  precisa_atualizar: true,
};

const EMPTY_FALTANTES_META = {
  total: 0,
  snapshotDisponivel: false,
  coletaCompleta: true,
  atualizadoEm: null,
  cacheIdadeSegundos: 0,
  precisaAtualizar: true,
};

const EMPTY_VINCULOS_META = {
  total: 0,
  snapshotDisponivel: false,
  atualizadoEm: null,
  cacheIdadeSegundos: 0,
  coletaCompleta: true,
  precisaAtualizar: true,
};

const EMPTY_BLING_CONNECTION = {
  checked: false,
  connected: null,
  message: '',
  detail: '',
};

const TAB_CONFIG = {
  criar: {
    label: 'Criar no sistema',
    emptyTitle: 'Nenhum produto pendente para criar',
    emptyDescription: 'Quando o catalogo do Bling tiver item sem SKU ou codigo de barras local, ele aparece aqui.',
  },
  vincular: {
    label: 'Vincular existente',
    emptyTitle: 'Nenhum vinculo pendente',
    emptyDescription: 'Quando encontrarmos o produto no Bling mas faltar apenas o vinculo, ele aparece aqui.',
  },
  corrigir: {
    label: 'Corrigir falhas',
    emptyTitle: 'Nenhuma falha de sincronizacao aberta',
    emptyDescription: 'Produtos vinculados com divergencia, fila travada ou erro aparecem nesta fila.',
  },
};

const ISSUE_TONES = {
  red: {
    panel: 'border-red-200 bg-red-50 text-red-700',
    badge: 'bg-red-100 text-red-700',
    button: 'bg-red-600 text-white hover:bg-red-700',
  },
  amber: {
    panel: 'border-amber-200 bg-amber-50 text-amber-800',
    badge: 'bg-amber-100 text-amber-700',
    button: 'bg-amber-500 text-white hover:bg-amber-600',
  },
  sky: {
    panel: 'border-sky-200 bg-sky-50 text-sky-800',
    badge: 'bg-sky-100 text-sky-700',
    button: 'bg-sky-600 text-white hover:bg-sky-700',
  },
  slate: {
    panel: 'border-slate-200 bg-slate-50 text-slate-700',
    badge: 'bg-slate-100 text-slate-700',
    button: 'bg-slate-700 text-white hover:bg-slate-800',
  },
  emerald: {
    panel: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    badge: 'bg-emerald-100 text-emerald-700',
    button: 'bg-emerald-600 text-white hover:bg-emerald-700',
  },
};

function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

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

function formatCacheAge(seconds) {
  const totalSeconds = Number(seconds || 0);
  if (!totalSeconds) return 'agora';
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h`;
}

function formatDurationMs(value) {
  const totalMs = Number(value || 0);
  if (!totalMs) return 'agora';
  if (totalMs < 1000) return `${totalMs} ms`;
  return `${(totalMs / 1000).toFixed(totalMs >= 10000 ? 0 : 1)} s`;
}

function getErrorMessage(error, fallback = 'Nao foi possivel carregar agora.') {
  return error?.response?.data?.detail || error?.message || fallback;
}

function includesSearch(search, values) {
  const term = normalizeText(search);
  if (!term) return true;
  return values.some((value) => normalizeText(value).includes(term));
}

function buildSyncErrorMeta(item, { blingConnected = null } = {}) {
  const ultimoErro = String(item.ultimo_erro || '').trim();
  const rateLimited = /429|too many requests|too_many_requests|limite de requisi/i.test(ultimoErro);
  const authInvalid = /invalid_token|invalid token|invalid_grant|unauthorized|401 client error|token expirado|reconecte o bling|autorizacao salva/i.test(ultimoErro);
  const noActiveLink = /sem v[ií]nculo ativo com o bling|nao configurado para sincroniza/i.test(ultimoErro);
  const notFound = /not found|nao encontrado|não encontrado/i.test(ultimoErro);

  if (rateLimited) {
    const waitingQueue = item.queue_status === 'pendente';
    return {
      category: 'rate_limit',
      tone: 'amber',
      title: waitingQueue ? 'Aguardando janela segura do Bling' : 'Limite temporario da API do Bling',
      description: waitingQueue
        ? 'O item ja entrou de novo na fila segura e sera retomado em lote menor. Abrir ou atualizar a pagina nao dispara esse erro; a tela mostra apenas o ultimo registro salvo.'
        : 'A ultima tentativa esbarrou no limite temporario de requisicoes do Bling. Abrir ou atualizar a pagina nao dispara esse erro; a tela mostra apenas o ultimo registro salvo.',
      buttonLabel: waitingQueue ? 'Tentar item' : 'Reenfileirar item',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: waitingQueue
        ? 'Item aguardando nova janela segura para reenviar.'
        : 'Ultima tentativa bloqueada pelo limite temporario do Bling.',
      technicalValue: '429 TOO_MANY_REQUESTS',
    };
  }

  if (authInvalid) {
    const invalidGrant = /invalid_grant/i.test(ultimoErro);

    if (blingConnected === true) {
      return {
        category: 'auth_resolved',
        tone: 'sky',
        title: 'Conexao com o Bling restabelecida',
        description: 'A integracao ja voltou a responder. Agora voce pode reprocessar esta falha normalmente.',
        buttonLabel: 'Corrigir agora',
        action: 'force',
        detailLabel: 'Ultimo registro',
        detailValue: 'A fila guardou um erro antigo de autorizacao, mas a conexao atual ja esta valida.',
        technicalValue: invalidGrant ? '400 INVALID_GRANT (historico)' : '401 INVALID_TOKEN (historico)',
      };
    }

    return {
      category: 'auth_invalid',
      tone: 'amber',
      title: 'Integracao do Bling precisa ser reconectada',
      description: invalidGrant
        ? 'A autorizacao salva do Bling deixou de valer. Enquanto isso nao for reconectado, reprocessar e forcar sync vao falhar.'
        : 'O token do Bling expirou e a renovacao automatica nao conseguiu concluir. Enquanto isso nao for reconectado, reprocessar e forcar sync vao falhar.',
      buttonLabel: 'Reconectar Bling',
      action: 'reauthorize',
      detailLabel: 'Ultimo registro',
      detailValue: 'A credencial atual da integracao foi recusada pelo Bling.',
      technicalValue: invalidGrant ? '400 INVALID_GRANT' : '401 INVALID_TOKEN',
    };
  }

  if (noActiveLink) {
    return {
      category: 'link',
      tone: 'slate',
      title: 'Vinculo do produto precisa de revisao',
      description: 'A integracao deste produto nao esta pronta para enviar estoque agora. Revise o vinculo e depois tente novamente.',
      buttonLabel: 'Corrigir agora',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: 'Produto sem vinculo ativo para sincronizacao.',
      technicalValue: 'VINCULO_INATIVO',
    };
  }

  if (notFound) {
    return {
      category: 'not_found',
      tone: 'amber',
      title: 'Produto nao localizado no Bling',
      description: 'A ultima tentativa nao encontrou este produto do outro lado. Vale revisar o vinculo antes de tentar novo envio.',
      buttonLabel: 'Corrigir agora',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: 'Ultima tentativa sem encontrar o item correspondente no Bling.',
      technicalValue: 'ITEM_NAO_ENCONTRADO',
    };
  }

  if (ultimoErro) {
    return {
      category: 'generic_error',
      tone: 'red',
      title: 'Falha de sincronizacao',
      description: 'A ultima tentativa de envio nao foi concluida. Revise e tente novamente quando quiser.',
      buttonLabel: 'Corrigir agora',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: 'O ultimo envio ao Bling terminou com erro.',
      technicalValue: ultimoErro.length > 140 ? `${ultimoErro.slice(0, 140)}...` : ultimoErro,
    };
  }

  return null;
}

function buildSyncIssue(item, options = {}) {
  const divergencia = Math.abs(Number(item.divergencia || 0));
  const syncError = buildSyncErrorMeta(item, options);

  if (syncError?.category === 'rate_limit' && item.queue_status === 'pendente') {
    return syncError;
  }

  if (item.queue_status === 'falha_final' || item.queue_status === 'erro' || item.status === 'erro') {
    return syncError || {
      tone: 'red',
      title: 'Falha de sincronizacao',
      description: 'A ultima tentativa de envio para o Bling falhou e precisa de nova tentativa.',
      buttonLabel: 'Corrigir agora',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: 'Falha registrada na ultima tentativa.',
      technicalValue: '-',
    };
  }

  if (divergencia >= 0.01) {
    return {
      tone: 'amber',
      title: 'Estoque divergente',
      description: `Sistema ${formatNumber(item.estoque_sistema)} | Bling ${formatNumber(item.estoque_bling)} | Divergencia ${formatNumber(item.divergencia)}`,
      buttonLabel: 'Reconciliar agora',
      action: 'reconcile',
    };
  }

  if (item.queue_status === 'pendente') {
    return {
      tone: 'sky',
      title: 'Fila pendente',
      description: 'Existe uma tentativa aguardando processamento. Abrir ou atualizar a pagina nao dispara o envio; a tela mostra apenas o estado atual da fila.',
      buttonLabel: 'Forcar agora',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: 'Item aguardando a vez na fila automatica.',
      technicalValue: 'FILA_PENDENTE',
    };
  }

  if (item.status !== 'ativo') {
    return {
      tone: 'slate',
      title: 'Vinculo fora do estado ideal',
      description: 'O produto esta vinculado, mas o status do sync nao esta como ativo.',
      buttonLabel: 'Forcar agora',
      action: 'force',
      detailLabel: 'Ultimo registro',
      detailValue: 'Estado do sync diferente do esperado para envio automatico.',
      technicalValue: item.status || 'STATUS_FORA_DO_IDEAL',
    };
  }

  return null;
}

function SummaryCard({ label, value, hint, tone = 'slate' }) {
  const toneClasses = ISSUE_TONES[tone] || ISSUE_TONES.slate;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-medium text-slate-500">{label}</div>
      <div className="mt-3 flex items-end gap-3">
        <div className="text-3xl font-semibold text-slate-900">{value}</div>
        {hint ? (
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${toneClasses.badge}`}>
            {hint}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function HealthMeter({ percent, label, detail, tone = 'slate' }) {
  const toneMap = {
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
    sky: 'bg-sky-500',
    slate: 'bg-slate-500',
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center justify-between gap-3 text-sm">
        <div className="font-semibold text-slate-900">{label}</div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{percent}%</div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all ${toneMap[tone] || toneMap.slate}`}
          style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
        />
      </div>
      <div className="mt-2 text-sm text-slate-600">{detail}</div>
    </div>
  );
}

function TabButton({ active, label, count, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
        active
          ? 'bg-slate-900 text-white shadow-sm'
          : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
      }`}
    >
      <span>{label}</span>
      <span className={`rounded-full px-2 py-0.5 text-xs ${active ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600'}`}>
        {count}
      </span>
    </button>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-sm">
      <div className="text-base font-semibold text-slate-900">{title}</div>
      <div className="mx-auto mt-2 max-w-2xl text-sm text-slate-500">{description}</div>
    </div>
  );
}

function DetailItem({ label, value, mono = false }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-sm text-slate-800 ${mono ? 'font-mono' : ''}`}>{value || '-'}</div>
    </div>
  );
}

function PendingCard({
  title,
  subtitle,
  reason,
  tone = 'slate',
  badges = [],
  details = [],
  actions = [],
}) {
  const toneClasses = ISSUE_TONES[tone] || ISSUE_TONES.slate;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 flex-1 space-y-4">
          <div className="space-y-1">
            <div className="text-base font-semibold text-slate-900">{title}</div>
            {subtitle ? <div className="text-sm text-slate-500">{subtitle}</div> : null}
          </div>

          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {badges.map((badge) => (
                <span
                  key={`${badge.label}-${badge.value}`}
                  className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                >
                  {badge.label}: <span className={badge.mono ? 'font-mono' : ''}>{badge.value || '-'}</span>
                </span>
              ))}
            </div>
          ) : null}

          <div className={`rounded-xl border px-4 py-3 text-sm ${toneClasses.panel}`}>
            <div className="font-semibold">{reason.title}</div>
            <div className="mt-1">{reason.description}</div>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {details.map((detail) => (
              <DetailItem
                key={`${detail.label}-${detail.value}`}
                label={detail.label}
                value={detail.value}
                mono={detail.mono}
              />
            ))}
          </div>
        </div>

        <div className="flex w-full flex-col gap-2 xl:w-56">
          {actions.map((action) => (
            <button
              key={action.label}
              onClick={action.onClick}
              disabled={action.disabled}
              className={`rounded-xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 ${action.className}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MassLinkProgressPanel({ progress, onClose }) {
  if (!progress) return null;

  const initialTotal = Number(progress.initialTotal || 0);
  const remaining = Math.max(Number(progress.remaining || 0), 0);
  const completed = Math.max(initialTotal - remaining, 0);
  const percent = initialTotal > 0
    ? Math.min(100, Math.round((completed / initialTotal) * 100))
    : 0;

  return (
    <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 shadow-sm">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm font-semibold text-sky-900">Execucao do vinculo em lotes</div>
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${progress.running ? 'bg-sky-600 text-white' : 'bg-emerald-100 text-emerald-700'}`}>
              {progress.running ? 'Em andamento' : 'Concluido'}
            </span>
          </div>

          <div className="text-sm text-slate-700">{progress.message}</div>

          <div className="grid gap-3 md:grid-cols-4">
            <DetailItem label="Lotes" value={`${progress.batchesCompleted || 0}/${progress.maxBatches || 0}`} />
            <DetailItem label="Tentados" value={formatNumber(progress.attempted || 0)} />
            <DetailItem label="Vinculados" value={formatNumber(progress.linked || 0)} />
            <DetailItem label="Restantes" value={formatNumber(remaining)} />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-sky-700">
              <span>Evolucao</span>
              <span>{percent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white">
              <div
                className="h-full rounded-full bg-sky-600 transition-all"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <DetailItem label="Sync OK" value={formatNumber(progress.syncOk || 0)} />
            <DetailItem label="Sync com erro" value={formatNumber(progress.syncErrors || 0)} />
            <DetailItem label="Nao encontrados" value={formatNumber(progress.notFound || 0)} />
            <DetailItem label="Duracao" value={formatDurationMs(progress.elapsedMs || 0)} />
          </div>

          {progress.history?.length ? (
            <div className="space-y-1 rounded-xl bg-white/70 px-3 py-3 text-sm text-slate-600">
              {progress.history.map((item) => (
                <div key={`batch-${item.batchNumber}`}>
                  Lote {item.batchNumber}: {item.linked} vinculados, {item.errors} erros, {item.remaining} restantes, {formatDurationMs(item.elapsedMs)}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {!progress.running ? (
          <button
            onClick={onClose}
            className="rounded-xl border border-sky-200 bg-white px-4 py-2 text-sm font-semibold text-sky-700 transition hover:bg-sky-100"
          >
            Fechar resumo
          </button>
        ) : null}
      </div>
    </div>
  );
}

function EstoqueBling() {
  const [activeTab, setActiveTab] = useState('criar');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState('Abrindo pelo cache da central do Bling...');
  const [coreWarning, setCoreWarning] = useState('');
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [runningAction, setRunningAction] = useState('');
  const [rowActionKey, setRowActionKey] = useState('');
  const [massLinkProgress, setMassLinkProgress] = useState(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncLoaded, setSyncLoaded] = useState(false);
  const [syncError, setSyncError] = useState('');

  const [cobertura, setCobertura] = useState(EMPTY_COBERTURA);
  const [faltantesBling, setFaltantesBling] = useState([]);
  const [faltantesMeta, setFaltantesMeta] = useState(EMPTY_FALTANTES_META);
  const [produtosSemVinculo, setProdutosSemVinculo] = useState([]);
  const [vinculosMeta, setVinculosMeta] = useState(EMPTY_VINCULOS_META);
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
      const response = await api.get('/bling/teste-conexao', { timeout: 15000 });
      const data = response?.data || {};
      setBlingConnection({
        checked: true,
        connected: Boolean(data.conectado || data.success),
        message: data.message || '',
        detail: data.detail || '',
      });
    } catch (error) {
      const detail = getErrorMessage(error, 'Nao foi possivel verificar a conexao atual do Bling.');
      setBlingConnection((current) => ({
        checked: true,
        connected: current.checked ? current.connected : null,
        message: current.checked
          ? (current.message || 'Mantivemos o ultimo estado conhecido da conexao com o Bling.')
          : 'Nao foi possivel validar a conexao com o Bling.',
        detail,
      }));
      if (!silent) {
        toast.error(detail);
      }
    }
  };

  const loadSyncProblems = async ({ silent = true } = {}) => {
    setSyncLoading(true);
    setSyncError('');

    try {
      const response = await api.get('/estoque/sync/status-problemas', {
        timeout: HEAVY_REQUEST_TIMEOUT_MS,
        params: {
          limit: SYNC_PROBLEMS_LIMIT,
          offset: 0,
        },
      });

      setSyncItems(response?.data || []);
      setSyncLoaded(true);
    } catch (error) {
      const message = getErrorMessage(error, 'Nao foi possivel carregar a fila de falhas agora.');
      setSyncError(message);
      setSyncLoaded(true);
      if (!silent) {
        toast.error(message);
      }
    } finally {
      setSyncLoading(false);
    }
  };

  const loadDashboard = async ({ forceRefresh = false, showToast = false, refreshSyncProblems = false } = {}) => {
    if (hasLoadedOnce) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setCoreWarning('');
    setRefreshMessage(
      forceRefresh
        ? 'Atualizando painel do Bling em uma leitura consolidada...'
        : 'Abrindo pelo cache da central do Bling...',
    );

    try {
      await loadBlingConnectionStatus({ silent: true });

      const response = await api.get('/estoque/sync/dashboard', {
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
        payload?.resumo?.snapshot_disponivel
        || payload?.faltantes?.snapshot_disponivel
        || payload?.vinculos?.snapshot_disponivel,
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
        setRefreshMessage(forceRefresh ? 'Carregando fila de falhas...' : 'Lendo fila de falhas...');
        await loadSyncProblems({ silent: !showToast });
      }

      if (showToast) {
        if (forceRefresh && !snapshotReturned) {
          toast.error(dashboardWarnings[0] || 'A leitura terminou, mas o snapshot do Bling nao ficou disponivel.');
        } else if (dashboardWarnings.length) {
          toast(dashboardWarnings[0]);
        } else {
          toast.success(forceRefresh ? 'Painel atualizado com leitura nova do Bling.' : 'Painel atualizado.');
        }
      }
    } catch (error) {
      const message = getErrorMessage(error, 'Nao foi possivel abrir a central do Bling agora.');
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
      setRefreshMessage('');
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  useEffect(() => {
    const refreshConnectionOnFocus = () => {
      if (document.visibilityState === 'hidden') return;
      loadBlingConnectionStatus({ silent: true }).catch(() => {});
    };

    window.addEventListener('focus', refreshConnectionOnFocus);
    document.addEventListener('visibilitychange', refreshConnectionOnFocus);

    return () => {
      window.removeEventListener('focus', refreshConnectionOnFocus);
      document.removeEventListener('visibilitychange', refreshConnectionOnFocus);
    };
  }, []);

  useEffect(() => {
    if (activeTab === 'corrigir' && !syncLoaded && !syncLoading) {
      loadSyncProblems();
    }
  }, [activeTab, syncLoaded, syncLoading]);

  const syncProblems = useMemo(() => {
    return (syncItems || [])
      .map((item) => ({
        ...item,
        issue: buildSyncIssue(item, { blingConnected: blingConnection.connected }),
      }))
      .filter((item) => item.issue);
  }, [blingConnection.connected, syncItems]);

  const filteredCreate = useMemo(() => {
    return faltantesBling.filter((item) => includesSearch(search, [
      item.descricao,
      item.codigo,
      item.sku,
      item.codigo_barras,
      item.id,
      item.motivo,
    ]));
  }, [faltantesBling, search]);

  const filteredLink = useMemo(() => {
    return produtosSemVinculo.filter((item) => includesSearch(search, [
      item.nome,
      item.codigo,
      item.codigo_barras,
      item.bling_nome,
      item.bling_codigo,
      item.bling_sku,
      item.bling_codigo_barras,
      item.motivo,
    ]));
  }, [produtosSemVinculo, search]);

  const filteredFix = useMemo(() => {
    return syncProblems.filter((item) => includesSearch(search, [
      item.produto_nome,
      item.sku,
      item.bling_produto_id,
      item.issue?.title,
      item.issue?.description,
      item.ultimo_erro,
    ]));
  }, [search, syncProblems]);

  const hasAuthInvalidIssues = filteredFix.some((item) => item.issue?.category === 'auth_invalid');
  const shouldShowReconnectWarning = hasAuthInvalidIssues && blingConnection.connected !== true;

  const hasAnySnapshot = Boolean(
    cobertura.snapshot_disponivel || faltantesMeta.snapshotDisponivel || vinculosMeta.snapshotDisponivel,
  );
  const dashboardSyncProblemCount = cobertura.snapshot_disponivel
    ? Number((cobertura.sync_problemas_abertos ?? cobertura.bling_com_problema) || 0)
    : 0;
  const syncProblemCount = syncLoaded
    ? syncProblems.length
    : dashboardSyncProblemCount;
  const counts = {
    criar: faltantesMeta.snapshotDisponivel ? Number(faltantesMeta.total || 0) : '-',
    vincular: vinculosMeta.snapshotDisponivel ? Number(vinculosMeta.total || 0) : '-',
    corrigir: syncLoaded || cobertura.snapshot_disponivel ? syncProblemCount : '-',
  };
  const knownPendingCount = hasAnySnapshot
    ? Number(faltantesMeta.snapshotDisponivel ? faltantesMeta.total || 0 : 0)
      + Number(vinculosMeta.snapshotDisponivel ? vinculosMeta.total || 0 : 0)
      + Number(syncLoaded || cobertura.snapshot_disponivel ? syncProblemCount : 0)
    : null;
  const healthBaseTotal = Math.max(Number(cobertura.total_bling || 0), Number(knownPendingCount || 0), 1);
  const healthPercent = knownPendingCount === null
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
  const healthTone = knownPendingCount === null
    ? 'slate'
    : knownPendingCount === 0
      ? 'emerald'
      : knownPendingCount <= 20
        ? 'amber'
        : 'red';
  const healthDetail = knownPendingCount === null
    ? 'Sem leitura valida ainda. Ao atualizar, a central deve mostrar o termometro e as pendencias abertas.'
    : knownPendingCount === 0
      ? 'Sem pendencias nesta leitura. O catalogo atual ficou coberto e sem fila aberta.'
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
    const initialTotal = Number(vinculosMeta.total || 0);
    if (!initialTotal) {
      toast('Nao ha produtos pendentes para vincular neste momento.');
      return;
    }

    const maxBatches = Math.max(1, Math.min(MASS_LINK_MAX_BATCHES, Math.ceil(initialTotal / MASS_LINK_BATCH_SIZE)));
    const startedAt = new Date().toISOString();

    setRunningAction('vincular-lote');
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

        const response = await api.post('/estoque/sync/vincular-todos', {}, {
          timeout: HEAVY_REQUEST_TIMEOUT_MS,
          params: {
            limite: MASS_LINK_BATCH_SIZE,
            timeout_seconds: 15,
          },
        });

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

        const batchMessage = linked > 0
          ? `Lote ${batchNumber} concluido: ${linked} vinculado(s), ${remaining} restante(s).`
          : (apiErrors || notFound)
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
          elapsedMs: (Number(current?.elapsedMs || 0) + elapsedMs),
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
        message: accumulated.linked > 0
          ? `Execucao finalizada. ${accumulated.linked} item(ns) vinculado(s) e ${accumulated.remaining} restante(s).`
          : 'Execucao finalizada sem avancos. Revise os itens que continuam pendentes.',
      }));

      if (accumulated.linked > 0) {
        toast.success(`Vinculo em lotes concluido. ${accumulated.linked} item(ns) vinculado(s).`);
      } else {
        toast('Nenhum vinculo novo foi criado neste lote.');
      }

      await loadDashboard();
    } catch (error) {
      setMassLinkProgress((current) => ({
        ...current,
        running: false,
        finishedAt: new Date().toISOString(),
        message: error.response?.data?.detail || 'Nao foi possivel concluir o vinculo em lotes.',
      }));
      toast.error(error.response?.data?.detail || 'Nao foi possivel concluir o vinculo em lotes.');
    } finally {
      setRunningAction('');
    }
  };

  const handleImportImagesFromBling = async () => {
    const confirmed = window.confirm(
      'Importar imagens do Bling para os produtos do sistema que ainda estao sem foto? A rotina usa o SKU/codigo atual e roda mais devagar para respeitar o limite da API.',
    );

    if (!confirmed) {
      return;
    }

    setRunningAction('importar-imagens');
    try {
      const response = await api.post('/estoque/sync/importar-imagens', {}, {
        timeout: 0,
        params: {
          limite: 100,
          apenas_sem_imagem: true,
          atraso_ms: 900,
        },
      });

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
      toast.error(error.response?.data?.detail || 'Nao foi possivel importar as imagens do Bling agora.');
    } finally {
      setRunningAction('');
    }
  };

  const runRowAction = async (key, action, successMessage) => {
    setRowActionKey(key);
    try {
      const response = await action();
      const data = response?.data || {};
      const resolvedMessage = typeof successMessage === 'function'
        ? successMessage(data)
        : (data.message || successMessage);

      if (data.ok === false && !data.rate_limited) {
        throw new Error(data.detail || data.erro || 'Nao foi possivel concluir a acao.');
      }

      if (data.rate_limited) {
        toast(data.message || 'O Bling pediu uma pausa. O item foi reagendado automaticamente.');
      } else {
        toast.success(resolvedMessage);
      }
      await loadDashboard();
      if (activeTab === 'corrigir') {
        await loadSyncProblems();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Nao foi possivel concluir a acao.');
    } finally {
      setRowActionKey('');
    }
  };

  const runGlobalAction = async (key, action, successMessage, refreshOptions = {}) => {
    setRunningAction(key);
    try {
      await action();
      toast.success(successMessage);
      await loadDashboard(refreshOptions);
      if (activeTab === 'corrigir' || refreshOptions.refreshSyncProblems) {
        await loadSyncProblems();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Nao foi possivel concluir a acao.');
    } finally {
      setRunningAction('');
    }
  };

  const handleReprocessFailures = async () => {
    setRunningAction('reprocessar');
    try {
      const response = await api.post('/estoque/sync/reprocessar-falhas', { limit: 30 }, { timeout: HEAVY_REQUEST_TIMEOUT_MS });
      const data = response?.data || {};
      const scheduled = Number(data.reprocessados || 0);
      const normalizedBefore = Number(data.normalizados_antes || 0);
      const requeuedWithoutQueue = Number(data.sem_fila_reenfileirados || 0);
      const processedNow = Number(data.processados_agora || 0);
      const remaining = Number(data.restantes_para_scheduler || 0);
      const rateLimited = Boolean(data.rate_limited);
      const cooldown = Number(data.cooldown_seconds || 0);
      const followUpDelayMs = Math.max((cooldown ? Math.ceil(cooldown) : 4), 4) * 1000 + 1000;

      if (scheduled <= 0) {
        const visibleIssues = Number(syncProblems.length || 0);
        toast(
          normalizedBefore > 0
            ? `${normalizedBefore} item(ns) antigos foram ajustados de volta ao estado correto. Nao havia falhas reais prontas para reprocessar agora.`
            : visibleIssues > 0
              ? `Os ${visibleIssues} item(ns) visiveis agora pedem revisao ou reconciliacao individual. Nao havia falhas de fila prontas para reprocessar em lote.`
              : 'Nao havia falhas prontas para reprocessar.',
        );
      } else if (rateLimited) {
        toast.success(
          `Reagendamos ${scheduled} falha(s). ${processedNow} passaram agora, ${remaining} seguem na fila segura, ${requeuedWithoutQueue} vieram de erro sem fila e ${normalizedBefore} item(ns) antigos foram limpos${cooldown ? ` (${Math.ceil(cooldown)}s de respiro).` : '.'}`,
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
      toast.error(error.response?.data?.detail || 'Nao foi possivel reprocessar as falhas agora.');
    } finally {
      setRunningAction('');
    }
  };

  const handleReconnectBling = async () => {
    try {
      const authRedirectUrl = `${window.location.origin}/api/auth/bling/link-autorizacao?redirect=1`;
      const opened = window.open(authRedirectUrl, '_blank', 'noopener,noreferrer');

      if (!opened) {
        window.location.assign(authRedirectUrl);
      }

      toast.success('Abrimos a autorizacao do Bling em nova aba para reconectar a integracao.');
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Nao foi possivel abrir a autorizacao do Bling agora.');
    }
  };

  const criarPrimeirosFaltantes = async () => {
    const candidatos = filteredCreate
      .filter((item) => item.pronto_para_autocorrecao && item.id)
      .slice(0, 20);

    if (!candidatos.length) {
      toast('Nenhum item pronto para autocorrecao neste recorte.');
      return;
    }

    setRunningAction('criar-lote');
    let sucesso = 0;
    let falhas = 0;

    try {
      for (const item of candidatos) {
        try {
          await api.post('/estoque/sync/faltantes-bling/criar', { bling_id: item.id });
          sucesso += 1;
        } catch {
          falhas += 1;
        }
      }
      toast.success(`Lote concluido. Sucesso: ${sucesso} | Falhas: ${falhas}`);
      await loadDashboard();
    } finally {
      setRunningAction('');
    }
  };

  const handleFixItem = async (item) => {
    const issue = item.issue;
    if (!issue) return;

    if (issue.action === 'reauthorize') {
      await handleReconnectBling();
      return;
    }

    if (issue.action === 'reconcile') {
      await runRowAction(
        `fix-${item.produto_id}`,
        () => api.post(`/estoque/sync/reconciliar/${item.produto_id}?origem=sistema`),
        'Reconcilicao enviada para o Bling.',
      );
      return;
    }

    await runRowAction(
      `fix-${item.produto_id}`,
      () => api.post(`/estoque/sync/forcar/${item.produto_id}`),
      'Nova tentativa enviada com sucesso.',
    );
  };

  const searchPlaceholder = {
    criar: 'Buscar por nome, SKU ou codigo de barras',
    vincular: 'Buscar por produto local, SKU ou item do Bling',
    corrigir: 'Buscar por produto, SKU, ID Bling ou erro',
  }[activeTab];

  const renderCreateTab = () => {
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
            subtitle={`Bling #${item.id || '-'} | Estoque no Bling: ${formatNumber(item.estoque)}`}
            tone={item.pronto_para_autocorrecao ? 'amber' : 'slate'}
            badges={[
              { label: 'SKU', value: item.sku || item.codigo || '-', mono: true },
              { label: 'Codigo de barras', value: item.codigo_barras || '-', mono: true },
            ]}
            reason={{
              title: item.acao_sugerida || 'Criar cadastro local',
              description: item.motivo || 'Produto do Bling sem correspondente local.',
            }}
            details={[
              { label: 'Codigo no Bling', value: item.codigo || '-', mono: true },
              { label: 'Ultima leitura', value: formatDate(faltantesMeta.atualizadoEm) },
              { label: 'Cache', value: formatCacheAge(faltantesMeta.cacheIdadeSegundos) },
            ]}
            actions={[
              {
                label: rowActionKey === `create-${item.id}` ? 'Criando...' : 'Criar e vincular',
                onClick: () => runRowAction(
                  `create-${item.id}`,
                  () => api.post('/estoque/sync/faltantes-bling/criar', { bling_id: item.id }),
                  'Produto criado e vinculado com sucesso.',
                ),
                disabled: !item.pronto_para_autocorrecao || rowActionKey !== '',
                className: ISSUE_TONES.emerald.button,
              },
            ]}
          />
        ))}
      </div>
    );
  };

  const renderLinkTab = () => {
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
          const isParentProduct = String(item.tipo_produto || '').toUpperCase() === 'PAI' || item.sincroniza_estoque === false;
          const actionLabel = isParentProduct ? 'Vincular sem sync' : 'Vincular agora';
          const successMessage = isParentProduct
            ? 'Produto PAI vinculado para catalogo. O estoque continuou fora do sync automatico.'
            : 'Produto vinculado com sucesso.';

          return (
            <PendingCard
              key={`vincular-${item.id}`}
              title={item.nome}
              subtitle={`Bling: ${item.bling_nome || '-'} | Match por ${item.match_origem === 'sku' ? 'SKU' : 'codigo de barras'}${isParentProduct ? ' | Produto PAI' : ''}`}
              tone={isParentProduct ? 'slate' : item.match_origem === 'sku' ? 'sky' : 'amber'}
              badges={[
                { label: 'SKU local', value: item.codigo || '-', mono: true },
                { label: 'SKU Bling', value: item.bling_sku || item.bling_codigo || '-', mono: true },
                { label: 'Cod. barras local', value: item.codigo_barras || '-', mono: true },
                { label: 'Tipo local', value: item.tipo_produto || 'SIMPLES' },
              ]}
              reason={{
                title: item.acao_sugerida || 'Vinculo pendente',
                description: item.motivo || 'O produto ja existe dos dois lados, falta apenas criar o vinculo.',
              }}
              details={[
                { label: 'ID Bling', value: item.bling_id || '-', mono: true },
                { label: 'Cod. barras Bling', value: item.bling_codigo_barras || '-', mono: true },
                { label: isParentProduct ? 'Sync de estoque' : 'Estoque local', value: isParentProduct ? 'Desabilitado para produto PAI' : formatNumber(item.estoque_atual) },
              ]}
              actions={[
                {
                  label: rowActionKey === `link-${item.id}` ? 'Vinculando...' : actionLabel,
                  onClick: () => runRowAction(
                    `link-${item.id}`,
                    () => api.post(`/estoque/sync/vincular-automatico/${item.id}`),
                    successMessage,
                  ),
                  disabled: rowActionKey !== '',
                  className: isParentProduct ? ISSUE_TONES.slate.button : ISSUE_TONES.sky.button,
                },
              ]}
            />
          );
        })}
      </div>
    );
  };

  const renderFixTab = () => {
    if (syncLoading && !syncLoaded) {
      return (
        <EmptyState
          title="Carregando fila de falhas"
          description="Estamos buscando apenas os itens com problema de sincronizacao para evitar travar a tela."
        />
      );
    }

    if (syncError && !filteredFix.length) {
      return (
        <EmptyState
          title="Nao foi possivel carregar as falhas agora"
          description={syncError}
        />
      );
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
              Enquanto o token do Bling estiver invalido, reprocessar falhas ou forcar sincronizacao vai continuar falhando.
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

        {filteredFix.some((item) => item.issue?.category === 'rate_limit') ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm">
            Abrir ou atualizar a pagina nao envia estoque para o Bling. Quando aparecer aviso de limite, isso se refere a uma tentativa anterior ja registrada pela fila.
          </div>
        ) : null}

        {filteredFix.map((item) => (
          <PendingCard
            key={`corrigir-${item.produto_id}`}
            title={item.produto_nome}
            subtitle={`Bling ID ${item.bling_produto_id || '-'} | Status ${item.status}${item.queue_status ? ` | Fila ${item.queue_status}` : ''}`}
            tone={item.issue?.tone || 'slate'}
            badges={[
              { label: 'SKU', value: item.sku || '-', mono: true },
              { label: 'Divergencia', value: formatNumber(item.divergencia) },
              { label: 'Tentativas', value: String(item.tentativas_sync || 0) },
            ]}
            reason={{
              title: item.issue?.title || 'Pendencia de sincronizacao',
              description: item.issue?.description || 'Existe uma divergencia ou falha pendente neste item.',
            }}
            details={[
              { label: 'Ultima sync', value: formatDate(item.ultima_sincronizacao) },
              { label: 'Ultima tentativa', value: formatDate(item.ultima_tentativa_sync) },
              { label: item.issue?.detailLabel || 'Ultimo registro', value: item.issue?.detailValue || 'Sem detalhe adicional.' },
              { label: 'Detalhe tecnico', value: item.issue?.technicalValue || '-' },
            ]}
            actions={[
              {
                label: rowActionKey === `fix-${item.produto_id}` ? 'Corrigindo...' : (item.issue?.buttonLabel || 'Corrigir agora'),
                onClick: () => handleFixItem(item),
                disabled: rowActionKey !== '',
                className: (ISSUE_TONES[item.issue?.tone] || ISSUE_TONES.slate).button,
              },
            ]}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <div className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
            Central de pendencias Bling
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Sincronizacao Bling</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Esta tela mostra apenas o que pede acao. Regra de correspondencia: primeiro SKU do Bling, depois codigo de barras. Se nao existir match local, criamos e vinculamos.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleImportImagesFromBling}
            disabled={refreshing || runningAction !== ''}
            className="rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {runningAction === 'importar-imagens' ? 'Importando imagens...' : 'Importar imagens do Bling'}
          </button>
          <button
            onClick={() => loadDashboard({
              forceRefresh: true,
              showToast: true,
              refreshSyncProblems: activeTab === 'corrigir',
            })}
            disabled={refreshing || runningAction !== ''}
            className="rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {refreshing ? 'Atualizando...' : 'Atualizar agora'}
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard label="Bling sem cadastro local" value={counts.criar} tone="amber" />
        <SummaryCard label="Produtos para vincular" value={counts.vincular} tone="sky" />
        <SummaryCard label="Sync com problema" value={counts.corrigir} tone="red" />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="space-y-1">
            {hasAnySnapshot ? (
              <>
                <div className="text-sm font-semibold text-slate-900">
                  Cobertura atual: {Number(cobertura.bling_com_match_no_sistema || 0)} com match local, {Number(cobertura.bling_sync_ok || 0)} com sync ok.
                </div>
                <div className="text-sm text-slate-500">
                  Ultima leitura: {formatDate(cobertura.atualizado_em || faltantesMeta.atualizadoEm || vinculosMeta.atualizadoEm)} | Cache: {formatCacheAge(cobertura.cache_idade_segundos || faltantesMeta.cacheIdadeSegundos || vinculosMeta.cacheIdadeSegundos)}
                </div>
              </>
            ) : (
              <>
                <div className="text-sm font-semibold text-slate-900">
                  Ainda nao existe snapshot desta central.
                </div>
                <div className="text-sm text-slate-500">
                  A pagina abriu leve, sem ler o Bling inteiro. Clique em Atualizar agora quando quiser montar o cache.
                </div>
              </>
            )}
            {!faltantesMeta.coletaCompleta || !vinculosMeta.coletaCompleta ? (
              <div className="text-sm text-amber-700">
                A ultima coleta do Bling foi parcial. Atualize quando quiser refazer o catalogo completo.
              </div>
            ) : null}
            {coreWarning ? (
              <div className="text-sm text-red-600">
                {coreWarning}
              </div>
            ) : null}
          </div>

          <div className="w-full max-w-md space-y-3">
            <div className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {refreshing || loading ? (refreshMessage || 'Carregando...') : 'A tela abre pelo cache e so refaz o catalogo completo quando voce mandar.'}
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

      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {Object.entries(TAB_CONFIG).map(([key, config]) => (
            <TabButton
              key={key}
              active={activeTab === key}
              label={config.label}
              count={counts[key]}
              onClick={() => setActiveTab(key)}
            />
          ))}
        </div>

        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={searchPlaceholder}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-slate-500 xl:max-w-xl"
          />

          <div className="flex flex-wrap gap-3">
            {activeTab === 'criar' ? (
              <button
                onClick={criarPrimeirosFaltantes}
                disabled={runningAction !== '' || !faltantesMeta.snapshotDisponivel}
                className="rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {runningAction === 'criar-lote' ? 'Criando lote...' : 'Criar 20 primeiros'}
              </button>
            ) : null}

            {activeTab === 'vincular' ? (
              <button
                onClick={runMassLinkBySku}
                disabled={runningAction !== '' || !vinculosMeta.snapshotDisponivel}
                className="rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {runningAction === 'vincular-lote' ? 'Vinculando em lotes...' : `Rodar lotes de ${MASS_LINK_BATCH_SIZE} por SKU`}
              </button>
            ) : null}

            {activeTab === 'corrigir' ? (
              <>
                <button
                  onClick={shouldShowReconnectWarning ? handleReconnectBling : handleReprocessFailures}
                  disabled={runningAction !== '' || syncLoading}
                  className="rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {shouldShowReconnectWarning
                    ? 'Reconectar Bling'
                    : (runningAction === 'reprocessar' ? 'Reenfileirando...' : 'Reprocessar falhas')}
                </button>
                <button
                  onClick={() => runGlobalAction(
                    'recentes',
                    () => api.post('/estoque/sync/reconciliar-recentes', { limit: 150, minutes: 30 }, { timeout: 0 }),
                    'Revisao dos recentes concluida.',
                  )}
                  disabled={runningAction !== '' || syncLoading}
                  className="rounded-xl bg-amber-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {runningAction === 'recentes' ? 'Reconciliando...' : 'Reconciliar recentes'}
                </button>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {activeTab === 'vincular' && massLinkProgress ? (
        <MassLinkProgressPanel
          progress={massLinkProgress}
          onClose={() => setMassLinkProgress(null)}
        />
      ) : null}

      {activeTab === 'corrigir' && syncError && filteredFix.length > 0 ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm">
          Exibindo a ultima lista de falhas carregada. Nao conseguimos atualizar agora: {syncError}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm">
          {refreshMessage || 'Carregando central de pendencias do Bling...'}
        </div>
      ) : null}

      {!loading && activeTab === 'criar' ? renderCreateTab() : null}
      {!loading && activeTab === 'vincular' ? renderLinkTab() : null}
      {!loading && activeTab === 'corrigir' ? renderFixTab() : null}
    </div>
  );
}

export default EstoqueBling;
