import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-hot-toast';

const STATUS_CONFIG = {
  aberto: { label: 'Aberto', cor: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500' },
  confirmado: { label: 'Confirmado', cor: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  expirado: { label: 'Expirado', cor: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  cancelado: { label: 'Cancelado', cor: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
};

function BadgeStatus({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: status, cor: 'bg-gray-100 text-gray-700', dot: 'bg-gray-400' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.cor}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function formatarDataHora(iso) {
  if (!iso) return '-';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '-';
  return data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function formatarMoeda(valor) {
  if (valor == null || Number.isNaN(Number(valor))) return '-';
  return Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function CampoInfo({ label, valor }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] uppercase tracking-wide text-gray-400">{label}</p>
      <p className="text-sm text-gray-700 break-words">{valor || '-'}</p>
    </div>
  );
}

function LinhaItem({ item }) {
  const reservado = !item.liberado_em && !item.vendido_em;
  const confirmado = !!item.vendido_em;
  const liberado = !!item.liberado_em;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs text-gray-500">{item.sku || 'SEM-SKU'}</span>
            {item.produto_bling_id && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                Produto Bling #{item.produto_bling_id}
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-900 mt-1">{item.descricao || '-'}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 mt-1">
            <span>Qtd: {item.quantidade}</span>
            <span>Unitario: {formatarMoeda(item.valor_unitario)}</span>
            <span>Total: {formatarMoeda(item.total)}</span>
            {item.desconto != null && <span>Desconto: {formatarMoeda(item.desconto)}</span>}
          </div>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          confirmado ? 'bg-green-50 text-green-700'
          : liberado ? 'bg-gray-100 text-gray-500'
          : reservado ? 'bg-blue-50 text-blue-700'
          : 'bg-gray-100 text-gray-500'
        }`}>
          {confirmado ? 'Baixado' : liberado ? 'Liberado' : 'Reservado'}
        </span>
      </div>
    </div>
  );
}

function CardPedido({ pedido, onConfirmar, onCancelar, onConsolidarDuplicidade, onReconciliarFluxo }) {
  const [expandido, setExpandido] = useState(false);
  const [acao, setAcao] = useState(false);

  const podeConfirmar = pedido.status === 'aberto' || pedido.status === 'expirado';
  const podeCancelar = pedido.status === 'aberto' || pedido.status === 'expirado';
  const expirado = pedido.status === 'aberto' && new Date(pedido.expira_em) < new Date();
  const canalLabel = pedido.canal_label || pedido.canal_origem || pedido.canal || 'Bling';
  const clienteNome = pedido.cliente?.nome || 'Cliente nao informado';
  const totalPedido = pedido.financeiro?.total;
  const notaFiscal = pedido.nota_fiscal || {};
  const situacaoBling = pedido.situacao_bling || {};
  const duplicidade = pedido.duplicidade || {};
  const acoesDisponiveis = pedido.acoes_disponiveis || {};

  async function handleConfirmar() {
    if (!window.confirm(`Confirmar pedido Bling #${pedido.pedido_bling_numero || pedido.pedido_bling_id}?
Isso vai apenas confirmar o pedido no sistema. A venda sera consolidada somente quando houver NF.`)) return;
    setAcao(true);
    try {
      const res = await api.post(`/integracoes/bling/pedidos/${pedido.id}/confirmar-manual`);
      if (res.data.erros_estoque?.length > 0) {
        toast.success('Pedido confirmado com avisos');
        toast.error(`Alguns SKUs nao baixaram: ${res.data.erros_estoque.join(', ')}`, { duration: 8000 });
      } else {
        toast.success('Pedido confirmado. Estoque aguardando NF.');
      }
      onConfirmar();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao confirmar pedido');
    } finally {
      setAcao(false);
    }
  }

  async function handleCancelar() {
    if (!window.confirm(`Cancelar pedido #${pedido.pedido_bling_numero || pedido.pedido_bling_id}?
As reservas de estoque serao liberadas.`)) return;
    setAcao(true);
    try {
      await api.post(`/integracoes/bling/pedidos/${pedido.id}/cancelar`);
      toast.success('Pedido cancelado e estoque liberado.');
      onCancelar();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao cancelar pedido');
    } finally {
      setAcao(false);
    }
  }

  async function handleConsolidarDuplicidade() {
    setAcao(true);
    try {
      await onConsolidarDuplicidade(pedido);
    } finally {
      setAcao(false);
    }
  }

  async function handleReconciliarFluxo() {
    setAcao(true);
    try {
      await onReconciliarFluxo(pedido);
    } finally {
      setAcao(false);
    }
  }

  return (
    <div className={`bg-white rounded-xl border shadow-sm overflow-hidden ${expirado ? 'border-yellow-300' : 'border-gray-200'}`}>
      <div
        className="flex items-center gap-3 p-4 cursor-pointer select-none hover:bg-gray-50 transition"
        onClick={() => setExpandido((v) => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-gray-900">#{pedido.pedido_bling_numero || pedido.pedido_bling_id}</span>
            <BadgeStatus status={expirado && pedido.status === 'aberto' ? 'expirado' : pedido.status} />
            <span className="text-xs text-gray-500">{canalLabel}</span>
            {notaFiscal?.id && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                NF #{notaFiscal.numero || notaFiscal.id}
              </span>
            )}
          </div>
          <div className="text-sm text-gray-700 mt-1 flex flex-wrap gap-x-3 gap-y-1">
            <span>{clienteNome}</span>
            <span className="text-gray-300">|</span>
            <span>{formatarMoeda(totalPedido)}</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Criado em {formatarDataHora(pedido.criado_em)}
            {pedido.status === 'aberto' && (
              <span className={`ml-2 ${expirado ? 'text-yellow-600 font-semibold' : ''}`}>
                | Expira {formatarDataHora(pedido.expira_em)}
              </span>
            )}
            {pedido.confirmado_em && <span className="ml-2 text-green-600">| Confirmado {formatarDataHora(pedido.confirmado_em)}</span>}
            {pedido.cancelado_em && <span className="ml-2 text-red-500">| Cancelado {formatarDataHora(pedido.cancelado_em)}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-gray-400">{pedido.itens.length} item{pedido.itens.length !== 1 ? 's' : ''}</span>

          {podeConfirmar && (
            <button
              onClick={(e) => { e.stopPropagation(); handleConfirmar(); }}
              disabled={acao}
              className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Confirmar
            </button>
          )}
          {podeCancelar && (
            <button
              onClick={(e) => { e.stopPropagation(); handleCancelar(); }}
              disabled={acao}
              className="text-xs bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Cancelar
            </button>
          )}
          {acoesDisponiveis.pode_consolidar_duplicidade && (
            <button
              onClick={(e) => { e.stopPropagation(); handleConsolidarDuplicidade(); }}
              disabled={acao}
              className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Consolidar
            </button>
          )}
          {acoesDisponiveis.pode_reconciliar_fluxo && (
            <button
              onClick={(e) => { e.stopPropagation(); handleReconciliarFluxo(); }}
              disabled={acao}
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Reconciliar
            </button>
          )}

          <span className="text-gray-400 text-sm">{expandido ? '^' : 'v'}</span>
        </div>
      </div>

      {expandido && (
        <div className="border-t border-gray-100 px-4 py-4 bg-gray-50 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <CampoInfo label="Pedido na loja" valor={pedido.numero_pedido_loja} />
            <CampoInfo label="Pedido no canal" valor={pedido.numero_pedido_canal} />
            <CampoInfo label="Situacao Bling" valor={situacaoBling?.descricao || situacaoBling?.codigo} />
            <CampoInfo label="Loja Bling" valor={pedido.loja?.nome} />
            <CampoInfo label="Cliente" valor={pedido.cliente?.nome} />
            <CampoInfo label="Documento" valor={pedido.cliente?.documento} />
            <CampoInfo label="Telefone" valor={pedido.cliente?.telefone} />
            <CampoInfo label="Email" valor={pedido.cliente?.email} />
            <CampoInfo label="Data do pedido" valor={formatarDataHora(pedido.data_pedido)} />
            <CampoInfo label="Total" valor={formatarMoeda(pedido.financeiro?.total)} />
            <CampoInfo label="Desconto" valor={formatarMoeda(pedido.financeiro?.desconto)} />
            <CampoInfo label="Frete" valor={formatarMoeda(pedido.financeiro?.frete)} />
          </div>

          {(notaFiscal?.id || notaFiscal?.numero || notaFiscal?.chave) && (
            <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">NF vinculada</p>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-2">
                <CampoInfo label="NF Bling ID" valor={notaFiscal.id} />
                <CampoInfo label="Numero / serie" valor={[notaFiscal.numero, notaFiscal.serie].filter(Boolean).join(' / ')} />
                <CampoInfo label="Situacao NF" valor={notaFiscal.situacao} />
                <CampoInfo label="Chave" valor={notaFiscal.chave} />
              </div>
            </div>
          )}

          {duplicidade.tem_duplicados && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Duplicidade por numero do pedido loja</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
                <CampoInfo label="Pedido canônico" valor={duplicidade.pedido_canonico?.pedido_bling_numero || duplicidade.pedido_canonico?.pedido_bling_id} />
                <CampoInfo label="Pedido loja" valor={duplicidade.numero_pedido_loja} />
                <CampoInfo label="Revisao manual" valor={duplicidade.requer_revisao_manual ? 'Sim' : 'Nao'} />
              </div>
              {(duplicidade.pedidos_duplicados || []).length > 0 && (
                <div className="mt-3 space-y-2">
                  {duplicidade.pedidos_duplicados.map((duplicado) => (
                    <div key={duplicado.id} className="rounded-lg border border-amber-100 bg-white px-3 py-2 text-sm text-gray-700">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold">#{duplicado.pedido_bling_numero || duplicado.pedido_bling_id || duplicado.id}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${duplicado.pode_mesclar_automaticamente ? 'bg-green-50 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                          {duplicado.pode_mesclar_automaticamente ? 'Seguro para consolidar' : 'Bloqueado para revisao'}
                        </span>
                      </div>
                      {duplicado.motivos_bloqueio?.length > 0 && (
                        <p className="text-xs text-amber-700 mt-1">{duplicado.motivos_bloqueio.join(', ')}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {pedido.observacoes && (
            <div className="rounded-lg border border-gray-200 bg-white px-3 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Observacoes</p>
              <p className="text-sm text-gray-700 mt-1 whitespace-pre-wrap">{pedido.observacoes}</p>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">Itens do pedido</p>
            {pedido.itens.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Sem itens registrados</p>
            ) : (
              <div className="space-y-2">
                {pedido.itens.map((it, index) => (
                  <LinhaItem key={it.id || `${pedido.id}-${it.sku || index}`} item={it} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PedidosBling() {
  const [searchParams] = useSearchParams();
  const [pedidos, setPedidos] = useState([]);
  const [total, setTotal] = useState(0);
  const [paginas, setPaginas] = useState(1);
  const [pagina, setPagina] = useState(1);
  const [statusFiltro, setStatusFiltro] = useState('');
  const [carregando, setCarregando] = useState(false);
  const buscaPedido = useMemo(() => (searchParams.get('pedido') || '').trim(), [searchParams]);

  const ABAS = [
    { valor: '', label: 'Todos' },
    { valor: 'aberto', label: 'Abertos' },
    { valor: 'confirmado', label: 'Confirmados' },
    { valor: 'expirado', label: 'Expirados' },
    { valor: 'cancelado', label: 'Cancelados' },
  ];

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const params = { pagina, por_pagina: 20 };
      if (statusFiltro) params.status = statusFiltro;
      if (buscaPedido) params.busca = buscaPedido;
      const res = await api.get('/integracoes/bling/pedidos', { params });
      setPedidos(res.data.pedidos || []);
      setTotal(res.data.total || 0);
      setPaginas(res.data.paginas || 1);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao carregar pedidos');
    } finally {
      setCarregando(false);
    }
  }, [pagina, statusFiltro, buscaPedido]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  useEffect(() => {
    setPagina(1);
  }, [buscaPedido]);

  function mudarStatus(novoStatus) {
    setStatusFiltro(novoStatus);
    setPagina(1);
  }

  async function consolidarDuplicidade(pedido) {
    try {
      const response = await api.post(`/integracoes/bling/pedidos/${pedido.id}/consolidar-duplicidade`);
      const totalMesclados = response.data?.pedidos_mesclados?.length || 0;
      toast.success(`Duplicidade consolidada. ${totalMesclados} pedido(s) incorporado(s).`);
      await carregar();
    } catch (e) {
      const detail = typeof e.response?.data?.detail === 'string'
        ? e.response.data.detail
        : e.response?.data?.detail?.motivo || 'Erro ao consolidar duplicidade';
      toast.error(detail);
    }
  }

  async function reconciliarFluxo(pedido) {
    try {
      const response = await api.post(`/integracoes/bling/pedidos/${pedido.id}/reconciliar-fluxo`);
      toast.success(
        response.data?.nf_numero
          ? `Fluxo reconciliado com a NF ${response.data.nf_numero}.`
          : 'Fluxo reconciliado com sucesso.'
      );
      await carregar();
    } catch (e) {
      const detail = typeof e.response?.data?.detail === 'string'
        ? e.response.data.detail
        : e.response?.data?.detail?.motivo || 'Erro ao reconciliar fluxo do pedido';
      toast.error(detail);
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pedidos Bling</h1>
        <p className="text-sm text-gray-500 mt-1">
          Pedidos recebidos via Bling com canal, referencias, cliente, financeiro, itens e vinculo com NF quando disponivel.
        </p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit flex-wrap">
        {ABAS.map((aba) => (
          <button
            key={aba.valor}
            onClick={() => mudarStatus(aba.valor)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
              statusFiltro === aba.valor ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {aba.label}
          </button>
        ))}
      </div>

      {buscaPedido && (
        <div className="mb-4 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          Filtrado pelo pedido <span className="font-semibold">#{buscaPedido}</span>.
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">
          {carregando ? 'Carregando...' : `${total} pedido${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}`}
        </p>
        <button
          onClick={carregar}
          disabled={carregando}
          className="text-xs text-blue-600 hover:underline disabled:opacity-50"
        >
          Atualizar
        </button>
      </div>

      {carregando ? (
        <div className="text-center py-16 text-gray-400">Carregando pedidos...</div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-5xl mb-3">PED</div>
          <p className="text-gray-500 font-medium">Nenhum pedido encontrado</p>
          <p className="text-sm text-gray-400 mt-1">
            {statusFiltro
              ? `Sem pedidos com status "${STATUS_CONFIG[statusFiltro]?.label || statusFiltro}"`
              : 'Os pedidos aparecem aqui quando o Bling envia via webhook'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pedidos.map((p) => (
            <CardPedido
              key={p.id}
              pedido={p}
              onConfirmar={carregar}
              onCancelar={carregar}
              onConsolidarDuplicidade={consolidarDuplicidade}
              onReconciliarFluxo={reconciliarFluxo}
            />
          ))}
        </div>
      )}

      {paginas > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPagina((v) => Math.max(1, v - 1))}
            disabled={pagina === 1}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Pagina {pagina} de {paginas}
          </span>
          <button
            onClick={() => setPagina((v) => Math.min(paginas, v + 1))}
            disabled={pagina === paginas}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Proxima
          </button>
        </div>
      )}
    </div>
  );
}
