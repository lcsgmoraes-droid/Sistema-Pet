import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { toast } from 'react-hot-toast';

const STATUS_CONFIG = {
  aberto:     { label: 'Aberto',     cor: 'bg-blue-100 text-blue-800',   dot: 'bg-blue-500' },
  confirmado: { label: 'Confirmado', cor: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
  expirado:   { label: 'Expirado',   cor: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
  cancelado:  { label: 'Cancelado',  cor: 'bg-red-100 text-red-800',     dot: 'bg-red-500' },
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

function LinhaItem({ item }) {
  const reservado = !item.liberado_em && !item.vendido_em;
  const confirmado = !!item.vendido_em;
  const liberado = !!item.liberado_em;

  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="font-mono text-gray-600 mr-2 min-w-[90px]">{item.sku}</span>
      <span className="flex-1 text-gray-800 truncate">{item.descricao || '—'}</span>
      <span className="ml-4 font-semibold text-gray-700">× {item.quantidade}</span>
      <span className={`ml-3 text-xs px-2 py-0.5 rounded-full font-medium ${
        confirmado ? 'bg-green-50 text-green-700'
        : liberado  ? 'bg-gray-100 text-gray-500'
        : reservado ? 'bg-blue-50 text-blue-700'
        : 'bg-gray-100 text-gray-500'
      }`}>
        {confirmado ? 'Baixado' : liberado ? 'Liberado' : 'Reservado'}
      </span>
    </div>
  );
}

function CardPedido({ pedido, onConfirmar, onCancelar }) {
  const [expandido, setExpandido] = useState(false);
  const [acao, setAcao] = useState(false);

  const podeConfirmar = pedido.status === 'aberto' || pedido.status === 'expirado';
  const podeCancelar = pedido.status === 'aberto' || pedido.status === 'expirado';

  async function handleConfirmar() {
    if (!window.confirm(`Confirmar pedido Bling #${pedido.pedido_bling_numero || pedido.pedido_bling_id}?\nIsso vai baixar o estoque dos itens manualmente.`)) return;
    setAcao(true);
    try {
      const res = await api.post(`/integracoes/bling/pedidos/${pedido.id}/confirmar-manual`);
      if (res.data.erros_estoque?.length > 0) {
        toast.success('✅ Pedido confirmado com avisos');
        toast.error('Alguns SKUs não baixaram: ' + res.data.erros_estoque.join(', '), { duration: 8000 });
      } else {
        toast.success('✅ Pedido confirmado e estoque baixado!');
      }
      onConfirmar();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao confirmar pedido');
    } finally {
      setAcao(false);
    }
  }

  async function handleCancelar() {
    if (!window.confirm(`Cancelar pedido #${pedido.pedido_bling_numero || pedido.pedido_bling_id}?\nAs reservas de estoque serão liberadas.`)) return;
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

  const formatarData = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  };

  const expirado = pedido.status === 'aberto' && new Date(pedido.expira_em) < new Date();

  return (
    <div className={`bg-white rounded-xl border shadow-sm overflow-hidden ${expirado ? 'border-yellow-300' : 'border-gray-200'}`}>
      {/* Cabeçalho */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer select-none hover:bg-gray-50 transition"
        onClick={() => setExpandido(v => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-gray-900">
              #{pedido.pedido_bling_numero || pedido.pedido_bling_id}
            </span>
            <BadgeStatus status={expirado && pedido.status === 'aberto' ? 'expirado' : pedido.status} />
            <span className="text-xs text-gray-400 capitalize">{/^\d+$/.test(pedido.canal) || pedido.canal === 'online' ? 'Bling' : pedido.canal}</span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            Criado em {formatarData(pedido.criado_em)}
            {pedido.status === 'aberto' && (
              <span className={`ml-2 ${expirado ? 'text-yellow-600 font-semibold' : ''}`}>
                · Expira {formatarData(pedido.expira_em)}
              </span>
            )}
            {pedido.confirmado_em && (
              <span className="ml-2 text-green-600">· Confirmado {formatarData(pedido.confirmado_em)}</span>
            )}
            {pedido.cancelado_em && (
              <span className="ml-2 text-red-500">· Cancelado {formatarData(pedido.cancelado_em)}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-gray-400">{pedido.itens.length} item{pedido.itens.length !== 1 ? 's' : ''}</span>

          {podeConfirmar && (
            <button
              onClick={e => { e.stopPropagation(); handleConfirmar(); }}
              disabled={acao}
              className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              ✅ Confirmar
            </button>
          )}
          {podeCancelar && (
            <button
              onClick={e => { e.stopPropagation(); handleCancelar(); }}
              disabled={acao}
              className="text-xs bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              ✕ Cancelar
            </button>
          )}

          <span className="text-gray-400 text-sm">{expandido ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* Itens */}
      {expandido && (
        <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 space-y-0.5">
          {pedido.itens.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Sem itens registrados</p>
          ) : (
            pedido.itens.map(it => <LinhaItem key={it.id} item={it} />)
          )}
        </div>
      )}
    </div>
  );
}

export default function PedidosBling() {
  const [pedidos, setPedidos] = useState([]);
  const [total, setTotal] = useState(0);
  const [paginas, setPaginas] = useState(1);
  const [pagina, setPagina] = useState(1);
  const [statusFiltro, setStatusFiltro] = useState('');
  const [carregando, setCarregando] = useState(false);

  const ABAS = [
    { valor: '',           label: 'Todos' },
    { valor: 'aberto',     label: 'Abertos' },
    { valor: 'confirmado', label: 'Confirmados' },
    { valor: 'expirado',   label: 'Expirados' },
    { valor: 'cancelado',  label: 'Cancelados' },
  ];

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const params = { pagina, por_pagina: 20 };
      if (statusFiltro) params.status = statusFiltro;
      const res = await api.get('/integracoes/bling/pedidos', { params });
      setPedidos(res.data.pedidos || []);
      setTotal(res.data.total || 0);
      setPaginas(res.data.paginas || 1);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao carregar pedidos');
    } finally {
      setCarregando(false);
    }
  }, [pagina, statusFiltro]);

  useEffect(() => { carregar(); }, [carregar]);

  function mudarStatus(novoStatus) {
    setStatusFiltro(novoStatus);
    setPagina(1);
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Título */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pedidos Bling</h1>
        <p className="text-sm text-gray-500 mt-1">
          Pedidos recebidos via webhook do Bling. Confirme manualmente se a nota fiscal não chegou automaticamente.
        </p>
      </div>

      {/* Abas de status */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit">
        {ABAS.map(aba => (
          <button
            key={aba.valor}
            onClick={() => mudarStatus(aba.valor)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
              statusFiltro === aba.valor
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {aba.label}
          </button>
        ))}
      </div>

      {/* Contagem */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">
          {carregando ? 'Carregando…' : `${total} pedido${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}`}
        </p>
        <button
          onClick={carregar}
          disabled={carregando}
          className="text-xs text-blue-600 hover:underline disabled:opacity-50"
        >
          ↻ Atualizar
        </button>
      </div>

      {/* Lista */}
      {carregando ? (
        <div className="text-center py-16 text-gray-400">Carregando pedidos…</div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-5xl mb-3">📭</div>
          <p className="text-gray-500 font-medium">Nenhum pedido encontrado</p>
          <p className="text-sm text-gray-400 mt-1">
            {statusFiltro
              ? `Sem pedidos com status "${STATUS_CONFIG[statusFiltro]?.label || statusFiltro}"`
              : 'Os pedidos aparecem aqui quando o Bling envia via webhook'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pedidos.map(p => (
            <CardPedido
              key={p.id}
              pedido={p}
              onConfirmar={carregar}
              onCancelar={carregar}
            />
          ))}
        </div>
      )}

      {/* Paginação */}
      {paginas > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPagina(v => Math.max(1, v - 1))}
            disabled={pagina === 1}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            ← Anterior
          </button>
          <span className="text-sm text-gray-600">
            Página {pagina} de {paginas}
          </span>
          <button
            onClick={() => setPagina(v => Math.min(paginas, v + 1))}
            disabled={pagina === paginas}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Próxima →
          </button>
        </div>
      )}
    </div>
  );
}
