import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';

import api from '../api';

function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700',
    green: 'bg-emerald-100 text-emerald-700',
    yellow: 'bg-amber-100 text-amber-700',
    red: 'bg-rose-100 text-rose-700',
    blue: 'bg-blue-100 text-blue-700',
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  );
}

function toneFromSeverity(severity) {
  if (severity === 'critical') return 'red';
  if (severity === 'high') return 'yellow';
  if (severity === 'medium') return 'blue';
  if (severity === 'info') return 'green';
  return 'slate';
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function SummaryCard({ title, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

function friendlyErrorMessage(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';

  const lower = raw.toLowerCase();

  if (lower.includes("estoque_movimentacoes_user_id_fkey")) {
    return 'Nao foi possivel registrar a baixa automatica porque faltava um usuario valido para a operacao.';
  }
  if (lower.includes("session's transaction has been rolled back")) {
    return 'A tentativa automatica falhou por um erro interno de processamento. O incidente continua aberto para nova tentativa.';
  }
  if (lower.includes('foreign key constraint')) {
    return 'A correcao automatica nao conseguiu salvar todos os vinculos necessarios no banco.';
  }
  if (lower.includes('produto nao encontrado') || lower.includes('produto não encontrado')) {
    return 'O produto do item ainda nao foi encontrado no cadastro local.';
  }
  if (lower.includes('sku') && lower.includes('nao encontrado')) {
    return 'O SKU do item ainda nao foi encontrado no cadastro local.';
  }
  if (lower.includes('autocorrecao falhou') || lower.includes('autocorreção falhou')) {
    return 'A correcao automatica nao conseguiu concluir a acao sugerida.';
  }
  if (raw.length > 220) {
    return `${raw.slice(0, 217)}...`;
  }

  return raw;
}

function formatAutofixDetails(details) {
  if (!details || typeof details !== 'object') return '';

  if (details.auto_fix_error) return friendlyErrorMessage(details.auto_fix_error);

  const result = details.auto_fix_result;
  if (result?.error) return friendlyErrorMessage(result.error);
  if (Array.isArray(result?.erros) && result.erros.length > 0) return friendlyErrorMessage(result.erros.join(' | '));
  if (result?.motivo) return friendlyErrorMessage(result.motivo);

  return '';
}

function IncidentCard({ incidente, onCorrigir, onResolver, acaoId }) {
  const pedidoLabel = incidente.pedido_bling_numero || incidente.pedido_bling_id || '-';
  const autoFixDetalhe = formatAutofixDetails(incidente.details);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={toneFromSeverity(incidente.severity)}>{incidente.severity}</Badge>
            <Badge tone={incidente.status === 'resolved' ? 'green' : 'slate'}>{incidente.status}</Badge>
            <span className="text-xs font-mono text-slate-500">{incidente.code}</span>
          </div>
          <h3 className="mt-2 text-sm font-semibold text-slate-900">{incidente.title}</h3>
          <p className="mt-1 text-sm text-slate-600">{incidente.message}</p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <p>{formatDate(incidente.last_seen_em)}</p>
          <p>{incidente.occurrences}x</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-500 md:grid-cols-2">
        <p>Pedido Bling: {pedidoLabel}</p>
        <p>ID interno: {incidente.pedido_bling_id || '-'}</p>
        <p>NF Bling: {incidente.nf_bling_id || '-'}</p>
        <p>SKU: {incidente.sku || '-'}</p>
      </div>

      {incidente.suggested_action && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          {incidente.suggested_action}
        </div>
      )}

      {incidente.auto_fix_status === 'failed' && autoFixDetalhe && (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          Ultima tentativa de correcao: {autoFixDetalhe}
        </div>
      )}

      <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
        <strong>Corrigir</strong> tenta executar a acao automatica sugerida.
        <br />
        <strong>Resolver</strong> apenas marca o incidente como tratado manualmente, sem corrigir o pedido.
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {incidente.auto_fixable && incidente.status !== 'resolved' && (
          <button
            type="button"
            onClick={() => onCorrigir(incidente)}
            disabled={acaoId === `corrigir-${incidente.id}`}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-emerald-700 disabled:opacity-50"
          >
            Tentar corrigir
          </button>
        )}
        {incidente.status !== 'resolved' && (
          <button
            type="button"
            onClick={() => onResolver(incidente)}
            disabled={acaoId === `resolver-${incidente.id}`}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Marcar como resolvido
          </button>
        )}
      </div>
    </div>
  );
}

export default function BlingFlowMonitor() {
  const [resumo, setResumo] = useState(null);
  const [incidentes, setIncidentes] = useState([]);
  const [eventos, setEventos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [rodandoAuditoria, setRodandoAuditoria] = useState(false);
  const [acaoId, setAcaoId] = useState('');

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [resumoRes, incidentesRes, eventosRes] = await Promise.all([
        api.get('/integracoes/bling/monitor/resumo'),
        api.get('/integracoes/bling/monitor/incidentes', { params: { status: 'open', limite: 50 } }),
        api.get('/integracoes/bling/monitor/eventos', { params: { limite: 30 } }),
      ]);
      setResumo(resumoRes.data);
      setIncidentes(incidentesRes.data || []);
      setEventos(eventosRes.data || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao carregar monitor do Bling');
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function executarAuditoria() {
    setRodandoAuditoria(true);
    try {
      const response = await api.post('/integracoes/bling/monitor/auditar?dias=7&limite=300&auto_fix=true');
      const data = response.data || {};
      toast.success(`Auditoria concluida: ${data.incidentes_detectados || 0} incidente(s), ${data.auto_fix_sucessos || 0} correcao(oes).`);
      await carregar();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao executar auditoria');
    } finally {
      setRodandoAuditoria(false);
    }
  }

  async function corrigirIncidente(incidente) {
    setAcaoId(`corrigir-${incidente.id}`);
    try {
      const response = await api.post(`/integracoes/bling/monitor/incidentes/${incidente.id}/corrigir`);
      const detalhe =
        response.data?.details?.error ||
        response.data?.details?.motivo ||
        (Array.isArray(response.data?.details?.erros) ? response.data.details.erros.join(' | ') : '');

      if (response.data?.success) {
        toast.success('Correcao automatica aplicada.');
      } else {
        toast.error(friendlyErrorMessage(detalhe) || 'A correcao automatica nao conseguiu resolver o incidente.');
      }
      await carregar();
    } catch (error) {
      toast.error(friendlyErrorMessage(error.response?.data?.detail) || 'Erro ao corrigir incidente');
    } finally {
      setAcaoId('');
    }
  }

  async function resolverIncidente(incidente) {
    setAcaoId(`resolver-${incidente.id}`);
    try {
      await api.post(`/integracoes/bling/monitor/incidentes/${incidente.id}/resolver`);
      toast.success('Incidente marcado como resolvido manualmente.');
      await carregar();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao resolver incidente');
    } finally {
      setAcaoId('');
    }
  }

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Monitor Bling</h1>
          <p className="mt-1 text-sm text-slate-500">
            Auditoria do fluxo pedido, NF, reserva e baixa de estoque.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={carregar}
            disabled={carregando}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Atualizar
          </button>
          <button
            type="button"
            onClick={executarAuditoria}
            disabled={rodandoAuditoria}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-50"
          >
            Rodar auditoria
          </button>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard title="Status" value={resumo?.status || '-'} hint="Saude atual do fluxo" />
        <SummaryCard title="Incidentes abertos" value={resumo?.incidentes_abertos ?? '-'} hint="Pendencias em aberto" />
        <SummaryCard title="Criticos" value={resumo?.por_severidade?.critical || 0} hint="Exigem atencao imediata" />
        <SummaryCard title="High" value={resumo?.por_severidade?.high || 0} hint="Fluxo em risco" />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Incidentes</h2>
            <span className="text-sm text-slate-500">{incidentes.length} item(ns)</span>
          </div>

          {carregando ? (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">Carregando...</div>
          ) : incidentes.length === 0 ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center text-emerald-700">
              Nenhum incidente aberto no momento.
            </div>
          ) : (
            <div className="space-y-3">
              {incidentes.map((incidente) => (
                <IncidentCard
                  key={incidente.id}
                  incidente={incidente}
                  onCorrigir={corrigirIncidente}
                  onResolver={resolverIncidente}
                  acaoId={acaoId}
                />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Eventos recentes</h2>
            <span className="text-sm text-slate-500">{eventos.length} item(ns)</span>
          </div>

          <div className="space-y-3">
            {eventos.map((evento) => (
              <div key={evento.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={toneFromSeverity(evento.severity)}>{evento.severity}</Badge>
                      <Badge tone={evento.status === 'ok' ? 'green' : evento.status === 'received' ? 'blue' : 'yellow'}>
                        {evento.status}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{evento.event_type}</p>
                    <p className="mt-1 text-sm text-slate-600">{evento.message || '-'}</p>
                  </div>
                  <span className="text-xs text-slate-500">{formatDate(evento.processed_at)}</span>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-500">
                  <p>Pedido Bling: {evento.pedido_bling_numero || evento.pedido_bling_id || '-'}</p>
                  <p>ID interno: {evento.pedido_bling_id || '-'}</p>
                  <p>NF Bling: {evento.nf_bling_id || '-'}</p>
                  <p>SKU: {evento.sku || '-'}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
