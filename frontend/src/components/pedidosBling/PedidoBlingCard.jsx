import { useState } from 'react';
import { toast } from 'react-hot-toast';
import api from '../../api';
import PedidoBlingCampoInfo from './PedidoBlingCampoInfo';
import PedidoBlingLinhaItem from './PedidoBlingLinhaItem';
import PedidoBlingStatusBadge from './PedidoBlingStatusBadge';
import { formatarDataHora, formatarMoeda } from './pedidoBlingUtils';

export default function PedidoBlingCard({
  pedido,
  onConfirmar,
  onCancelar,
  onConsolidarDuplicidade,
  onReconciliarFluxo,
}) {
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
    const confirmou = window.confirm(
      `Confirmar pedido Bling #${pedido.pedido_bling_numero || pedido.pedido_bling_id}?\nIsso vai apenas confirmar o pedido no sistema. A venda sera consolidada somente quando houver NF.`
    );
    if (!confirmou) return;

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
    const confirmou = window.confirm(
      `Cancelar pedido #${pedido.pedido_bling_numero || pedido.pedido_bling_id}?\nAs reservas de estoque serao liberadas.`
    );
    if (!confirmou) return;

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
        onClick={() => setExpandido((value) => !value)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-gray-900">#{pedido.pedido_bling_numero || pedido.pedido_bling_id}</span>
            <PedidoBlingStatusBadge status={expirado && pedido.status === 'aberto' ? 'expirado' : pedido.status} />
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
              onClick={(event) => {
                event.stopPropagation();
                handleConfirmar();
              }}
              disabled={acao}
              className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Confirmar
            </button>
          )}
          {podeCancelar && (
            <button
              onClick={(event) => {
                event.stopPropagation();
                handleCancelar();
              }}
              disabled={acao}
              className="text-xs bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Cancelar
            </button>
          )}
          {acoesDisponiveis.pode_consolidar_duplicidade && (
            <button
              onClick={(event) => {
                event.stopPropagation();
                handleConsolidarDuplicidade();
              }}
              disabled={acao}
              className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg font-medium disabled:opacity-50 transition"
            >
              Consolidar
            </button>
          )}
          {acoesDisponiveis.pode_reconciliar_fluxo && (
            <button
              onClick={(event) => {
                event.stopPropagation();
                handleReconciliarFluxo();
              }}
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
            <PedidoBlingCampoInfo label="Pedido na loja" valor={pedido.numero_pedido_loja} />
            <PedidoBlingCampoInfo label="Pedido no canal" valor={pedido.numero_pedido_canal} />
            <PedidoBlingCampoInfo label="Situacao Bling" valor={situacaoBling?.descricao || situacaoBling?.codigo} />
            <PedidoBlingCampoInfo label="Loja Bling" valor={pedido.loja?.nome} />
            <PedidoBlingCampoInfo label="Cliente" valor={pedido.cliente?.nome} />
            <PedidoBlingCampoInfo label="Documento" valor={pedido.cliente?.documento} />
            <PedidoBlingCampoInfo label="Telefone" valor={pedido.cliente?.telefone} />
            <PedidoBlingCampoInfo label="Email" valor={pedido.cliente?.email} />
            <PedidoBlingCampoInfo label="Data do pedido" valor={formatarDataHora(pedido.data_pedido)} />
            <PedidoBlingCampoInfo label="Total" valor={formatarMoeda(pedido.financeiro?.total)} />
            <PedidoBlingCampoInfo label="Desconto" valor={formatarMoeda(pedido.financeiro?.desconto)} />
            <PedidoBlingCampoInfo label="Frete" valor={formatarMoeda(pedido.financeiro?.frete)} />
          </div>

          {(notaFiscal?.id || notaFiscal?.numero || notaFiscal?.chave) && (
            <div className="rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">NF vinculada</p>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-2">
                <PedidoBlingCampoInfo label="NF Bling ID" valor={notaFiscal.id} />
                <PedidoBlingCampoInfo
                  label="Numero / serie"
                  valor={[notaFiscal.numero, notaFiscal.serie].filter(Boolean).join(' / ')}
                />
                <PedidoBlingCampoInfo label="Situacao NF" valor={notaFiscal.situacao} />
                <PedidoBlingCampoInfo label="Chave" valor={notaFiscal.chave} />
              </div>
            </div>
          )}

          {duplicidade.tem_duplicados && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Duplicidade por numero do pedido loja</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
                <PedidoBlingCampoInfo
                  label="Pedido canonico"
                  valor={duplicidade.pedido_canonico?.pedido_bling_numero || duplicidade.pedido_canonico?.pedido_bling_id}
                />
                <PedidoBlingCampoInfo label="Pedido loja" valor={duplicidade.numero_pedido_loja} />
                <PedidoBlingCampoInfo label="Revisao manual" valor={duplicidade.requer_revisao_manual ? 'Sim' : 'Nao'} />
              </div>
              {(duplicidade.pedidos_duplicados || []).length > 0 && (
                <div className="mt-3 space-y-2">
                  {duplicidade.pedidos_duplicados.map((duplicado) => (
                    <div key={duplicado.id} className="rounded-lg border border-amber-100 bg-white px-3 py-2 text-sm text-gray-700">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold">#{duplicado.pedido_bling_numero || duplicado.pedido_bling_id || duplicado.id}</span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            duplicado.pode_mesclar_automaticamente
                              ? 'bg-green-50 text-green-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}
                        >
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
                {pedido.itens.map((item, index) => (
                  <PedidoBlingLinhaItem key={item.id || `${pedido.id}-${item.sku || index}`} item={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
